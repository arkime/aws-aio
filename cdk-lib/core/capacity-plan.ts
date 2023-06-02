/**
 * Structure to hold the capacity plan for a given set of capture nodes
 */
export interface CaptureNodesPlan {
    instanceType: string;
    desiredCount: number;
    maxCount: number;
    minCount: number;
}

/**
 * Structure to hold the ECS system resource plan for a given set of capture nodes
 */
export interface EcsSysResourcePlan {
    cpu: number;
    memory: number;
}

/**
 * Structure to hold the capacity plan for an OS Domain's data nodes
 */
export interface DataNodesPlan {
    count: number;
    instanceType: string;
    volumeSize: number;
}

/**
 * Structure to hold the capacity plan for an OS Domain's master nodes
 */
export interface MasterNodesPlan {
    count: number;
    instanceType: string;
}

/**
 * Structure to hold the overall capacity plan for an OS Domain
 */
export interface OSDomainPlan {
    dataNodes: DataNodesPlan;
    masterNodes: MasterNodesPlan;
}

/**
 * Structure to hold the details of the cluster's Capture VPC
 */
export interface CaptureVpcPlan {
    numAzs: number;
}

/**
 * Structure to hold the overall capacity plan for an Arkime Cluster
 */
export interface ClusterPlan {
    captureNodes: CaptureNodesPlan;
    captureVpc: CaptureVpcPlan;
    ecsResources: EcsSysResourcePlan;
    osDomain: OSDomainPlan;
}
