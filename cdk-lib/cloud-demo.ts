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
    case 'ClusterMgmtParams':
        const captureBucketStack = new CaptureBucketStack(app, params.nameCaptureBucketStack, {
            env: env,
            planCluster: params.planCluster,
            ssmParamName: params.nameCaptureBucketSsmParam,
        });

        const captureVpcStack = new CaptureVpcStack(app, params.nameCaptureVpcStack, {
            env: env,
            planCluster: params.planCluster,
        });

        const osDomainStack = new OpenSearchDomainStack(app, params.nameOSDomainStack, {
            env: env,
            captureVpc: captureVpcStack.vpc,
            planCluster: params.planCluster,
            ssmParamName: params.nameOSDomainSsmParam,
        });
        osDomainStack.addDependency(captureVpcStack)

        const captureNodesStack = new CaptureNodesStack(app, params.nameCaptureNodesStack, {
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

        const viewerNodesStack = new ViewerNodesStack(app, params.nameViewerNodesStack, {
            env: env,
            arnViewerCert: params.nameViewerCertArn,
            captureBucket: captureBucketStack.bucket,
            viewerVpc: captureVpcStack.vpc,
            clusterConfigBucketName: params.nameClusterConfigBucket,
            clusterName: params.nameCluster,
            osDomain: osDomainStack.domain,
            osPassword: osDomainStack.osPassword,
            ssmParamNameViewerConfig: params.nameViewerConfigSsmParam,
            ssmParamNameViewerDetails: params.nameViewerDetailsSsmParam,
        });
        viewerNodesStack.addDependency(captureBucketStack)
        viewerNodesStack.addDependency(captureVpcStack)
        viewerNodesStack.addDependency(osDomainStack)
        viewerNodesStack.addDependency(captureNodesStack)

        break;
    case 'MirrorMgmtParams':
        new VpcMirrorStack(app, params.nameVpcMirrorStack, {
            clusterName: params.nameCluster,
            eventBusArn: params.arnEventBus,
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



