import assert = require('assert');

import { Construct } from 'constructs';
import { Stack, StackProps } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ssm from 'aws-cdk-lib/aws-ssm';

import {SubnetSsmValue, VpcSsmValue} from '../core/ssm-wrangling'

export interface VpcMirrorStackProps extends StackProps {
    readonly subnetIds: string[];
    readonly subnetSsmParamNames: string[];
    readonly vpcId: string;
    readonly vpcSsmParamName: string;
    readonly vpceServiceId: string;
}

/**
 * This stack contains the core/shared components required to set up traffic mirroring from one User VPC to one
 * Capture VPC.  That is, one of these stacks should exist for each combination of Capture VPC/Source VPC.  It
 * instantiates AWS Resources into the user's Source VPC in order for their traffic to be mirrored to the Capture
 * VPC.
 * 
 * The components it contains are considered 'core/shared' components because they are (relatively) static.  They
 * should remain unchanged as long as the subnets in the user's Source VPC remain unchanged.  They will shared by the
 * many, fluidly-defined mirroring configurations we make for each Elastic Network Interface in the user's VPC.  We
 * create/manage the ENI-specific components from the Python management CLI.  It is presumed that the subnets in a User
 * VPC will change much less often than the ENIs (e.g. compute auto-scaling)
 * 
 * See: https://docs.aws.amazon.com/vpc/latest/mirroring/tm-example-glb-endpoints.html
 */
export class VpcMirrorStack extends Stack {
    constructor(scope: Construct, id: string, props: VpcMirrorStackProps) {
        super(scope, id, props);

        // Make a new joined list of tuples of the form [[subnetId1, subnetSsmParamName1], ...]
        const combinedList: [string, string][] = props.subnetIds.map((element, index) => [element, props.subnetSsmParamNames[index]]);

        for (const [subnetId, subnetParamName] of combinedList) {
            // Since we're relying on stable/consistent ordering of the two lists, let's make sure that's true
            assert.ok(subnetParamName.includes(subnetId), `Expected Subnet SSM Param ${subnetParamName} to contain Subnet ID ${subnetId}`)

            const vpcEndpoint = new ec2.CfnVPCEndpoint(this, `VPCE-${subnetId}`, {
                serviceName: `com.amazonaws.vpce.${this.region}.${props.vpceServiceId}`,
                vpcId: props.vpcId,
                vpcEndpointType: 'GatewayLoadBalancer',
                subnetIds: [subnetId],
            });

            const mirrorTarget = new ec2.CfnTrafficMirrorTarget(this, `Target-${subnetId}`, {
                gatewayLoadBalancerEndpointId: vpcEndpoint.ref
            });

            // These SSM parameter will enable us share the details of our subnet-specific Capture setups
            const subnetParamValue: SubnetSsmValue = {mirrorTargetId: mirrorTarget.ref, subnetId: subnetId, vpcEndpointId: vpcEndpoint.ref}
            const subnetParam = new ssm.StringParameter(this, `SubnetParam-${subnetId}`, {
                allowedPattern: '.*',
                description: 'The Subnet\'s details',
                parameterName: subnetParamName,
                stringValue: JSON.stringify(subnetParamValue),
                tier: ssm.ParameterTier.STANDARD,
            });
            subnetParam.node.addDependency(mirrorTarget);
        };

        // Let's mirror all non-local VPC traffic
        // See: https://docs.aws.amazon.com/vpc/latest/mirroring/tm-example-non-vpc.html
        const filter = new ec2.CfnTrafficMirrorFilter(this, `Filter`, {
            description: 'Mirror non-local VPC traffic'
        });
        new ec2.CfnTrafficMirrorFilterRule(this, `FRule-RejectLocalOutbound`, {
            destinationCidrBlock: '10.0.0.0/16', // TODO: Need to figure this out instead of hardcode
            ruleAction: 'REJECT',
            ruleNumber: 10,
            sourceCidrBlock: '0.0.0.0/0',
            trafficDirection: 'EGRESS',
            trafficMirrorFilterId: filter.ref,
            description: 'Reject all intra-VPC traffic'
        });
        new ec2.CfnTrafficMirrorFilterRule(this, `FRule-AllowOtherOutbound`, {
            destinationCidrBlock: '0.0.0.0/0', // TODO: Need to figure this out instead of hardcode
            ruleAction: 'ACCEPT',
            ruleNumber: 20,
            sourceCidrBlock: '0.0.0.0/0',
            trafficDirection: 'EGRESS',
            trafficMirrorFilterId: filter.ref,
            description: 'Accept all outbound traffic'
        });

        new ec2.CfnTrafficMirrorFilterRule(this, `FRule-RejectLocalInbound`, {
            destinationCidrBlock: '0.0.0.0/0',
            ruleAction: 'REJECT',
            ruleNumber: 10,
            sourceCidrBlock: '10.0.0.0/16', // TODO: Need to figure this out instead of hardcode
            trafficDirection: 'INGRESS',
            trafficMirrorFilterId: filter.ref,
            description: 'Reject all intra-VPC traffic'
        });
        new ec2.CfnTrafficMirrorFilterRule(this, `FRule-AllowOtherInbound`, {
            destinationCidrBlock: '0.0.0.0/0',
            ruleAction: 'ACCEPT',
            ruleNumber: 20,
            sourceCidrBlock: '0.0.0.0/0',
            trafficDirection: 'INGRESS',
            trafficMirrorFilterId: filter.ref,
            description: 'Accept all inbound traffic'
        });

        // This SSM parameter will enable us share the details of our VPC-specific Capture setup
        const vpcParamValue: VpcSsmValue = {mirrorFilterId: filter.ref, vpcId: props.vpcId}
        const vpcParam = new ssm.StringParameter(this, `VpcParam-${props.vpcId}`, {
            allowedPattern: '.*',
            description: 'The VPC\'s details',
            parameterName: props.vpcSsmParamName,
            stringValue: JSON.stringify(vpcParamValue),
            tier: ssm.ParameterTier.STANDARD,
        });
        vpcParam.node.addDependency(filter);
    }
}