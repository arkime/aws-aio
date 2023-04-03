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
import { Environment } from 'aws-cdk-lib';

const app = new cdk.App();

const params: (prms.CreateClusterParams | prms.DeployDemoTrafficParams | prms.DestroyDemoTrafficParams) = context.getCommandParams(app);

const env: Environment = { 
    account: params.awsAccount, 
    region: params.awsRegion
}

switch(params.type) {
    case "CreateClusterParams":
        const captureBucketStack = new CaptureBucketStack(app, params.nameCaptureBucket, {
            env: env
        });

        const captureVpcStack = new CaptureVpcStack(app, params.nameCaptureVpc, {
            env: env
        });

        const osDomainStack = new OpenSearchDomainStack(app, params.nameOSDomain, {
            env: env,
            captureVpc: captureVpcStack.vpc
        });
        osDomainStack.addDependency(captureVpcStack)

        const captureNodesStack = new CaptureNodesStack(app, params.nameCaptureNodes, {
            env: env,
            captureBucket: captureBucketStack.bucket,
            captureVpc: captureVpcStack.vpc,
            clusterName: params.nameCluster,
            osDomain: osDomainStack.domain,
            osPassword: osDomainStack.osPassword
        });
        captureNodesStack.addDependency(captureBucketStack)
        captureNodesStack.addDependency(captureVpcStack)
        captureNodesStack.addDependency(osDomainStack)

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



