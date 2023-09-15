import * as cdk from 'aws-cdk-lib';
import * as autoscaling from 'aws-cdk-lib/aws-autoscaling';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as path from 'path'
import { Construct } from 'constructs';

import * as constants from '../core/constants';
import * as plan from '../core/context-types';
import {CaptureSsmValue, ClusterSsmValue} from '../core/ssm-wrangling';
import * as types from '../core/context-types';

export interface CaptureNodesStackProps extends cdk.StackProps {
    readonly captureBucket: s3.Bucket;
    readonly captureBucketKey: kms.Key;
    readonly captureVpc: ec2.Vpc;
    readonly clusterConfigBucketName: string;
    readonly clusterName: string;
    readonly osDomain: opensearch.Domain;
    readonly osPassword: secretsmanager.Secret;
    readonly planCluster: plan.ClusterPlan;
    readonly ssmParamNameCaptureConfig: string;
    readonly ssmParamNameCaptureDetails: string;
    readonly ssmParamNameCluster: string;
    readonly userConfig: types.UserConfig;
}

export class CaptureNodesStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: CaptureNodesStackProps) {
        super(scope, id, props);

        /**
         * Begin configuration of the Gateway Load Balancer and associated resources
         */
        const gwlb = new elbv2.CfnLoadBalancer(this, 'GatewayLoadBalancer', {
            type: 'gateway',
            subnets: props.captureVpc.selectSubnets({subnetType: ec2.SubnetType.PUBLIC}).subnetIds,
            loadBalancerAttributes: [
                {
                    key: 'load_balancing.cross_zone.enabled',
                    value: 'true', // IMO, resilience is more important than latency here
                }
            ],
        });

        // Per docs, the protocol (GENEVE) and port (6081) MUST be these.
        // See: https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/target-groups.html
        const healthCheckPort = 4242; // arbitrarily chosen
        const gwlbTargetGroup = new elbv2.CfnTargetGroup(this, 'GWLBTargetGroup', {
            protocol: 'GENEVE',
            port: 6081,
            vpcId: props.captureVpc.vpcId,
            targetType: 'instance',
            healthCheckProtocol: 'TCP',
            healthCheckPort: healthCheckPort.toString(),
        });

        const gwlbListener = new elbv2.CfnListener(this, 'GWLBListener', {
            loadBalancerArn: gwlb.ref,
            defaultActions: [
                {
                    targetGroupArn: gwlbTargetGroup.ref,
                    type: 'forward',
                },
            ],
        });
        gwlbListener.node.addDependency(gwlb);
        gwlbListener.node.addDependency(gwlbTargetGroup);

        /**
         * Define our ECS Cluster and its associated resources
         */

        // Create an ECS Cluster that runs fleet of Arkime Capture Nodes.  We use EC2 as our compute because Gateway
        // Load Balancers do not properly integrate with ECS Fargate.
        const autoScalingGroup = new autoscaling.AutoScalingGroup(this, 'ASG', {
            vpc: props.captureVpc,
            instanceType: new ec2.InstanceType(props.planCluster.captureNodes.instanceType),
            machineImage: ecs.EcsOptimizedImage.amazonLinux2(),
            desiredCapacity: props.planCluster.captureNodes.desiredCount,
            minCapacity: props.planCluster.captureNodes.minCount,
            maxCapacity: props.planCluster.captureNodes.maxCount
        });

