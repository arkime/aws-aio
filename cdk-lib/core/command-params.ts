/**
 * Base type for receiving arguments from the Python side of the app.  These directly match the interface on the Python
 * side for a given command and can be type-cast into using JSON.  It's expected these will only be used during the
 * creation of CommandParams objects and discarded once one of those is created.
 */
export interface CommandParamsRaw { }

/**
 * Type to receive the raw Create and Destroy Cluster arguments from Python
 */
export interface ClusterMgmtParamsRaw extends CommandParamsRaw {
    type: "ClusterMgmtParamsRaw";
    nameCluster: string;
    nameCaptureBucketStack: string;
    nameCaptureBucketSsmParam: string;
    nameCaptureNodesStack: string;
    nameCaptureVpcStack: string;
    nameOSDomainStack: string;
    nameOSDomainSsmParam: string;
}

/**
 * Base type for storing arguments received from the Python side of the app.  These may be embellished with additional
 * details not present in the raw arguments from Python.  The rest of the CDK App will use these types to seed stack
 * generation configuration based.
 */
export interface CommandParams {
    awsAccount: string;
    awsRegion: string;
}

/**
 * Receptacle type to store arguments for Deploy Demo Traffic calls
 */
export interface DeployDemoTrafficParams extends CommandParams {
    type: "DeployDemoTrafficParams";
    // same as base for now
}

/**
 * Receptacle type to store arguments for Destroy Demo Traffic calls
 */
export interface DestroyDemoTrafficParams extends CommandParams {
    type: "DestroyDemoTrafficParams";
    // same as base for now
}

/**
 * Receptacle type to store arguments for Create and Destroy Cluster calls
 */
export interface ClusterMgmtParams extends CommandParams {
    type: "ClusterMgmtParams"
    nameCluster: string;
    nameCaptureBucketStack: string;
    nameCaptureBucketSsmParam: string;
    nameCaptureNodesStack: string;
    nameCaptureVpcStack: string;
    nameOSDomainStack: string;
    nameOSDomainSsmParam: string;
}
