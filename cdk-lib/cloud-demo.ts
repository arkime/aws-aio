#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import * as context from './core/context-wrangling';
import * as prms from './core/command-params';
import { TrafficGenStack } from './traffic-gen-sample/traffic-gen-stack';
import { CaptureVpcStack } from './capture-stacks/capture-vpc-stack';
import { Environment } from 'aws-cdk-lib';

const app = new cdk.App();

const params: (prms.CreateClusterParams | prms.DeployDemoTrafficParams | prms.DestroyDemoTrafficParams) = context.getCommandParams(app);

const env: Environment = { 
    account: params.awsAccount, 
    region: params.awsRegion
}

switch(params.type) {
    case "CreateClusterParams":
        new CaptureVpcStack(app, params.nameCaptureVpc, {
            env: env
        });
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



