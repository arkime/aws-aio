import * as cdk from 'aws-cdk-lib';
import * as prms from './command-params';
import {CDK_CONTEXT_CMD_VAR, CDK_CONTEXT_REGION_VAR, CDK_CONTEXT_PARAMS_VAR, ManagementCmd} from './constants';


/**
 * Function for retrieving all information needed for template generation from environment variables and CDK context.
 * Provides a wrapper for the process of retrieval so the rest of the CDK App does not need to know the specifics of
 * where these values ultimately come from.
 * 
 * @param app The current CDK App
 * @returns All external arguments for template generation
 */
export function getCommandParams(app: cdk.App) : (prms.ClusterMgmtParams | prms.DeployDemoTrafficParams | prms.DestroyDemoTrafficParams | prms.MirrorMgmtParams) {
    // This ENV variable is set by the CDK CLI.  It reads it from your AWS Credential profile, and configures the var
    // before invoking CDK actions.
    const awsAccount: string | undefined = process.env.CDK_DEFAULT_ACCOUNT

    // Like the CDK_DEFAULT_ACCOUNT, the CDK CLI sets the CDK_DEFAULT_REGION by reading the AWS Credential profile.
    // However, we want the user to to able to specify a different region than the default so we optionaly pass in one
    // via CDK Context ourselves.
    const regionContext = app.node.tryGetContext(CDK_CONTEXT_REGION_VAR)
    const awsRegion: string | undefined = regionContext ?? process.env.CDK_DEFAULT_REGION

    // We pass in the name of the current management command via CDK Context
    const cmdContext: keyof typeof ManagementCmd | undefined = app.node.tryGetContext(CDK_CONTEXT_CMD_VAR)
    const managementCmd: ManagementCmd | undefined = cmdContext === undefined ? undefined : ManagementCmd[cmdContext]

    // We pass in application state information via string-encoded JSON in this context variable
    const cmdParamsRaw: string | undefined = app.node.tryGetContext(CDK_CONTEXT_PARAMS_VAR)

    return validateArgs({
            awsAccount: awsAccount,
            awsRegion: awsRegion,
            managementCmd: managementCmd,
            cmdParamsRaw: cmdParamsRaw
    });
}

interface ValidateArgs {
    readonly awsAccount?: string;
    readonly awsRegion?: string;
    readonly managementCmd?: ManagementCmd;
    readonly cmdParamsRaw?: string
}

