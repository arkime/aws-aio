import assert = require('assert');

import { Construct } from 'constructs';
import { Duration, Stack, StackProps } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as path from 'path'

import {SubnetSsmValue, VpcSsmValue} from '../core/ssm-wrangling'
import * as constants from '../core/constants'

export interface VpcMirrorStackProps extends StackProps {
    readonly eventBusArn: string;
    readonly subnetIds: string[];
    readonly subnetSsmParamNames: string[];
    readonly vpcId: string;
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
            assert.ok(subnetParamName.includes(subnetId), `Expected Subnet SSM Param ${subnetParamName} to contain Subnet ID ${subnetId}`)

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
            const subnetParamValue: SubnetSsmValue = {mirrorTargetId: mirrorTarget.ref, subnetId: subnetId, vpcEndpointId: vpcEndpoint.ref}
            const subnetParam = new ssm.StringParameter(this, `SubnetParam-${subnetId}`, {
                allowedPattern: '.*',
                description: 'The Subnet\'s details',
                parameterName: subnetParamName,
                stringValue: JSON.stringify(subnetParamValue),
                tier: ssm.ParameterTier.STANDARD,
            });
            subnetParam.node.addDependency(mirrorTarget);
        };

        // Let's mirror all non-local VPC traffic
        // See: https://docs.aws.amazon.com/vpc/latest/mirroring/tm-example-non-vpc.html
        const filter = new ec2.CfnTrafficMirrorFilter(this, `Filter`, {
            description: 'Mirror non-local VPC traffic',
            tags: [{key: 'Name', value: props.vpcId}]
        });
        new ec2.CfnTrafficMirrorFilterRule(this, `FRule-RejectLocalOutbound`, {
            destinationCidrBlock: '10.0.0.0/16', // TODO: Need to figure this out instead of hardcode
            ruleAction: 'REJECT',
            ruleNumber: 10,
            sourceCidrBlock: '0.0.0.0/0',
            trafficDirection: 'EGRESS',
            trafficMirrorFilterId: filter.ref,
            description: 'Reject all intra-VPC traffic'
        });
        new ec2.CfnTrafficMirrorFilterRule(this, `FRule-AllowOtherOutbound`, {
            destinationCidrBlock: '0.0.0.0/0', // TODO: Need to figure this out instead of hardcode
            ruleAction: 'ACCEPT',
            ruleNumber: 20,
            sourceCidrBlock: '0.0.0.0/0',
            trafficDirection: 'EGRESS',
            trafficMirrorFilterId: filter.ref,
            description: 'Accept all outbound traffic'
        });

        new ec2.CfnTrafficMirrorFilterRule(this, `FRule-RejectLocalInbound`, {
            destinationCidrBlock: '0.0.0.0/0',
            ruleAction: 'REJECT',
            ruleNumber: 10,
            sourceCidrBlock: '10.0.0.0/16', // TODO: Need to figure this out instead of hardcode
            trafficDirection: 'INGRESS',
            trafficMirrorFilterId: filter.ref,
            description: 'Reject all intra-VPC traffic'
        });
        new ec2.CfnTrafficMirrorFilterRule(this, `FRule-AllowOtherInbound`, {
            destinationCidrBlock: '0.0.0.0/0',
            ruleAction: 'ACCEPT',
            ruleNumber: 20,
            sourceCidrBlock: '0.0.0.0/0',
            trafficDirection: 'INGRESS',
            trafficMirrorFilterId: filter.ref,
            description: 'Accept all inbound traffic'
        });

        // This SSM parameter will enable us share the details of our VPC-specific Capture setup
        const vpcParamValue: VpcSsmValue = {mirrorFilterId: filter.ref, mirrorVni: props.mirrorVni, vpcId: props.vpcId}
        const vpcParam = new ssm.StringParameter(this, `VpcParam-${props.vpcId}`, {
            allowedPattern: '.*',
            description: 'The VPC\'s details',
            parameterName: props.vpcSsmParamName,
            stringValue: JSON.stringify(vpcParamValue),
            tier: ssm.ParameterTier.STANDARD,
        });
        vpcParam.node.addDependency(filter);

        /**
         * Configure the resources required for event-based mirroring configuration
         */
        // Get a handle to the cluster event bus
        const clusterBus = events.EventBus.fromEventBusArn(this, 'ClusterBus', props.eventBusArn);

        // Archive Arkime events related to this User VPC to enable replay, with a focus on shorter-term debugging
        clusterBus.archive('Archive', {
            archiveName: `Arkime-${props.vpcId}`,
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
            functionName: `CreateEniMirror-${props.vpcId}`,
            runtime: lambda.Runtime.PYTHON_3_9,
            code: lambda.Code.fromAsset(path.resolve(__dirname, '..', '..', 'manage_arkime')),            
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
                    "*"
                ]
            })
        );

        // Create a rule to funnel appropriate events to our setup lambda
        const createRule = new events.Rule(this, 'RuleCreateEniMirror', {
            eventBus: clusterBus,
            eventPattern: {
                source: [constants.EVENT_SOURCE],
                detailType: [constants.EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR],
                detail: {
                    'vpc_id': events.Match.exactString(props.vpcId)
                }
            },
            targets: [new targets.LambdaFunction(createLambda)]
        });
        createRule.node.addDependency(clusterBus);

        // Create the Lambda that will tear down the traffic mirroring for ENIs in our VPC
        const destroyLambda = new lambda.Function(this, 'DestroyEniMirrorLambda', {
            functionName: `DestroyEniMirror-${props.vpcId}`,
            runtime: lambda.Runtime.PYTHON_3_9,
            code: lambda.Code.fromAsset(path.resolve(__dirname, '..', '..', 'manage_arkime')),            
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
                    'cloudwatch:PutMetricData',
                    'ssm:GetParameter',
                    'ssm:DeleteParameter',
                ],
                resources: [
                    `arn:aws:ssm:${this.region}:${this.account}:*`
                ]
            })
        );

        // Create a rule to funnel appropriate events to our teardwon lambda
        const destroyRule = new events.Rule(this, 'RuleDestroyEniMirror', {
            eventBus: clusterBus,
            eventPattern: {
                source: [constants.EVENT_SOURCE],
                detailType: [constants.EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR],
                detail: {
                    'vpc_id': events.Match.exactString(props.vpcId)
                }
            },
            targets: [new targets.LambdaFunction(destroyLambda)]
        });
        destroyRule.node.addDependency(clusterBus);
    }
}