import assert = require('assert');

import { Construct } from 'constructs';
import { Duration, RemovalPolicy, Stack, StackProps } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as path from 'path';

import {SubnetSsmValue, VpcSsmValue} from '../core/ssm-wrangling';
import * as constants from '../core/constants';

export interface VpcMirrorStackProps extends StackProps {
    readonly clusterName: string;
    readonly subnetIds: string[];
    readonly subnetSsmParamNames: string[];
    readonly vpcId: string;
    readonly vpcCidrs: string[];
    readonly vpcSsmParamName: string;
    readonly vpceServiceId: string;
    readonly mirrorVni: string;
}

/**
 * This stack contains the core/shared components required to set up traffic mirroring from one User VPC to one
 * Capture VPC.  That is, one of these stacks should exist for each combination of Capture VPC/Source VPC.  It
 * instantiates AWS Resources into the user's Source VPC in order for their traffic to be mirrored to the Capture
 * VPC.
 *
 * The components it contains are considered 'core/shared' components because they are (relatively) static.  They
 * should remain unchanged as long as the subnets in the user's Source VPC remain unchanged.  They will shared by the
 * many, fluidly-defined mirroring configurations we make for each Elastic Network Interface in the user's VPC.  We
 * create/manage the ENI-specific components from the Python management CLI.  It is presumed that the subnets in a User
 * VPC will change much less often than the ENIs (e.g. compute auto-scaling)
 *
 * See: https://docs.aws.amazon.com/vpc/latest/mirroring/tm-example-glb-endpoints.html
 */
