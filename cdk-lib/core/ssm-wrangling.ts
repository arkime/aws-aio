/**
 * This file contains functions and types that define a shared interface with the Python management CLI; the two need
 * to stay in sync.  We should probably find a way to put these definitions in a single location both the Python and
 * TypeScript sides can pull from.
 */

export interface ClusterSsmValue {
    readonly clusterName: string;
    readonly vpceServiceId: string;
}

export interface SubnetSsmValue {
    readonly mirrorTargetId: string;
    readonly subnetId: string;
    readonly vpcEndpointId: string;
}

export interface VpcSsmValue {
    readonly mirrorFilterId: string;
    readonly vpcId: string;
}