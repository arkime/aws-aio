import * as cdk from 'aws-cdk-lib';
import * as autoscaling from 'aws-cdk-lib/aws-autoscaling';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as path from 'path';
import { Construct } from 'constructs';

export interface TrafficGenStackProps extends cdk.StackProps {
    readonly cidr: string;
}

export class TrafficGenStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: TrafficGenStackProps) {
        super(scope, id, props);

        /**
         * Set up our demo Traffic Generator's networking
         */
        // This is a Stock VPC w/ a Public/Private subnet pair in 1 AZ along with NATGateways providing internet access
        // to the private subnet.
        const vpc = new ec2.Vpc(this, 'VPC', {
            ipAddresses: ec2.IpAddresses.cidr(props.cidr),
            maxAzs: 1
        });

        /**
         * Set up some shared components.
         */
        // Key to encrypt SSM traffic when using ECS Exec to shell into the container
        const ssmKey = new kms.Key(this, 'SsmKey', {
            enableKeyRotation: true,
        });

        /**
         * Create a Fargate service that runs our traffic generation image
         */
        const fargateCluster = new ecs.Cluster(this, 'FargateCluster', {
            vpc,
            executeCommandConfiguration: { kmsKey: ssmKey }
        });

        const fargateTaskDef = new ecs.FargateTaskDefinition(this, 'TaskDef', {
            memoryLimitMiB: 512,
            cpu: 256,
        });
        fargateTaskDef.addToTaskRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: ['kms:Decrypt'], // Required for ECS Exec & shelling into the container
                resources: [ssmKey.keyArn]
            }),
        );

        fargateTaskDef.addContainer('FargateContainer', {
            image: ecs.ContainerImage.fromAsset(path.resolve(__dirname, '..', '..', 'docker-traffic-gen')),
            memoryLimitMiB: 512,
            logging: new ecs.AwsLogDriver({ streamPrefix: 'DemoTrafficGenFargate', mode: ecs.AwsLogDriverMode.NON_BLOCKING })
        });

        new ecs.FargateService(this, 'Service', {
            cluster: fargateCluster,
            taskDefinition: fargateTaskDef,
            desiredCount: 1,
            enableExecuteCommand: true
        });

        /**
         * Create an ECS-on-EC2 Cluster that runs our traffic generation image
         */

        //
        const ecsAsg = new autoscaling.AutoScalingGroup(this, 'EcsASG', {
            vpc: vpc,
            instanceType: new ec2.InstanceType('t3.micro'), // Arbitrarily chosen
            machineImage: ecs.EcsOptimizedImage.amazonLinux2(),
            desiredCapacity: 3,
            minCapacity: 3,
            maxCapacity: 10 // Arbitrarily chosen
        });

        const ecsCluster = new ecs.Cluster(this, 'EcsCluster', {
            vpc: vpc,
            executeCommandConfiguration: { kmsKey: ssmKey }
        });

        const ecsCapacityProvider = new ecs.AsgCapacityProvider(this, 'EcsCapacityProvider', {
            autoScalingGroup: ecsAsg,
        });
        ecsCluster.addAsgCapacityProvider(ecsCapacityProvider);

        const ecsTaskDef = new ecs.Ec2TaskDefinition(this, 'EcsTaskDef', {
            networkMode: ecs.NetworkMode.BRIDGE,
        });
        ecsTaskDef.addToTaskRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: ['kms:Decrypt'], // Required for ECS Exec & shelling into the container
                resources: [ssmKey.keyArn]
            }),
        );

        ecsTaskDef.addContainer('EcsContainer', {
            image: ecs.ContainerImage.fromAsset(path.resolve(__dirname, '..', '..', 'docker-traffic-gen')),
            logging: new ecs.AwsLogDriver({ streamPrefix: 'DemoTrafficGenEcs', mode: ecs.AwsLogDriverMode.NON_BLOCKING }),

            // Because we're using the BRIDGE network type for our ECS Tasks, we can only place a single container
            // on each of our t3.micro instances.  We can't ask for all of their resources because ECS placement will
            // fail, so we ask for a bit less than that.
            cpu: 1536, // 1.5 vCPUs
            memoryLimitMiB: 768, // 0.75 GiB
        });

        new ecs.Ec2Service(this, 'EcsService', {
            cluster: ecsCluster,
            taskDefinition: ecsTaskDef,
            desiredCount: 1,
            minHealthyPercent: 0,
            enableExecuteCommand: true
        });
    }
}
