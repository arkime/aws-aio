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
 * Structure to hold CIDR details
 */
export interface Cidr {
    block: string;
    prefix: string;
    mask: string;
}

/**
 * Structure to hold the details of the cluster's S3 usage plan
 */
export interface S3Plan {
    pcapStorageClass: string;
    pcapStorageDays: number;
}

/**
 * Structure to hold the capacity plan for a given set of viewer nodes
 */
export interface ViewerNodesPlan {
    maxCount: number;
    minCount: number;
}

/**
 * Structure to hold the details of the cluster's Capture VPC
 */
export interface VpcPlan {
    cidr: Cidr;
    azs: string[];
    publicSubnetMask: number;
}

/**
 * Structure to hold the overall capacity plan for an Arkime Cluster
 */
export interface ClusterPlan {
    captureNodes: CaptureNodesPlan;
    captureVpc: VpcPlan;
    ecsResources: EcsSysResourcePlan;
    osDomain: OSDomainPlan;
    s3: S3Plan;
    viewerNodes: ViewerNodesPlan;
    viewerVpc: VpcPlan | null;
}

/**
 * Structure to hold the user's input configuration
 */
export interface UserConfig {
    expectedTraffic: number;
    spiDays: number;
    historyDays: number;
    replicas: number;
    pcapDays: number;
    viewerPrefixList: string;
}

/**
 * Structure to hold the stack names for Cluster management commands
 */
export interface ClusterMgmtStackNames {
    captureBucket: string;
    captureNodes: string;
    captureTgw: string;
    captureVpc: string;
    osDomain: string;
    viewerNodes: string;
    viewerVpc: string;
}
