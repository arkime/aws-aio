#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { TrafficGenStack } from '../lib/traffic-gen-stack';
import { Environment } from 'aws-cdk-lib';

const demo_env: Environment = { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION }

const app = new cdk.App();
new TrafficGenStack(app, 'TrafficGen01', {
    env: demo_env
});