        const asgSecurityGroup = new ec2.SecurityGroup(this, 'ASGSecurityGroup', {
            vpc: props.captureVpc,
            description: 'Control traffic to the Capture Nodes',
            allowAllOutbound: true
        });
        asgSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(healthCheckPort), 'Enable LB Health Checks');
        asgSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.udp(6081), 'Enable mirrored traffic');
        autoScalingGroup.addSecurityGroup(asgSecurityGroup);

        // There might be a better way to do this, but the escape hatch exists for a reason.  We need to associate the
        // ASG with the GWLB Target Group so that our Containers get registered with the LB, and we don't have a
        // built-in method to do so given our usage of the L1 Constructs for the GWLB stuff.  Normally we'd call
        // attachToApplicationTargetGroup().
        // See: https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_autoscaling.CfnAutoScalingGroup.html#targetgrouparns
        const cfnAsg = autoScalingGroup.node.defaultChild as autoscaling.CfnAutoScalingGroup;
        cfnAsg.targetGroupArns = [
            gwlbTargetGroup.ref
        ];
        cfnAsg.node.addDependency(gwlbListener);

        // Key to encrypt SSM traffic when using ECS Exec to shell into the container
        const kmsEncryptionKey = new kms.Key(this, 'ECSClusterKey', {
            enableKeyRotation: true,
        });

        const cluster = new ecs.Cluster(this, 'Cluster', {
            vpc: props.captureVpc,
            executeCommandConfiguration: { kmsKey: kmsEncryptionKey }
        });

        const capacityProvider = new ecs.AsgCapacityProvider(this, 'AsgCapacityProvider', {
            autoScalingGroup: autoScalingGroup,
            enableManagedTerminationProtection: false
        });
        cluster.addAsgCapacityProvider(capacityProvider);

        const taskDefinition = new ecs.Ec2TaskDefinition(this, 'TaskDef', {
            // The Gateway Load Balancer register our ASG's instances as its targets, and directs traffic to those
            // instances at their host-level IP/PORT.  To enable our ECS Container to receive traffic from the LB (and
            // respond to its health checks), we need to directly map the instance's ports to our containers.  That
            // means we can use either the HOST or BRIDGE modes here, but not VPC (as far as I know).
            //
            // See: https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/networking-networkmode.html
            networkMode: ecs.NetworkMode.BRIDGE,
        });
        taskDefinition.addToTaskRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: ['kms:Decrypt'], // Required for ECS Exec & shelling into the container
                resources: [kmsEncryptionKey.keyArn]
            }),
        );
        taskDefinition.addToTaskRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: ['ssm:GetParameter'], // Container pulls configuration info from Parameter Store
                resources: [`arn:aws:ssm:${this.region}:${this.account}:parameter*`]
            }),
        );
        taskDefinition.addToTaskRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: ['s3:GetObject'], // Container pulls configuration from the Config S3 Bucket
                resources: [`arn:aws:s3:::${props.clusterConfigBucketName}/*`]
            }),
        );
        props.osPassword.grantRead(taskDefinition.taskRole);
        props.captureBucket.grantReadWrite(taskDefinition.taskRole);
        props.captureBucketKey.grantEncryptDecrypt(taskDefinition.taskRole);

        // Enable NET_ADMIN capability so we use ip commands and /dev/net items work
        const kernelCapabilitiesProperty: ecs.CfnTaskDefinition.KernelCapabilitiesProperty = {
            add: ['NET_ADMIN'],
        };

        const linuxParameters = new ecs.LinuxParameters(this, 'LinuxParameters');
        linuxParameters.addCapabilities(ecs.Capability.NET_ADMIN);

        const container = taskDefinition.addContainer('CaptureContainer', {
            image: ecs.ContainerImage.fromAsset(path.resolve(__dirname, '..', '..', 'docker-capture-node')),
            logging: new ecs.AwsLogDriver({ streamPrefix: 'CaptureNodes', mode: ecs.AwsLogDriverMode.NON_BLOCKING }),
            environment: {
                'AWS_REGION': this.region, // Seems not to be defined in this container, strangely
                'BUCKET_NAME': props.captureBucket.bucketName,
                'CAPTURE_CONFIG_SSM_PARAM': props.ssmParamNameCaptureConfig,
                'CLUSTER_NAME': props.clusterName,
                'LB_HEALTH_PORT': healthCheckPort.toString(),
                'OPENSEARCH_ENDPOINT': props.osDomain.domainEndpoint,
                'OPENSEARCH_SECRET_ARN': props.osPassword.secretArn,
                'S3_STORAGE_CLASS': props.planCluster.s3.pcapStorageClass,
            },
            cpu: props.planCluster.ecsResources.cpu,
            memoryLimitMiB: props.planCluster.ecsResources.memory,
            portMappings: [
                { containerPort: 6081, hostPort: 6081, protocol: ecs.Protocol.UDP},
                { containerPort: healthCheckPort, hostPort: healthCheckPort, protocol: ecs.Protocol.TCP},
            ],
            linuxParameters: linuxParameters,
        });

        const service = new ecs.Ec2Service(this, 'Service', {
            cluster,
            taskDefinition,
            desiredCount: 1,
            minHealthyPercent: 0, // TODO: Speeds up test deployments but need to change to something safer
            enableExecuteCommand: true
        });

        // TODO: Fix autoscaling.  We need our ECS Tasks to scale together with our EC2 fleet since we are only placing
        // a single container on each instance due to using the HOST network mode.
        // See: https://stackoverflow.com/questions/72839842/aws-ecs-auto-scaling-an-ec2-auto-scaling-group-with-single-container-hosts
        const scaling = service.autoScaleTaskCount({ maxCapacity: 10 });
        scaling.scaleOnCpuUtilization('CpuScaling', {
            targetUtilizationPercent: 60,
        });
        scaling.scaleOnMemoryUtilization('MemoryScaling', {
            targetUtilizationPercent: 60,
        });

        /**
         * Set up our Capture setup to use VPC Endpoints
         */
        const gwlbEndpointService = new ec2.CfnVPCEndpointService(this, 'VPCEndpointService', {
            gatewayLoadBalancerArns: [gwlb.ref],

            // Allows us to bypass the need to confirm acceptance of each endpoint we create, but means we are limited
            // to our own account (I think)
            acceptanceRequired: false,
        });

        new ec2.CfnVPCEndpointServicePermissions(this, 'EndpointServicePermissions', {
            serviceId: gwlbEndpointService.ref,
            allowedPrincipals: [`arn:aws:iam::${this.account}:root`],
        });

        /**
         * Set up shared resources for event-based management of mirroring.
         */
        const clusterBus = new events.EventBus(this, 'ClusterBus', {})

        // Store a copy of the Arkime events that occur for later replay
        clusterBus.archive('Archive', {
            archiveName: `Arkime-${props.clusterName}`,
            description: `Archive of Arkime events for Cluster ${props.clusterName}`,
            eventPattern: {
                source: [constants.EVENT_SOURCE],
            },
            retention: cdk.Duration.days(365), // Arbitrarily chosen
        });

        // Make a human-readable log of the Arkime events that occur on the bus
        const clusterLogGroup = new logs.LogGroup(this, 'LogGroup', {
            logGroupName: `Arkime-${props.clusterName}`,
            removalPolicy: cdk.RemovalPolicy.DESTROY // The archive contains the real events
        });
        const logClusterEventsRule = new events.Rule(this, 'RuleLogClusterEvents', {
            eventBus: clusterBus,
            eventPattern: {
                source: [constants.EVENT_SOURCE],
            },
            targets: [new targets.CloudWatchLogGroup(clusterLogGroup)]
        });

        /**
         * This SSM parameter will enable us share the details of our Cluster.
         */
        const clusterParamValue: ClusterSsmValue = {
            busArn: clusterBus.eventBusArn,
            busName: clusterBus.eventBusName,
            clusterName: props.clusterName,
            osDomainName: props.osDomain.domainName,
            vpceServiceId: gwlbEndpointService.ref,
            capacityPlan: props.planCluster,
            userConfig: props.userConfig
        }
        const clusterParam = new ssm.StringParameter(this, 'ClusterParam', {
            allowedPattern: '.*',
            description: 'The Cluster\'s details',
            parameterName: props.ssmParamNameCluster,
            stringValue: JSON.stringify(clusterParamValue),
            tier: ssm.ParameterTier.STANDARD,
        });
        clusterParam.node.addDependency(gwlbEndpointService);
        clusterParam.node.addDependency(clusterBus);

        /**
         * This SSM parameter will enable us share the details of our Capture Setup.
         */
        const captureParamValue: CaptureSsmValue = {
            ecsCluster: service.cluster.clusterName,
            ecsService: service.serviceName,
        }
        const captureParam = new ssm.StringParameter(this, 'CaptureDetails', {
            description: 'Details about the Arkime Capture Nodes',
            parameterName: props.ssmParamNameCaptureDetails,
            stringValue: JSON.stringify(captureParamValue),
            tier: ssm.ParameterTier.STANDARD,
        });
        captureParam.node.addDependency(service);

        /**
         * Create the Lambda set up the ISM policy for the OpenSearch Domain.  It receives events via a rule on the
         * Cluster Event Bus.
        */
        const configureIsmLambda = new lambda.Function(this, 'ConfigureIsmLambda', {
            vpc: props.captureVpc,
            functionName: `${props.clusterName}-ConfigureIsm`,
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
            handler: 'lambda_handlers.configure_ism_handler',
            timeout:  cdk.Duration.seconds(30), // Something has gone very wrong if this is exceeded,
            environment: {
                'CLUSTER_NAME': props.clusterName,
                'OPENSEARCH_ENDPOINT': props.osDomain.domainEndpoint,
                'OPENSEARCH_SECRET_ARN': props.osPassword.secretArn,
            },
        });
        configureIsmLambda.addToRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    'secretsmanager:GetSecretValue',
                ],
                resources: [
                    `${props.osPassword.secretArn}`,
                ]
            })
        );
        configureIsmLambda.addToRolePolicy(
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

        // Create a rule to funnel appropriate events to our configure Lambda
        const configureRule = new events.Rule(this, 'RuleConfigureIsm', {
            eventBus: clusterBus,
            eventPattern: {
                source: [constants.EVENT_SOURCE],
                detailType: [constants.EVENT_DETAIL_TYPE_CONFIGURE_ISM],
            },
            targets: [new targets.LambdaFunction(configureIsmLambda)]
        });
        configureRule.node.addDependency(clusterBus);
    }
}
