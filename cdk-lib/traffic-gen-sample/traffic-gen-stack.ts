import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as path from 'path'
import { Construct } from 'constructs';

export class TrafficGenStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        // Stock VPC w/ a Public/Private subnet pair in 1 AZ along with NATGateways providing internet access to the
        // private VPCs.
        const vpc = new ec2.Vpc(this, 'VPC', {maxAzs: 1});

        // Key to encrypt SSM traffic when using ECS Exec to shell into the container
        const ksmEncryptionKey = new kms.Key(this, 'ECSClusterKey', {
            enableKeyRotation: true,
        });

        // Create a Fargate service that runs a single instance of our traffic generation image
        const cluster = new ecs.Cluster(this, 'Cluster', {
            vpc,
            executeCommandConfiguration: { kmsKey: ksmEncryptionKey }
        });

        const taskDefinition = new ecs.FargateTaskDefinition(this, 'TaskDef', {
            memoryLimitMiB: 512,
            cpu: 256,
        });
        taskDefinition.addToTaskRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: ['kms:Decrypt'], // Required for ECS Exec & shelling into the container
                resources: [ksmEncryptionKey.keyArn]
            }),
        );

        const container = taskDefinition.addContainer('FargateContainer', {
            image: ecs.ContainerImage.fromAsset(path.resolve(__dirname, '..', '..', 'docker-traffic-gen')),
            memoryLimitMiB: 512,
            logging: new ecs.AwsLogDriver({ streamPrefix: 'DemoTrafficGen', mode: ecs.AwsLogDriverMode.NON_BLOCKING })
        });
        
        const service = new ecs.FargateService(this, 'Service', {
            cluster,
            taskDefinition,
            desiredCount: 1,
            enableExecuteCommand: true
        });

        // Set up VPC Flow Logs to enable visibility of the traffic mirroring on the user-side    
        const flowLogsGroup = new logs.LogGroup(this, 'FlowLogsLogGroup', {
            logGroupName: `FlowLogs-${id}`,
            removalPolicy: cdk.RemovalPolicy.DESTROY,
            retention: logs.RetentionDays.TEN_YEARS,
        });

        new ec2.FlowLog(this, 'FlowLogs', {
            resourceType: ec2.FlowLogResourceType.fromVpc(vpc),
            destination: ec2.FlowLogDestination.toCloudWatchLogs(flowLogsGroup),
        });

    }
}
