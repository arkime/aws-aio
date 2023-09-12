#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import * as context from './core/context-wrangling';
import * as prms from './core/command-params';
import { TrafficGenStack } from './traffic-gen-sample/traffic-gen-stack';
import { CaptureBucketStack } from './capture-stacks/capture-bucket-stack';
import { CaptureNodesStack } from './capture-stacks/capture-nodes-stack';
import { CaptureTgwStack } from './capture-stacks/capture-tgw-stack';
import { CaptureVpcStack } from './capture-stacks/capture-vpc-stack';
import { OpenSearchDomainStack } from './capture-stacks/opensearch-domain-stack';
import { ViewerNodesStack } from './viewer-stacks/viewer-nodes-stack';
import { ViewerVpcStack } from './viewer-stacks/viewer-vpc-stack';
import { VpcMirrorStack } from './mirror-stacks/vpc-mirror-stack';
import { Environment } from 'aws-cdk-lib';

const app = new cdk.App();

const params: (prms.ClusterMgmtParams | prms.DeployDemoTrafficParams | prms.DestroyDemoTrafficParams | prms.MirrorMgmtParams) = context.getCommandParams(app);

const env: Environment = {
    account: params.awsAccount,
    region: params.awsRegion
}

switch(params.type) {
    case 'ClusterMgmtParams':
        const captureBucketStack = new CaptureBucketStack(app, params.stackNames.captureBucket, {
            env: env,
            planCluster: params.planCluster,
            ssmParamName: params.nameCaptureBucketSsmParam,
        });

        const captureVpcStack = new CaptureVpcStack(app, params.stackNames.captureVpc, {
            env: env,
            planCluster: params.planCluster,
        });

        const osDomainStack = new OpenSearchDomainStack(app, params.stackNames.osDomain, {
            env: env,
            captureVpc: captureVpcStack.vpc,
            planCluster: params.planCluster,
            ssmParamName: params.nameOSDomainSsmParam,
        });
        osDomainStack.addDependency(captureVpcStack)

        const captureNodesStack = new CaptureNodesStack(app, params.stackNames.captureNodes, {
            env: env,
            captureBucket: captureBucketStack.bucket,
            captureBucketKey: captureBucketStack.bucketKey,
            captureVpc: captureVpcStack.vpc,
            clusterConfigBucketName: params.nameClusterConfigBucket,
            clusterName: params.nameCluster,
            osDomain: osDomainStack.domain,
            osPassword: osDomainStack.osPassword,
            planCluster: params.planCluster,
            ssmParamNameCaptureConfig: params.nameCaptureConfigSsmParam,
            ssmParamNameCaptureDetails: params.nameCaptureDetailsSsmParam,
            ssmParamNameCluster: params.nameClusterSsmParam,
            userConfig: params.userConfig
        });
        captureNodesStack.addDependency(captureBucketStack)
        captureNodesStack.addDependency(captureVpcStack)
        captureNodesStack.addDependency(osDomainStack)


        let vpcStackToUse = null;

        if (params.planCluster.viewerVpc == null){
            vpcStackToUse = captureVpcStack;
        } else {
            const captureTgwStack = new CaptureTgwStack(app, params.stackNames.captureTgw, {
                env: env,
                captureVpc: captureVpcStack.vpc
            });
            captureTgwStack.addDependency(captureVpcStack)

            const viewerVpcStack = new ViewerVpcStack(app, params.stackNames.viewerVpc, {
                env: env,
                captureTgw: captureTgwStack.tgw,
                captureVpc: captureVpcStack.vpc,
                viewerVpcPlan: params.planCluster.viewerVpc
            });
            viewerVpcStack.addDependency(captureVpcStack)
            viewerVpcStack.addDependency(captureTgwStack)

            vpcStackToUse = viewerVpcStack;
        }

        const viewerNodesStack = new ViewerNodesStack(app, params.stackNames.viewerNodes, {
            env: env,
            arnViewerCert: params.nameViewerCertArn,
            captureBucket: captureBucketStack.bucket,
            viewerVpc: vpcStackToUse.vpc,
            clusterConfigBucketName: params.nameClusterConfigBucket,
            clusterName: params.nameCluster,
            osDomain: osDomainStack.domain,
            osPassword: osDomainStack.osPassword,
            ssmParamNameViewerConfig: params.nameViewerConfigSsmParam,
            ssmParamNameViewerDetails: params.nameViewerDetailsSsmParam,
            planCluster: params.planCluster,
        });
        viewerNodesStack.addDependency(captureBucketStack)
        viewerNodesStack.addDependency(vpcStackToUse)
        viewerNodesStack.addDependency(osDomainStack)
        viewerNodesStack.addDependency(captureNodesStack)

        break;
    case 'MirrorMgmtParams':
        new VpcMirrorStack(app, params.nameVpcMirrorStack, {
            clusterName: params.nameCluster,
            subnetIds: params.listSubnetIds,
            subnetSsmParamNames: params.listSubnetSsmParams,
            vpcId: params.idVpc,
            vpcCidrs: params.vpcCidrs,
            vpcSsmParamName: params.nameVpcSsmParam,
            vpceServiceId: params.idVpceService,
            mirrorVni: params.idVni,
        })
        break;
    case 'DeployDemoTrafficParams':
        new TrafficGenStack(app, 'DemoTrafficGen01', {
            cidr: "10.0.0.0/16",
            env: env
        });
        new TrafficGenStack(app, 'DemoTrafficGen02', {
            cidr: "192.168.0.0/17",
            env: env
        });
        break;
    case 'DestroyDemoTrafficParams':
        new TrafficGenStack(app, 'DemoTrafficGen01', {
            cidr: "10.0.0.0/16",
            env: env
        });
        new TrafficGenStack(app, 'DemoTrafficGen02', {
            cidr: "192.168.0.0/17",
            env: env
        });
        break;
}



