import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as path from 'path'
import { Construct } from 'constructs';

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

        // Key to encrypt SSM traffic when using ECS Exec to shell into the container
        const ksmEncryptionKey = new kms.Key(this, 'ECSClusterKey', {
            enableKeyRotation: true,
        });

        // Create a Fargate service that runs fleet of Arkime Capture Nodes
        const cluster = new ecs.Cluster(this, 'Cluster', {
            vpc: props.captureVpc,
            executeCommandConfiguration: { kmsKey: ksmEncryptionKey }
        });

        // Make containers roughly equivalent in capability to M5.large EC2 instances.  Arbitrarily chosen sizing.
        // See: https://aws.amazon.com/ec2/instance-types/
        // See https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-taskdefinition.html#cfn-ecs-taskdefinition-cpu
        const taskDefinition = new ecs.FargateTaskDefinition(this, 'TaskDef', {
            cpu: 2048,
            memoryLimitMiB: 8192,
        });
        taskDefinition.addToTaskRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: ['kms:Decrypt'], // Required for ECS Exec & shelling into the container
                resources: [ksmEncryptionKey.keyArn]
            }),
        );
        props.osPassword.grantRead(taskDefinition.taskRole);

        // This SSM parameter will be used to track whether the Capture Setup has been initialized or not.  Currently,
        // this means whether Arkime's initialization scripts have been invoked against the OpenSearch Domain.
        const initializedParam = new ssm.StringParameter(this, 'IsInitialized', {
            allowedPattern: 'true|false',
            description: 'Whether the capture setup is initialized or not',
            parameterName: `${props.clusterName}-Initialized`,
            stringValue: 'false',
            tier: ssm.ParameterTier.STANDARD,
        });
        initializedParam.grantRead(taskDefinition.taskRole);
        initializedParam.grantWrite(taskDefinition.taskRole);

        // Our Arkime Capture container
        const container = taskDefinition.addContainer("CaptureContainer", {
            image: ecs.ContainerImage.fromAsset(path.resolve(__dirname, '..', '..', 'docker-capture-node')),
            logging: new ecs.AwsLogDriver({ streamPrefix: 'CaptureNodes', mode: ecs.AwsLogDriverMode.NON_BLOCKING }),
            environment: {
                "CLUSTER_NAME": props.clusterName,
                "SSM_INITIALIZED_PARAM": initializedParam.parameterName,
                "OPENSEARCH_ENDPOINT": props.osDomain.domainEndpoint,
                "OPENSEARCH_SECRET_ARN": props.osPassword.secretArn,
            }
        });
        
        const service = new ecs.FargateService(this, 'Service', {
            cluster,
            taskDefinition,
            desiredCount: 1,
            enableExecuteCommand: true
        });        

        // const scaling = service.autoScaleTaskCount({ maxCapacity: 10 });
        // scaling.scaleOnCpuUtilization('CpuScaling', {
        //     targetUtilizationPercent: 60,
        // });

        // const lb = new elbv2.ApplicationLoadBalancer(this, 'LB', { vpc: props.captureVpc, internetFacing: true });
        // const listener = lb.addListener('Listener', { port: 80 });
        // const targetGroup1 = listener.addTargets('ECS1', {
        //     port: 80,
        //     targets: [service],
        // });
        // const targetGroup2 = listener.addTargets('ECS2', {
        //     port: 80,
        //     targets: [service.loadBalancerTarget({
        //         containerName: 'MyContainer',
        //         containerPort: 8080
        //     })],
        // });
    }
}
