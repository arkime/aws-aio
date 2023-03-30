/**
 * CDK Context variables the Python side will pass information through.  Currently hardcoded over there as well.
 */
export const CDK_CONTEXT_CMD_VAR: string = "ARKIME_CMD"
export const CDK_CONTEXT_REGION_VAR: string = "ARKIME_REGION"
export const CDK_CONTEXT_PARAMS_VAR: string = "ARKIME_PARAMS"

/**
 * These map directly to the specific commands executed by the user via the management CLI.  Since the strings are
 * shared between the TypeScript and Python sides of the application, they should ideally be in a shared config file
 * rather than hardcoded in both locations.
 */
export enum ManagementCmd {
    DeployDemoTraffic = "DeployDemoTraffic",
    DestroyDemoTraffic = "DestroyDemoTraffic",
    CreateCluster = "CreateCluster",
}

