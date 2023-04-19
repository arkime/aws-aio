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

export interface ViewerNodesStackProps extends cdk.StackProps {
    readonly captureBucket: s3.Bucket;
    readonly viewerVpc: ec2.Vpc;
    readonly clusterName: string;
    readonly osDomain: opensearch.Domain;
    readonly osPassword: secretsmanager.Secret;
    readonly ssmParamNameViewerDns: string;
    readonly ssmParamNameViewerPass: string;
    readonly ssmParamNameViewerUser: string;
}

export class ViewerNodesStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: ViewerNodesStackProps) {
        super(scope, id, props);

        // Some configuration values
        const viewerPort = 8005; // Arkime default
        const viewerUser = "admin";
        const viewerPass = new secretsmanager.Secret(this, 'ViewerPassword', {
            generateSecretString: {
                excludeCharacters: '\\$:()[]&\'"<>`|;*?# ' // Characters likely to cause problems in shells
            }
        });

        // Key to encrypt SSM traffic when using ECS Exec to shell into the container
        const ksmEncryptionKey = new kms.Key(this, 'ECSClusterKey', {
            enableKeyRotation: true,
        });

        // Create a Fargate service that runs fleet of Arkime Viewer Nodes
        const cluster = new ecs.Cluster(this, 'Cluster', {
            vpc: props.viewerVpc,
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
        props.captureBucket.grantRead(taskDefinition.taskRole);
        props.osDomain.grantReadWrite(taskDefinition.taskRole);
        viewerPass.grantRead(taskDefinition.taskRole);

        // Our Arkime Capture container

        const container = taskDefinition.addContainer('ViewerContainer', {
            image: ecs.ContainerImage.fromAsset(path.resolve(__dirname, '..', '..', 'docker-viewer-node')),
            logging: new ecs.AwsLogDriver({ streamPrefix: 'ViewerNodes', mode: ecs.AwsLogDriverMode.NON_BLOCKING }),
            environment: {
                'AWS_REGION': this.region, // Seems not to be defined in this container, strangely
                'BUCKET_NAME': props.captureBucket.bucketName,
                'CLUSTER_NAME': props.clusterName,
                'OPENSEARCH_ENDPOINT': props.osDomain.domainEndpoint,
                'OPENSEARCH_SECRET_ARN': props.osPassword.secretArn,
                'VIEWER_PASS_ARN': viewerPass.secretArn,
                'VIEWER_PORT': viewerPort.toString(),
                'VIEWER_USER': viewerUser,
            }
        });
        container.addPortMappings({
            containerPort: viewerPort,
            hostPort: viewerPort
        })
        
        const service = new ecs.FargateService(this, 'Service', {
            cluster,
            taskDefinition,
            minHealthyPercent: 0, // TODO: Speeds up test deployments but need to change to something safer
            enableExecuteCommand: true
        });        

        const scaling = service.autoScaleTaskCount({ maxCapacity: 10, minCapacity: 4 });
        scaling.scaleOnCpuUtilization('CpuScaling', {
            targetUtilizationPercent: 60,
        });
        scaling.scaleOnMemoryUtilization('MemoryScaling', {
            targetUtilizationPercent: 60,
        });

        const lb = new elbv2.ApplicationLoadBalancer(this, 'LB', { 
            vpc: props.viewerVpc,
            internetFacing: true,
            loadBalancerName: `${props.clusterName}-Viewer` // Receives a random suffix, which minimizes DNS collisions
        });
        const listener = lb.addListener('Listener', {
            protocol: elbv2.ApplicationProtocol.HTTP,
            port: 80,
            open: true
        });

        listener.addTargets('TargetGroup', {
            protocol: elbv2.ApplicationProtocol.HTTP,
            port: viewerPort,
            targets: [service.loadBalancerTarget({
                containerName: container.containerName,
                containerPort: viewerPort
            })],
            healthCheck: {
                healthyHttpCodes: '200,401',
                path: '/',
                unhealthyThresholdCount: 2,
                healthyThresholdCount: 5,
                interval: cdk.Duration.seconds(30),
            },
        });

        // This SSM parameter will be share the DNS name of the ALB fronting the Viewer nodes.
        new ssm.StringParameter(this, 'ViewerDNS', {
            description: 'The DNS name of the Viewer for the cluster',
            parameterName: props.ssmParamNameViewerDns,
            stringValue: lb.loadBalancerDnsName,
            tier: ssm.ParameterTier.STANDARD,
        });

        // This SSM parameter will be share the login password for the Viewer nodes.
        new ssm.StringParameter(this, 'ViewerPassArn', {
            description: 'The ARN of the AWS Secret Manager Secret containing the admin password',
            parameterName: props.ssmParamNameViewerPass,
            stringValue: viewerPass.secretArn,
            tier: ssm.ParameterTier.STANDARD,
        });

        // This SSM parameter will be share the login username for the Viewer nodes.
        new ssm.StringParameter(this, 'ViewerUserArn', {
            description: 'The login username for the Viewers',
            parameterName: props.ssmParamNameViewerUser,
            stringValue: viewerUser,
            tier: ssm.ParameterTier.STANDARD,
        });
    }
}