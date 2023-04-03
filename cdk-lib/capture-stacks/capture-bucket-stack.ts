import { Construct } from 'constructs';
import { Stack, StackProps } from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';

/**
 * This stack contains the S3 bucket our Arkime Capture Nodes dump the raw packet data to.  We split it into a separate
 * CloudFormation stack so that we can retain this stack (and the data within it) even if we tear down the other
 * stacks.
 */
export class CaptureBucketStack extends Stack {
    readonly bucket: s3.Bucket;

    constructor(scope: Construct, id: string, props: StackProps) {
        super(scope, id, props);

        this.bucket = new s3.Bucket(this, 'CaptureBucket', {
            encryption: s3.BucketEncryption.KMS,
          });
        
    }
}