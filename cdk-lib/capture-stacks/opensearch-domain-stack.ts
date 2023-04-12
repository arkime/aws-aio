import { Construct } from 'constructs';
import { Stack, StackProps } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import {Domain, EngineVersion, TLSSecurityPolicy} from 'aws-cdk-lib/aws-opensearchservice';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as ssm from 'aws-cdk-lib/aws-ssm';


export interface OpenSearchDomainStackProps extends StackProps {
    readonly captureVpc: ec2.Vpc;
    readonly ssmParamName: string;
}

export class OpenSearchDomainStack extends Stack {
    public readonly domainKey: kms.Key;
    public readonly domain: Domain;
    public readonly osSg: ec2.SecurityGroup;
    public readonly osPassword: secretsmanager.Secret;

    constructor(scope: Construct, id: string, props: OpenSearchDomainStackProps) {
        super(scope, id, props);

        // Support encryption-at-rest of the data in the OpenSearch Domain
        this.domainKey = new kms.Key(this, 'ArkimeDomainKey', {
            description: "Key for encrypting the Arkime OpenSearch Domain"
        });

        /**
         * This IAM role enables OpenSearch to perform management actions within the VPC.  You can read more about it
         * in the official docs.  There's a quirk here that this is an account-global resource, which means that if you
         * try to spin up a second of these CloudFormation stacks in the same AWS Account, the second deployment will
         * fail.  The alternative approach to embedding in CDK is to create it using the AWS CLI as part of account
         * bootstrapping.  We choose to have the user bootstrap their account using the AWS CLI, but leave this here,
         * disabled, in case someone wants to avoid that step.
         * 
         * See: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/slr.html
         * See: https://github.com/aws/aws-cdk/tree/main/packages/%40aws-cdk/aws-opensearchservice#a-note-about-slr
         */
        // const opensearchServiceLinkedRole = new iam.CfnServiceLinkedRole(this, 'opensearch-slr', {
        //     awsServiceName: 'es.amazonaws.com',
        //     description: 'Service-linked-role for OpenSearch to access resources in my VPC',
        // });

        // Enable access to our OpenSearch Domain
        this.osSg = new ec2.SecurityGroup(this, `opensearch-sg`, {
            securityGroupName: `opensearch-sg`,
            vpc: props.captureVpc
        });
      
        this.osSg.addIngressRule(
            ec2.Peer.anyIpv4(),
            ec2.Port.tcp(443),
            'allow HTTPS traffic from anywhere',
        );

        this.osPassword = new secretsmanager.Secret(this, "OpenSearchPassword", {
            generateSecretString: {
                excludeCharacters: '\\$:()[]&\'\"<>`|;*?# ' // Characters likely to cause problems in shells
            }
        });
        this.domain = new Domain(this, 'ArkimeDomain', {
            version: EngineVersion.OPENSEARCH_1_3,
            enableVersionUpgrade: true,
            capacity: {
                masterNodes: 3,
                dataNodes: 2,
            },
            ebs: {
                volumeSize: 20,
            },
            nodeToNodeEncryption: true,
            encryptionAtRest: {
                enabled: true,
                kmsKey: this.domainKey,
            },
            zoneAwareness: {
                availabilityZoneCount: 2,
            },
            logging: {
                slowSearchLogEnabled: true,
                appLogEnabled: true,
                slowIndexLogEnabled: true,
            },
            vpc: props.captureVpc,
            vpcSubnets: [{
                subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS
            }],
            tlsSecurityPolicy: TLSSecurityPolicy.TLS_1_2,
            securityGroups: [this.osSg],
            enforceHttps: true,
            useUnsignedBasicAuth: true,
            fineGrainedAccessControl: {
                masterUserPassword: this.osPassword.secretValue
            }
        });

        // This SSM parameter will be used to export the name of the domain to other consumers outside of
        // CloudFormation (such as our management CLI)
        new ssm.StringParameter(this, 'DomainName', {
            allowedPattern: '.*',
            description: 'The name of the Capture OpenSearch Domain',
            parameterName: props.ssmParamName,
            stringValue: this.domain.domainName,
            tier: ssm.ParameterTier.STANDARD,
        });
    }
}