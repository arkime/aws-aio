import * as cdk from "aws-cdk-lib";
import * as autoscaling from "aws-cdk-lib/aws-autoscaling";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as iam from "aws-cdk-lib/aws-iam";
import * as kms from "aws-cdk-lib/aws-kms";
import * as opensearch from "aws-cdk-lib/aws-opensearchservice";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as ssm from "aws-cdk-lib/aws-ssm";
import * as path from "path"
import { Construct } from "constructs";

export interface CaptureNodesStackProps extends cdk.StackProps {
    readonly captureBucket: s3.Bucket;
    readonly captureVpc: ec2.Vpc;
    readonly clusterName: string;
    readonly osDomain: opensearch.Domain;
    readonly osPassword: secretsmanager.Secret;
}

export class CaptureNodesStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: CaptureNodesStackProps) {
        super(scope, id, props);

        /**
         * Begin configuration of the Gateway Load Balancer and associated resources
         */
        const gwlb = new elbv2.CfnLoadBalancer(this, "GatewayLoadBalancer", {
            type: "gateway",
            subnets: props.captureVpc.selectSubnets({subnetType: ec2.SubnetType.PUBLIC}).subnetIds,
            loadBalancerAttributes: [
                {
                    key: "load_balancing.cross_zone.enabled",
                    value: "true", // IMO, resilience is more important than latency here
                }
            ],
        });

        // Per docs, the protocol and port MUST be these.
        // See: https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/target-groups.html
        const gwlbTargetGroup = new elbv2.CfnTargetGroup(this, "GWLBTargetGroup", {
            protocol: "GENEVE",
            port: 6081,
            vpcId: props.captureVpc.vpcId,
            targetType: "instance",

            // TODO: Needs to be configured correctly
            // healthCheckProtocol: "TCP",
            // healthCheckPort: "8032",
        });
        
        const gwlbListener = new elbv2.CfnListener(this, "GWLBListener", {
            loadBalancerArn: gwlb.ref,
            defaultActions: [
                {
                    targetGroupArn: gwlbTargetGroup.ref,
                    type: "forward",
                },
            ],
        });
        gwlbListener.node.addDependency(gwlb);
        gwlbListener.node.addDependency(gwlbTargetGroup);
        
        /**
         * Define our ECS Cluster and its associated resources
         */

        // Create an ECS Cluster that runs fleet of Arkime Capture Nodes
        const autoScalingGroup = new autoscaling.AutoScalingGroup(this, "ASG", {
            vpc: props.captureVpc,
            instanceType: new ec2.InstanceType("m5.xlarge"),
            machineImage: ecs.EcsOptimizedImage.amazonLinux2(),
            desiredCapacity: 3,
        });

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
        const ksmEncryptionKey = new kms.Key(this, "ECSClusterKey", {
            enableKeyRotation: true,
        });
        
        const cluster = new ecs.Cluster(this, "Cluster", {
            vpc: props.captureVpc,
            executeCommandConfiguration: { kmsKey: ksmEncryptionKey }
        });
        
        const capacityProvider = new ecs.AsgCapacityProvider(this, "AsgCapacityProvider", {
            autoScalingGroup,
        });
        cluster.addAsgCapacityProvider(capacityProvider);

        const taskDefinition = new ecs.Ec2TaskDefinition(this, "TaskDef", {
            networkMode: ecs.NetworkMode.AWS_VPC,
        });
        taskDefinition.addToTaskRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: ["kms:Decrypt"], // Required for ECS Exec & shelling into the container
                resources: [ksmEncryptionKey.keyArn]
            }),
        );
        props.osPassword.grantRead(taskDefinition.taskRole);

        // This SSM parameter will be used to track whether the Capture Setup has been initialized or not.  Currently,
        // this means whether Arkime's initialization scripts have been invoked against the OpenSearch Domain.
        const initializedParam = new ssm.StringParameter(this, "IsInitialized", {
            allowedPattern: "true|false",
            description: "Whether the capture setup is initialized or not",
            parameterName: `${props.clusterName}-Initialized`,
            stringValue: "false",
            tier: ssm.ParameterTier.STANDARD,
        });
        initializedParam.grantRead(taskDefinition.taskRole);
        initializedParam.grantWrite(taskDefinition.taskRole);
        
        const container = taskDefinition.addContainer("CaptureContainer", {
            image: ecs.ContainerImage.fromAsset(path.resolve(__dirname, "..", "..", "docker-capture-node")),
            logging: new ecs.AwsLogDriver({ streamPrefix: "CaptureNodes", mode: ecs.AwsLogDriverMode.NON_BLOCKING }),
            environment: {
                "CLUSTER_NAME": props.clusterName,
                "SSM_INITIALIZED_PARAM": initializedParam.parameterName,
                "OPENSEARCH_ENDPOINT": props.osDomain.domainEndpoint,
                "OPENSEARCH_SECRET_ARN": props.osPassword.secretArn,
            },
            memoryLimitMiB: 4096,
            portMappings: [
                // TODO: Pretty sure this is wrong; get real numbers.  This is the GWLB port # and protocol.
                { containerPort: 6081, hostPort: 6081, protocol: ecs.Protocol.UDP},
            ],
        });
        
        const service = new ecs.Ec2Service(this, "Service", {
            cluster,
            taskDefinition,

            // TODO: The LB hits the containers to see if they are healthy, but our containers aren't configured to
            // respond.  This causes the ECS Service Cfn resource to wait for 3 hours then Cfn kills the deployment.
            desiredCount: 0,
            enableExecuteCommand: true
        });
        
        const scaling = service.autoScaleTaskCount({ maxCapacity: 10 });
        scaling.scaleOnCpuUtilization("CpuScaling", {
            targetUtilizationPercent: 60,
        });
        scaling.scaleOnMemoryUtilization("MemoryScaling", {
            targetUtilizationPercent: 60,
        });

        /**
         * Set up our Capture setup to use VPC Endpoints
         */
        const gwlbEndpointService = new ec2.CfnVPCEndpointService(this, "VPCEndpointService", {
            gatewayLoadBalancerArns: [gwlb.ref],

            // Allows us to bypass the need to confirm acceptance of each endpoint we create, but means we are limited
            // to our own account
            acceptanceRequired: false,
        });

        new ec2.CfnVPCEndpointServicePermissions(this, "EndpointServicePermissions", {
            serviceId: gwlbEndpointService.ref,
            allowedPrincipals: [`arn:aws:iam::${this.account}:root`],
        });
    }
}
