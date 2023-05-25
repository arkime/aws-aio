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