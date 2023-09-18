import { Construct } from 'constructs';
import { Duration, Stack, StackProps } from 'aws-cdk-lib';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ssm from 'aws-cdk-lib/aws-ssm';

import * as plan from '../core/context-types';


export interface CaptureBucketStackProps extends StackProps {
    readonly planCluster: plan.ClusterPlan;
    readonly ssmParamName: string;
}

/**
 * This stack contains the S3 bucket our Arkime Capture Nodes dump the raw packet data to.  We split it into a separate
 * CloudFormation stack so that we can retain this stack (and the data within it) even if we tear down the other
 * stacks.
 */
export class CaptureBucketStack extends Stack {
    readonly bucket: s3.Bucket;
    readonly bucketKey: kms.Key;

    constructor(scope: Construct, id: string, props: CaptureBucketStackProps) {
        super(scope, id, props);


        this.bucketKey = new kms.Key(this, 'BucketKey', {
            enableKeyRotation: true,
        });

        this.bucket = new s3.Bucket(this, 'CaptureBucket', {
            encryption: s3.BucketEncryption.KMS,
            encryptionKey: this.bucketKey,
            enforceSSL: true,
            lifecycleRules: [
                {
                    id: 'PcapExpiration',
                    enabled: true,
                    expiration: Duration.days(props.planCluster.s3.pcapStorageDays),
                },
            ],
        });

        // This SSM parameter will be used to export the name of the capture bucket to other consumers outside of
        // CloudFormation (such as our management CLI)
        new ssm.StringParameter(this, 'BucketName', {
            allowedPattern: '.*',
            description: 'The name of the Capture S3 Bucket',
            parameterName: props.ssmParamName,
            stringValue: this.bucket.bucketName,
            tier: ssm.ParameterTier.STANDARD,
        });
        
    }
}