function validateArgs(args: ValidateArgs) : (prms.ClusterMgmtParams | prms.DeployDemoTrafficParams | prms.DestroyDemoTrafficParams | prms.MirrorMgmtParams) {
    if (!args.awsAccount) {
        throw Error('AWS Account not defined; have you configured your AWS Credentials?')
    }

    if (!args.awsRegion) {
        throw Error(`AWS Region not defined; expected to pull it from AWS Config or the CDK Context variable ${CDK_CONTEXT_REGION_VAR}`)
    }

    if (!args.managementCmd) {
        throw Error(`Management Command not defined; expected to pull it from the CDK Context variable ${CDK_CONTEXT_CMD_VAR}`)
    }

    switch (args.managementCmd) {
        case ManagementCmd.DeployDemoTraffic:
            const deployDemoParams: prms.DeployDemoTrafficParams = {
                type: 'DeployDemoTrafficParams',
                awsAccount: args.awsAccount, 
                awsRegion: args.awsRegion, 
            }
            return deployDemoParams;
        case ManagementCmd.DestroyDemoTraffic:
            const destroyDemoParams: prms.DeployDemoTrafficParams = {
                type: 'DeployDemoTrafficParams',
                awsAccount: args.awsAccount, 
                awsRegion: args.awsRegion, 
            }
            return destroyDemoParams;
        case ManagementCmd.CreateCluster: // Create and Destroy Cluster use the same parameters
        case ManagementCmd.DestroyCluster:
            // Must define stack config
            if (!args.cmdParamsRaw) {
                throw Error(`Command Parameters not defined; expected to pull from the CDK Context variable ${CDK_CONTEXT_PARAMS_VAR}`)
            }

            // Get the raw arguments from Python and convert to our params type
            const rawClusterMgmtParamsObj: prms.ClusterMgmtParamsRaw = JSON.parse(args.cmdParamsRaw)
            const clusterMgmtParams: prms.ClusterMgmtParams = {
                type: 'ClusterMgmtParams',
                awsAccount: args.awsAccount,
                awsRegion: args.awsRegion,
                arkimeFileMap: JSON.parse(rawClusterMgmtParamsObj.arkimeFileMap),
                nameCluster: rawClusterMgmtParamsObj.nameCluster,
                nameCaptureBucketStack: rawClusterMgmtParamsObj.nameCaptureBucketStack,
                nameCaptureBucketSsmParam: rawClusterMgmtParamsObj.nameCaptureBucketSsmParam,
                nameCaptureNodesStack: rawClusterMgmtParamsObj.nameCaptureNodesStack,
                nameCaptureVpcStack: rawClusterMgmtParamsObj.nameCaptureVpcStack,
                nameClusterSsmParam: rawClusterMgmtParamsObj.nameClusterSsmParam,
                nameOSDomainStack: rawClusterMgmtParamsObj.nameOSDomainStack,
                nameOSDomainSsmParam: rawClusterMgmtParamsObj.nameOSDomainSsmParam,
                nameViewerCertArn: rawClusterMgmtParamsObj.nameViewerCertArn,
                nameViewerDnsSsmParam: rawClusterMgmtParamsObj.nameViewerDnsSsmParam,
                nameViewerPassSsmParam: rawClusterMgmtParamsObj.nameViewerPassSsmParam,
                nameViewerUserSsmParam: rawClusterMgmtParamsObj.nameViewerUserSsmParam,
                nameViewerNodesStack: rawClusterMgmtParamsObj.nameViewerNodesStack,
                planCluster:  JSON.parse(rawClusterMgmtParamsObj.planCluster),
                userConfig: JSON.parse(rawClusterMgmtParamsObj.userConfig),
            }
            return clusterMgmtParams;
        case ManagementCmd.AddVpc: // Add and Remove VPC use the same parameters
        case ManagementCmd.RemoveVpc:
            // Must define stack config
            if (!args.cmdParamsRaw) {
                throw Error(`Command Parameters not defined; expected to pull from the CDK Context variable ${CDK_CONTEXT_PARAMS_VAR}`)
            }

            // Get the raw arguments from Python and convert to our params type
            const rawMirrorMgmtParamsObj: prms.MirrorMgmtParamsRaw = JSON.parse(args.cmdParamsRaw)
            const mirrorMgmtParams: prms.MirrorMgmtParams = {
                type: 'MirrorMgmtParams',
                arnEventBus: rawMirrorMgmtParamsObj.arnEventBus,
                awsAccount: args.awsAccount,
                awsRegion: args.awsRegion,
                nameCluster: rawMirrorMgmtParamsObj.nameCluster,
                nameVpcMirrorStack: rawMirrorMgmtParamsObj.nameVpcMirrorStack,
                nameVpcSsmParam: rawMirrorMgmtParamsObj.nameVpcSsmParam,
                idVni: rawMirrorMgmtParamsObj.idVni,
                idVpc: rawMirrorMgmtParamsObj.idVpc,
                idVpceService: rawMirrorMgmtParamsObj.idVpceService,
                listSubnetIds: rawMirrorMgmtParamsObj.listSubnetIds,
                listSubnetSsmParams: rawMirrorMgmtParamsObj.listSubnetSsmParams,
                vpcCidrs: rawMirrorMgmtParamsObj.vpcCidrs,
            }
            return mirrorMgmtParams;
        default:
            throw new Error(`Non-existent command in switch: ${args.managementCmd}`);
    }
}
