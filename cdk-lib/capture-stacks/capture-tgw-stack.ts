import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Stack, StackProps } from 'aws-cdk-lib';

export interface CaptureTgwStackProps extends StackProps {
    readonly captureVpc: ec2.Vpc;
}

export class CaptureTgwStack extends Stack {
    readonly tgw: ec2.CfnTransitGateway;
    readonly tgwAttachment: ec2.CfnTransitGatewayAttachment;

  constructor(scope: Construct, id: string, props: CaptureTgwStackProps) {
    super(scope, id, props);

    this.tgw = new ec2.CfnTransitGateway(this, 'TGW', {
        autoAcceptSharedAttachments: 'enable',
        defaultRouteTableAssociation: 'enable',
        defaultRouteTablePropagation: 'enable',
        description: 'TGW providing access to Arkime Cluster',
        dnsSupport: 'enable',
      });

      this.tgwAttachment = new ec2.CfnTransitGatewayAttachment(this, 'TGWAttachment', {
        subnetIds: props.captureVpc.privateSubnets.map(obj => obj.subnetId),
        transitGatewayId: this.tgw.attrId,
        vpcId: props.captureVpc.vpcId,
      
        // the properties below are optional
        options: {
            "DnsSupport": "enable"
        },
      });
  }
}