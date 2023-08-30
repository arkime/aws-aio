import { Construct } from 'constructs';
import { RemovalPolicy } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Stack, StackProps } from 'aws-cdk-lib';

import * as plan from '../core/context-types';

export interface CaptureVpcStackProps extends StackProps {
    readonly planCluster: plan.ClusterPlan;
}

export class CaptureVpcStack extends Stack {
  public readonly vpc: ec2.Vpc;
  public readonly flowLog: ec2.FlowLog;

  constructor(scope: Construct, id: string, props: CaptureVpcStackProps) {
    super(scope, id, props);

    this.vpc = new ec2.Vpc(this, 'VPC', {
        ipAddresses: ec2.IpAddresses.cidr(props.planCluster.captureVpc.cidr.block),
        maxAzs: props.planCluster.captureVpc.numAzs,
        subnetConfiguration: [
            {
                subnetType: ec2.SubnetType.PUBLIC,
                name: 'Ingress',
                cidrMask: props.planCluster.captureVpc.publicSubnetMask
            },
            {
                subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
                name: 'CaptureNodes'
            }
        ]
    });
    
    const flowLogsGroup = new logs.LogGroup(this, 'FlowLogsLogGroup', {
        logGroupName: `FlowLogs-${id}`,
        removalPolicy: RemovalPolicy.DESTROY,
        retention: logs.RetentionDays.TEN_YEARS,
    });

    this.flowLog = new ec2.FlowLog(this, 'FlowLogs', {
        resourceType: ec2.FlowLogResourceType.fromVpc(this.vpc),
        destination: ec2.FlowLogDestination.toCloudWatchLogs(flowLogsGroup),
    });
  }
}