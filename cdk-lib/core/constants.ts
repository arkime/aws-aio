/**
 * CDK Context variables the Python side will pass information through.  Currently hardcoded over there as well.
 */
export const CDK_CONTEXT_CMD_VAR: string = 'ARKIME_CMD';
export const CDK_CONTEXT_REGION_VAR: string = 'ARKIME_REGION';
export const CDK_CONTEXT_PARAMS_VAR: string = 'ARKIME_PARAMS';
export const EVENT_SOURCE: string = 'arkime';
export const EVENT_DETAIL_TYPE_CONFIGURE_ISM: string = 'ConfigureIsm';
export const EVENT_DETAIL_TYPE_CREATE_ENI_MIRROR: string = 'CreateEniMirror';
export const EVENT_DETAIL_TYPE_DESTROY_ENI_MIRROR: string = 'DestroyEniMirror';

/**
 * These map directly to the specific commands executed by the user via the management CLI.  Since the strings are
 * shared between the TypeScript and Python sides of the application, they should ideally be in a shared config file
 * rather than hardcoded in both locations.
 */
export enum ManagementCmd {
    DeployDemoTraffic = 'DeployDemoTraffic',
    DestroyDemoTraffic = 'DestroyDemoTraffic',
    CreateCluster = 'CreateCluster',
    DestroyCluster = 'DestroyCluster',
    AddVpc = 'AddVpc',
    RemoveVpc = 'RemoveVpc',
}

