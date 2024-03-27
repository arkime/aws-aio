import * as cdk from 'aws-cdk-lib';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as path from 'path';
import { Construct } from 'constructs';
import * as ssmwrangling from '../core/ssm-wrangling';
import * as types from '../core/context-types';

export interface ViewerNodesStackProps extends cdk.StackProps {
    readonly arnViewerCert: string;
    readonly captureBucket: s3.Bucket;
    readonly viewerVpc: ec2.Vpc;
    readonly clusterConfigBucketName: string;
    readonly clusterName: string;
    readonly osDomain: opensearch.Domain;
    readonly osPassword: secretsmanager.Secret;
    readonly ssmParamNameViewerConfig: string;
    readonly ssmParamNameViewerDetails: string;
    readonly planCluster: types.ClusterPlan;
    readonly userConfig: types.UserConfig;
}

export class ViewerNodesStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: ViewerNodesStackProps) {
        super(scope, id, props);

        // Some configuration values
        const viewerPort = 8005; // Arkime default
        const viewerUser = 'admin';

        const viewerPass = new secretsmanager.Secret(this, 'ViewerPassword', {
            generateSecretString: {
                secretStringTemplate: JSON.stringify({
                    authSecret: '',
                    passwordSecret: 'ignore'
                }), // Changing value here causes cdk to generate new secrets
                generateStringKey: 'adminPassword',
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
        props.captureBucket.grantRead(taskDefinition.taskRole);
        props.osDomain.grantReadWrite(taskDefinition.taskRole);
        viewerPass.grantRead(taskDefinition.taskRole);

        const service = new ecs.FargateService(this, 'Service', {
            cluster,
            taskDefinition,
            minHealthyPercent: 0, // TODO: Speeds up test deployments but need to change to something safer
            enableExecuteCommand: true
        });

        const scaling = service.autoScaleTaskCount({
            minCapacity: props.planCluster.viewerNodes.minCount,
            maxCapacity: props.planCluster.viewerNodes.maxCount
        });
        scaling.scaleOnCpuUtilization('CpuScaling', {
            targetUtilizationPercent: 60,
        });
        scaling.scaleOnMemoryUtilization('MemoryScaling', {
            targetUtilizationPercent: 60,
        });

        const lb = new elbv2.ApplicationLoadBalancer(this, 'LB', {
            vpc: props.viewerVpc,
            internetFacing: true,
            loadBalancerName: `${props.clusterName}-Viewer`.toLowerCase() // Receives a random suffix, which minimizes DNS collisions
        });

        // If we have a prefix list, we need to create a SG for the LB that allows traffic from the prefix list
        if (props.userConfig.viewerPrefixList) {
            const sg = new ec2.SecurityGroup(this, 'ALBSG', {
                vpc: props.viewerVpc,
                description: 'Control access viewer ALB',
            });
            sg.addIngressRule(ec2.Peer.prefixList(props.userConfig.viewerPrefixList), ec2.Port.tcp(443), 'Allow HTTPS traffic from my prefix list');
            lb.addSecurityGroup(sg);
        }

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
                'VIEWER_CONFIG_SSM_PARAM': props.ssmParamNameViewerConfig,
                'VIEWER_DNS': lb.loadBalancerDnsName,
                'VIEWER_PASS_ARN': viewerPass.secretArn,
                'VIEWER_PORT': viewerPort.toString(),
                'VIEWER_USER': viewerUser,
            }
        });
        container.addPortMappings({
            containerPort: viewerPort,
            hostPort: viewerPort
        });

        /*
        const listener = lb.addListener('Listener', {
            protocol: elbv2.ApplicationProtocol.HTTP,
            port: 80,
            open: true,
            sslPolicy: elbv2.SslPolicy.RECOMMENDED_TLS,
        });

        listener.addTargets('TargetGroup', {
            protocol: elbv2.ApplicationProtocol.HTTP,
            port: viewerPort,
            targets: [service.loadBalancerTarget({
                containerName: container.containerName,
                containerPort: viewerPort
            })],
            healthCheck: {
                healthyHttpCodes: '200,302,401',
                path: '/',
                unhealthyThresholdCount: 2,
                healthyThresholdCount: 5,
                interval: cdk.Duration.seconds(30),
            },
        });
        */

        const certificate = acm.Certificate.fromCertificateArn(this, 'ViewerCert', props.arnViewerCert);
        const httpsListener = lb.addListener('HttpsListener', {
            port: 443,
            protocol: elbv2.ApplicationProtocol.HTTPS,
            certificates: [certificate],
        });
        httpsListener.addTargets('HttpsTargetGroup', {
            protocol: elbv2.ApplicationProtocol.HTTP,
            port: viewerPort,
            targets: [service.loadBalancerTarget({
                containerName: container.containerName,
                containerPort: viewerPort
            })],
            healthCheck: {
                healthyHttpCodes: '200,302,401',
                path: '/',
                unhealthyThresholdCount: 2,
                healthyThresholdCount: 5,
                interval: cdk.Duration.seconds(30),
            },
        });

        // This SSM parameter will be share details about the Viewer nodes.
        const viewerParamValue: ssmwrangling.ViewerSsmValue = {
            dns: lb.loadBalancerDnsName,
            ecsCluster: service.cluster.clusterName,
            ecsService: service.serviceName,
            passwordArn: viewerPass.secretArn,
            user: viewerUser
        };
        const viewerParam = new ssm.StringParameter(this, 'ViewerDetails', {
            description: 'Details about the Arkime Viewer Nodes',
            parameterName: props.ssmParamNameViewerDetails,
            stringValue: JSON.stringify(viewerParamValue),
            tier: ssm.ParameterTier.STANDARD,
        });
        viewerParam.node.addDependency(service);
    }
}
