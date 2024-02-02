import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Stack, StackProps } from 'aws-cdk-lib';

import * as types from '../core/context-types';

export interface ViewerVpcStackProps extends StackProps {
    readonly captureTgw: ec2.CfnTransitGateway;
    readonly captureVpc: ec2.Vpc;
    readonly viewerVpcPlan: types.VpcPlan;
}

export class ViewerVpcStack extends Stack {
    public readonly vpc: ec2.Vpc;

    constructor(scope: Construct, id: string, props: ViewerVpcStackProps) {
        super(scope, id, props);

        // The VPC the Viewer Nodes will live in
        this.vpc = new ec2.Vpc(this, 'VPC', {
            ipAddresses: ec2.IpAddresses.cidr(props.viewerVpcPlan.cidr.block),
            natGateways: 0,
            availabilityZones: props.viewerVpcPlan.azs,
            subnetConfiguration: [
                {
                    subnetType: ec2.SubnetType.PUBLIC,
                    name: 'Ingress',
                    cidrMask: props.viewerVpcPlan.publicSubnetMask
                },
                {
                    subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    name: 'ViewerNodes'
                }
            ]
        });

        // Connects the Viewer VPC to the Capture VPC via its TGW
        const tgwAttachment = new ec2.CfnTransitGatewayAttachment(this, 'TGWAttachment', {
            subnetIds: this.vpc.privateSubnets.map(obj => obj.subnetId),
            transitGatewayId: props.captureTgw.attrId,
            vpcId: this.vpc.vpcId,

            // the properties below are optional
            options: {
                'DnsSupport': 'enable'
            },
        });

        // Make sure that hosts inside the Viewer VPC's private subnets know how to talk to the Capture VPC
        this.vpc.privateSubnets.forEach((value, index) => {

            const subnet = value as ec2.Subnet;
            // subnet.addRoute(`ToCaptureVpc${index + 1}`, {
            //     routerId: props.captureTgw.attrId,
            //     routerType: ec2.RouterType.TRANSIT_GATEWAY,
            //     destinationCidrBlock: props.captureVpc.vpcCidrBlock,
            // })
            const route = new ec2.CfnRoute(this, `ToCaptureVpc${index + 1}`, {
                routeTableId: subnet.routeTable.routeTableId,
                transitGatewayId: props.captureTgw.attrId,
                destinationCidrBlock: props.captureVpc.vpcCidrBlock
            });
            route.addDependency(tgwAttachment);
        });

        // Make sure that return traffic back to the Viewer VPC has a way to get there
        props.captureVpc.privateSubnets.forEach((value, index) => {
            const subnet = value as ec2.Subnet;
            // subnet.addRoute(`ToViewerVpc${index + 1}`, {
            //     routerId: props.captureTgw.attrId,
            //     routerType: ec2.RouterType.TRANSIT_GATEWAY,
            //     destinationCidrBlock: this.vpc.vpcCidrBlock,
            // })

            const route = new ec2.CfnRoute(this, `ToViewerVpc${index + 1}`, {
                routeTableId: subnet.routeTable.routeTableId,
                transitGatewayId: props.captureTgw.attrId,
                destinationCidrBlock: props.viewerVpcPlan.cidr.block
            });
            route.addDependency(tgwAttachment);
        });
    }
}