export class VpcMirrorStack extends Stack {
    constructor(scope: Construct, id: string, props: VpcMirrorStackProps) {
        super(scope, id, props);

        // Make a new joined list of tuples of the form [[subnetId1, subnetSsmParamName1], ...]
        const combinedList: [string, string][] = props.subnetIds.map((element, index) => [element, props.subnetSsmParamNames[index]]);

        for (const [subnetId, subnetParamName] of combinedList) {
            // Since we're relying on stable/consistent ordering of the two lists, let's make sure that's true
            assert.ok(subnetParamName.includes(subnetId), `Expected Subnet SSM Param ${subnetParamName} to contain Subnet ID ${subnetId}`);

            const vpcEndpoint = new ec2.CfnVPCEndpoint(this, `VPCE-${subnetId}`, {
                serviceName: `com.amazonaws.vpce.${this.region}.${props.vpceServiceId}`,
                vpcId: props.vpcId,
                vpcEndpointType: 'GatewayLoadBalancer',
                subnetIds: [subnetId],
            });

            const mirrorTarget = new ec2.CfnTrafficMirrorTarget(this, `Target-${subnetId}`, {
                gatewayLoadBalancerEndpointId: vpcEndpoint.ref
            });

            // These SSM parameter will enable us share the details of our subnet-specific Capture setups
            const subnetParamValue: SubnetSsmValue = {mirrorTargetId: mirrorTarget.ref, subnetId: subnetId, vpcEndpointId: vpcEndpoint.ref};
            const subnetParam = new ssm.StringParameter(this, `SubnetParam-${subnetId}`, {
                allowedPattern: '.*',
                description: 'The Subnet\'s details',
                parameterName: subnetParamName,
                stringValue: JSON.stringify(subnetParamValue),
                tier: ssm.ParameterTier.STANDARD,
            });
            subnetParam.node.addDependency(mirrorTarget);
        }

        // Let's mirror all non-local VPC traffic
        // See: https://docs.aws.amazon.com/vpc/latest/mirroring/tm-example-non-vpc.html
        const filter = new ec2.CfnTrafficMirrorFilter(this, 'Filter', {
            description: 'Mirror non-local VPC traffic',
            tags: [{key: 'Name', value: props.vpcId}],
            networkServices: ['amazon-dns']
        });
        for (let block_num = 0; block_num < props.vpcCidrs.length; block_num++) {
            new ec2.CfnTrafficMirrorFilterRule(this, `FRule-RejectLocalOutboundBlock-${block_num + 1}`, {
                destinationCidrBlock: props.vpcCidrs[block_num],
                ruleAction: 'REJECT',
                ruleNumber: 10 + block_num,
                sourceCidrBlock: '0.0.0.0/0',
                trafficDirection: 'EGRESS',
                trafficMirrorFilterId: filter.ref,
                description: 'Reject all intra-VPC traffic'
            });
        }
        new ec2.CfnTrafficMirrorFilterRule(this, 'FRule-AllowOtherOutbound', {
            destinationCidrBlock: '0.0.0.0/0',
            ruleAction: 'ACCEPT',
            ruleNumber: 20,
            sourceCidrBlock: '0.0.0.0/0',
            trafficDirection: 'EGRESS',
            trafficMirrorFilterId: filter.ref,
            description: 'Accept all outbound traffic'
        });
        for (let block_num = 0; block_num < props.vpcCidrs.length; block_num++) {
            new ec2.CfnTrafficMirrorFilterRule(this, `FRule-RejectLocalInbound-${block_num + 1}`, {
                destinationCidrBlock: '0.0.0.0/0',
                ruleAction: 'REJECT',
                ruleNumber: 10 + block_num,
                sourceCidrBlock: props.vpcCidrs[block_num],
                trafficDirection: 'INGRESS',
                trafficMirrorFilterId: filter.ref,
                description: 'Reject all intra-VPC traffic'
            });
        }
        new ec2.CfnTrafficMirrorFilterRule(this, 'FRule-AllowOtherInbound', {
            destinationCidrBlock: '0.0.0.0/0',
            ruleAction: 'ACCEPT',
            ruleNumber: 20,
            sourceCidrBlock: '0.0.0.0/0',
            trafficDirection: 'INGRESS',
            trafficMirrorFilterId: filter.ref,
            description: 'Accept all inbound traffic'
        });

        /**
         * Configure the resources to listen for raw AWS Service events in the User VPC Account/Region and convert
         * those events into something more actionable for our system
         */

        const vpcBus = new events.EventBus(this, 'VpcBus', {});

        // Create the Lambda that listen for AWS Service events on the default bus and transform them into events we
        // can action
        const listenerLambda = new lambda.Function(this, 'AwsEventListenerLambda', {
            functionName: `${props.clusterName}-AwsEventListener-${props.vpcId}`,
            runtime: lambda.Runtime.PYTHON_3_9,
            code: lambda.Code.fromAsset(path.resolve(__dirname, '..', '..', 'manage_arkime'), {
                bundling: {
                    image: lambda.Runtime.PYTHON_3_9.bundlingImage,
                    command: [
                        'bash', '-c',
                        'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
                    ],
                },
            }),
            handler: 'lambda_handlers.aws_event_listener_handler',
            timeout:  Duration.seconds(30), // Something has gone very wrong if this is exceeded,
            environment: {
                EVENT_BUS_ARN: vpcBus.eventBusArn,
                CLUSTER_NAME: props.clusterName,
                VPC_ID: props.vpcId,
                TRAFFIC_FILTER_ID: filter.ref,
                MIRROR_VNI: props.mirrorVni,
            }
        });
        listenerLambda.addToRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    'events:PutEvents'
                ],
                resources: [
                    `${vpcBus.eventBusArn}`
                ]
            })
        );
        listenerLambda.addToRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    'ec2:DescribeInstances'
                ],
                resources: ['*']
            })
        );

        // Make a human-readable log of the raw AWS Service events we're proccessing
        const vpcLogGroup = new logs.LogGroup(this, 'LogGroup', {
            logGroupName: `${props.clusterName}-ArkimeInputEvents-${props.vpcId}`,
            removalPolicy: RemovalPolicy.DESTROY // This is intended for debugging
        });

        // Capture Fargate stop/start events for processing
        new events.Rule(this, 'RuleFargateEvents', {
            eventBus: undefined, // We want to listen to the Account/Region's default bus
            eventPattern: {
                source: ['aws.ecs'],
                detailType: ['ECS Task State Change'],
                detail: {
                    attachments: {
                        details: {
                            name: ['subnetId'],
                            value: props.subnetIds // Only care about subnets in *this* User VPC
                        }
                    },
                    launchType: ['FARGATE'],
                    lastStatus: ['RUNNING', 'STOPPED']
                }
            },
            targets: [
                new targets.CloudWatchLogGroup(vpcLogGroup),
                new targets.LambdaFunction(listenerLambda)
            ]
        });

        // Capture EC2 instance start/stop events.  This should cover one-off instance creation, EC2 Autoscaling
        // activities, and ECS-on-EC2.  All three of those situations map to an ENI being created or destroyed when
        // a concrete instance starts/stops, regardless of how many other steps/events are involved in the process.
        //
        // Unfortunately, this event does not give us the information we need to pre-screen it at the Rule level so
        // we have to check if it applies to our VPC in our Lambda code.
        new events.Rule(this, 'RuleEc2Events', {
            eventBus: undefined, // We want to listen to the Account/Region's default bus
            eventPattern: {
                source: ['aws.ec2'],
                detailType: ['EC2 Instance State-change Notification'],
                detail: {
                    state: ['running', 'shutting-down']
                }
            },
            targets: [
                new targets.CloudWatchLogGroup(vpcLogGroup),
                new targets.LambdaFunction(listenerLambda)
            ]
        });

        /**
         * Configure the resources required for event-based mirroring configuration
         */
        // Archive Arkime events related to this User VPC to enable replay, with a focus on shorter-term debugging
        vpcBus.archive('Archive', {
            archiveName: `${props.clusterName}-Arkime-${props.vpcId}`,
            description: `Archive of Arkime events for VPC ${props.vpcId}`,
            eventPattern: {
                source: [constants.EVENT_SOURCE],
                detail: {
                    'vpc_id': events.Match.exactString(props.vpcId)
                }
            },
            retention: Duration.days(30),
        });

        // Create the Lambda that will set up the traffic mirroring for ENIs in our VPC
        const createLambda = new lambda.Function(this, 'CreateEniMirrorLambda', {
            functionName: `${props.clusterName}-CreateEniMirror-${props.vpcId}`,
            runtime: lambda.Runtime.PYTHON_3_9,
            code: lambda.Code.fromAsset(path.resolve(__dirname, '..', '..', 'manage_arkime'), {
                bundling: {
                    image: lambda.Runtime.PYTHON_3_9.bundlingImage,
                    command: [
                        'bash', '-c',
                        'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
                    ],
                },
            }),
            handler: 'lambda_handlers.create_eni_mirror_handler',
            timeout:  Duration.seconds(30), // Something has gone very wrong if this is exceeded
        });
        createLambda.addToRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    // TODO: Should scope this down.
                    // We need ec2:CreateTrafficMirrorSession in order to set up our session, but whenever I add *just*
                    // that, I get an UnauthorizedOperation.  The docs say that's all that should be required, but the
                    // documentation appears wrong or there's something extra mysterious going on here.  Even CloudTrail
                    // indicates the only call being made is CreateTrafficMirrorSession, but it's still failing.  The
                    // exception also doesn't indicate otherwise.
                    // See: https://docs.aws.amazon.com/vpc/latest/mirroring/traffic-mirroring-security.html
                    'ec2:*',
                ],
                resources: [
                    `arn:aws:ec2:${this.region}:${this.account}:*`
                ]
            })
        );
        createLambda.addToRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    'ssm:GetParameter',
                    'ssm:PutParameter',
                ],
                resources: [
                    `arn:aws:ssm:${this.region}:${this.account}:*`
                ]
            })
        );
        createLambda.addToRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    'cloudwatch:PutMetricData',
                ],
                resources: [
                    '*'
                ]
            })
        );

        // Create a rule to funnel appropriate events to our setup lambda
        const createRule = new events.Rule(this, 'RuleCreateEniMirror', {
            eventBus: vpcBus,
            eventPattern: {
                source: [constants.EVENT_SOURCE],
                detailType: [constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR],
                detail: {
                    'vpc_id': events.Match.exactString(props.vpcId)
                }
            },
            targets: [new targets.LambdaFunction(createLambda)]
        });
        createRule.node.addDependency(vpcBus);

        // Create the Lambda that will tear down the traffic mirroring for ENIs in our VPC
        const destroyLambda = new lambda.Function(this, 'DestroyEniMirrorLambda', {
            functionName: `${props.clusterName}-DestroyEniMirror-${props.vpcId}`,
            runtime: lambda.Runtime.PYTHON_3_9,
            code: lambda.Code.fromAsset(path.resolve(__dirname, '..', '..', 'manage_arkime'), {
                bundling: {
                    image: lambda.Runtime.PYTHON_3_9.bundlingImage,
                    command: [
                        'bash', '-c',
                        'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
                    ],
                },
            }),
            handler: 'lambda_handlers.destroy_eni_mirror_handler',
            timeout:  Duration.seconds(30), // Something has gone very wrong if this is exceeded
        });
        destroyLambda.addToRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    // TODO: Should scope this down.
                    // Just need ec2:DeleteTrafficMirroringSession, but failing similar to the Create Lambda
                    'ec2:*',
                ],
                resources: [
                    `arn:aws:ec2:${this.region}:${this.account}:*`
                ]
            })
        );
        destroyLambda.addToRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    'ssm:GetParameter',
                    'ssm:DeleteParameter',
                ],
                resources: [
                    `arn:aws:ssm:${this.region}:${this.account}:*`
                ]
            })
        );
        destroyLambda.addToRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    'cloudwatch:PutMetricData',
                ],
                resources: [
                    '*'
                ]
            })
        );

        // Create a rule to funnel appropriate events to our teardwon lambda
        const destroyRule = new events.Rule(this, 'RuleDestroyEniMirror', {
            eventBus: vpcBus,
            eventPattern: {
                source: [constants.EVENT_SOURCE],
                detailType: [constants.EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR],
                detail: {
                    'vpc_id': events.Match.exactString(props.vpcId)
                }
            },
            targets: [new targets.LambdaFunction(destroyLambda)]
        });
        destroyRule.node.addDependency(vpcBus);

        // This SSM parameter will enable us share the details of our VPC-specific Capture setup
        const vpcParamValue: VpcSsmValue = {
            busArn: vpcBus.eventBusArn,
            mirrorFilterId: filter.ref,
            mirrorVni: props.mirrorVni,
            vpcId: props.vpcId,
        };
        const vpcParam = new ssm.StringParameter(this, `VpcParam-${props.vpcId}`, {
            allowedPattern: '.*',
            description: 'The VPC\'s details',
            parameterName: props.vpcSsmParamName,
            stringValue: JSON.stringify(vpcParamValue),
            tier: ssm.ParameterTier.STANDARD,
        });
        vpcParam.node.addDependency(filter);
    }
}
