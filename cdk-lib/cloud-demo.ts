#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import * as context from './core/context-wrangling';
import * as prms from './core/command-params';
import { TrafficGenStack } from './traffic-gen-sample/traffic-gen-stack';
import { CaptureBucketStack } from './capture-stacks/capture-bucket-stack';
import { CaptureNodesStack } from './capture-stacks/capture-nodes-stack';
import { CaptureVpcStack } from './capture-stacks/capture-vpc-stack';
import { OpenSearchDomainStack } from './capture-stacks/opensearch-domain-stack';
import { ViewerNodesStack } from './viewer-stacks/viewer-nodes-stack';
import { VpcMirrorStack } from './mirror-stacks/vpc-mirror-stack';
import { Environment } from 'aws-cdk-lib';

const app = new cdk.App();

const params: (prms.ClusterMgmtParams | prms.DeployDemoTrafficParams | prms.DestroyDemoTrafficParams | prms.MirrorMgmtParams) = context.getCommandParams(app);

const env: Environment = { 
    account: params.awsAccount, 
    region: params.awsRegion
}

switch(params.type) {
    case "ClusterMgmtParams":
        const captureBucketStack = new CaptureBucketStack(app, params.nameCaptureBucketStack, {
            env: env,
            ssmParamName: params.nameCaptureBucketSsmParam,
        });

        const captureVpcStack = new CaptureVpcStack(app, params.nameCaptureVpcStack, {
            env: env
        });

        const osDomainStack = new OpenSearchDomainStack(app, params.nameOSDomainStack, {
            env: env,
            captureVpc: captureVpcStack.vpc,
            ssmParamName: params.nameOSDomainSsmParam,
        });
        osDomainStack.addDependency(captureVpcStack)

        const captureNodesStack = new CaptureNodesStack(app, params.nameCaptureNodesStack, {
            env: env,
            captureBucket: captureBucketStack.bucket,
            captureBucketKey: captureBucketStack.bucketKey,
            captureVpc: captureVpcStack.vpc,
            clusterName: params.nameCluster,
            osDomain: osDomainStack.domain,
            osPassword: osDomainStack.osPassword,
            ssmParamNameCluster: params.nameClusterSsmParam
        });
        captureNodesStack.addDependency(captureBucketStack)
        captureNodesStack.addDependency(captureVpcStack)
        captureNodesStack.addDependency(osDomainStack)

        const viewerNodesStack = new ViewerNodesStack(app, params.nameViewerNodesStack, {
            env: env,
            captureBucket: captureBucketStack.bucket,
            viewerVpc: captureVpcStack.vpc,
            clusterName: params.nameCluster,
            osDomain: osDomainStack.domain,
            osPassword: osDomainStack.osPassword,
            ssmParamNameViewerDns: params.nameViewerDnsSsmParam,
            ssmParamNameViewerPass: params.nameViewerPassSsmParam,
        });
        viewerNodesStack.addDependency(captureBucketStack)
        viewerNodesStack.addDependency(captureVpcStack)
        viewerNodesStack.addDependency(osDomainStack)
        viewerNodesStack.addDependency(captureNodesStack)

        break;
    case "MirrorMgmtParams":
        new VpcMirrorStack(app, params.nameVpcMirrorStack, {
            subnetIds: params.listSubnetIds,
            subnetSsmParamNames: params.listSubnetSsmParams,
            vpcId: params.idVpc,
            vpcSsmParamName: params.nameVpcSsmParam,
            vpceServiceId: params.idVpceService
        })
        break;
    case "DeployDemoTrafficParams":
        new TrafficGenStack(app, 'DemoTrafficGen01', {
            env: env
        });
        new TrafficGenStack(app, 'DemoTrafficGen02', {
            env: env
        });
        break;
    case "DestroyDemoTrafficParams":
        new TrafficGenStack(app, 'DemoTrafficGen01', {
            env: env
        });
        new TrafficGenStack(app, 'DemoTrafficGen02', {
            env: env
        });
        break;
}



