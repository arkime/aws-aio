import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as path from 'path'
import { Construct } from 'constructs';

export class TrafficGenStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        // Stock VPC w/ a Public/Private subnet pair in 1 AZ along with NATGateways providing internet access to the
        // private VPCs.
        const vpc = new ec2.Vpc(this, 'VPC', {maxAzs: 1});

        // Create a Fargate service that runs a single instance of our traffic generation image
        const cluster = new ecs.Cluster(this, 'Cluster', { vpc });

        const taskDefinition = new ecs.FargateTaskDefinition(this, 'TaskDef', {
            memoryLimitMiB: 512,
            cpu: 256
        });
        const container = taskDefinition.addContainer("FargateContainer", {
            image: ecs.ContainerImage.fromAsset(path.resolve(__dirname, '..', 'docker-traffic-gen')),
            memoryLimitMiB: 512,
            logging: new ecs.AwsLogDriver({ streamPrefix: 'DemoTrafficGen', mode: ecs.AwsLogDriverMode.NON_BLOCKING })
        });
        
        const service = new ecs.FargateService(this, 'Service', {
            cluster,
            taskDefinition,
            desiredCount: 1,
          });
    }
}
