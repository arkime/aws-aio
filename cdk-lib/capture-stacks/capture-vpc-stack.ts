import { Construct } from 'constructs';
import { RemovalPolicy } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Stack, StackProps } from 'aws-cdk-lib';

export class CaptureVpcStack extends Stack {
  public readonly vpc: ec2.Vpc;
  public readonly flowLog: ec2.FlowLog;

  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);

    this.vpc = new ec2.Vpc(this, 'VPC', {
        maxAzs: 3,
        subnetConfiguration: [
            {
                subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
                name: 'CaptureNodes',
                cidrMask: 24
            },
            {
                subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
                name: 'Database',
                cidrMask: 24
            }
            ]
        });
    
        const flowLogsGroup = new logs.LogGroup(this, 'FlowLogsLogGroup', {
            logGroupName: `FlowLogs-${id}`,
            removalPolicy: RemovalPolicy.RETAIN,
            retention: logs.RetentionDays.TEN_YEARS,
        });
    
        this.flowLog = new ec2.FlowLog(this, 'FlowLogs', {
            resourceType: ec2.FlowLogResourceType.fromVpc(this.vpc),
            destination: ec2.FlowLogDestination.toCloudWatchLogs(flowLogsGroup),
        });
  }
}