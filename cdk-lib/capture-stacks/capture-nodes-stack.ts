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

import {ClusterSsmValue} from "../core/ssm-wrangling"

export interface CaptureNodesStackProps extends cdk.StackProps {
    readonly captureBucket: s3.Bucket;
    readonly captureVpc: ec2.Vpc;
    readonly clusterName: string;
    readonly osDomain: opensearch.Domain;
    readonly osPassword: secretsmanager.Secret;
    readonly ssmParamNameCluster: string;
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

        // Per docs, the protocol (GENEVE) and port (6081) MUST be these.
        // See: https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/target-groups.html
        const healthCheckPort = 4242; // arbitrarily chosen
        const gwlbTargetGroup = new elbv2.CfnTargetGroup(this, "GWLBTargetGroup", {
            protocol: "GENEVE",
            port: 6081,
            vpcId: props.captureVpc.vpcId,
            targetType: "instance",
            healthCheckProtocol: "TCP",
            healthCheckPort: healthCheckPort.toString(),
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

        // Create an ECS Cluster that runs fleet of Arkime Capture Nodes.  We use EC2 as our compute because Gateway
        // Load Balancers do not properly integrate with ECS Fargate.
        const autoScalingGroup = new autoscaling.AutoScalingGroup(this, "ASG", {
            vpc: props.captureVpc,
            instanceType: new ec2.InstanceType("m5.xlarge"), // Arbitrarily chosen
            machineImage: ecs.EcsOptimizedImage.amazonLinux2(),
            desiredCapacity: 1,
            minCapacity: 1,
            maxCapacity: 10 // Arbitrarily chosen
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
            // The Gateway Load Balancer register our ASG's instances as its targets, and directs traffic to those
            // instances at their host-level IP/PORT.  To enable our ECS Container to receive traffic from the LB (and
            // respond to its health checks), we need to directly map the instance's ports to our containers.  That
            // means we can use either the HOST or BRIDGE modes here, but not VPC (as far as I know).
            // 
            // See: https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/networking-networkmode.html
            networkMode: ecs.NetworkMode.HOST,
        });
        taskDefinition.addToTaskRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: ["kms:Decrypt"], // Required for ECS Exec & shelling into the container
                resources: [ksmEncryptionKey.keyArn]
            }),
        );
        props.osPassword.grantRead(taskDefinition.taskRole);
        props.captureBucket.grantReadWrite(taskDefinition.taskRole);
        
        const container = taskDefinition.addContainer("CaptureContainer", {
            image: ecs.ContainerImage.fromAsset(path.resolve(__dirname, "..", "..", "docker-capture-node")),
            logging: new ecs.AwsLogDriver({ streamPrefix: "CaptureNodes", mode: ecs.AwsLogDriverMode.NON_BLOCKING }),
            environment: {
                "AWS_REGION": this.region, // Seems not to be defined in this container, strangely
                "CLUSTER_NAME": props.clusterName,
                "LB_HEALTH_PORT": healthCheckPort.toString(),
                "OPENSEARCH_ENDPOINT": props.osDomain.domainEndpoint,
                "OPENSEARCH_SECRET_ARN": props.osPassword.secretArn,
            },
            cpu: 4, // one full m5.xlarge
            memoryLimitMiB: 16384, // one full m5.xlarge
            portMappings: [
                { containerPort: 6081, hostPort: 6081, protocol: ecs.Protocol.UDP},
                { containerPort: healthCheckPort, hostPort: healthCheckPort, protocol: ecs.Protocol.TCP},
            ],
        });
        
        const service = new ecs.Ec2Service(this, "Service", {
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
            // to our own account (I think)
            acceptanceRequired: false,
        });

        new ec2.CfnVPCEndpointServicePermissions(this, "EndpointServicePermissions", {
            serviceId: gwlbEndpointService.ref,
            allowedPrincipals: [`arn:aws:iam::${this.account}:root`],
        });

        // This SSM parameter will enable us share the details of our Capture setup.
        const clusterParamValue: ClusterSsmValue = {clusterName: props.clusterName, vpceServiceId: gwlbEndpointService.ref}
        const clusterParam = new ssm.StringParameter(this, "ClusterParam", {
            allowedPattern: ".*",
            description: "The Cluster's details",
            parameterName: props.ssmParamNameCluster,
            stringValue: JSON.stringify(clusterParamValue),
            tier: ssm.ParameterTier.STANDARD,
        });
        clusterParam.node.addDependency(gwlbEndpointService);        
    }
}
