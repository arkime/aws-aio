import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Stack, StackProps } from 'aws-cdk-lib';

import * as plan from '../core/context-types';

export interface CaptureVpcStackProps extends StackProps {
    readonly planCluster: plan.ClusterPlan;
}

export class CaptureVpcStack extends Stack {
    public readonly vpc: ec2.Vpc;

    constructor(scope: Construct, id: string, props: CaptureVpcStackProps) {
        super(scope, id, props);

        this.vpc = new ec2.Vpc(this, 'VPC', {
            ipAddresses: ec2.IpAddresses.cidr(props.planCluster.captureVpc.cidr.block),
            // natGateways: 0, // ECS on EC2 need NatGateways, there might be another way?
            availabilityZones: props.planCluster.captureVpc.azs,
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
    }
}
