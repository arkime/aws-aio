#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { TrafficGenStack } from './traffic-gen-sample/traffic-gen-stack';
import { Environment } from 'aws-cdk-lib';

const app = new cdk.App();

// This ENV variable is set by the CDK CLI.  It reads it from your AWS Credential profile, and configures the var
// before invoking CDK actions.
const aws_account: string | undefined = process.env.CDK_DEFAULT_ACCOUNT

// Like the CDK_DEFAULT_ACCOUNT, the CDK CLI sets the CDK_DEFAULT_REGION by reading the AWS Credential profile.
// However, we want the user to to able to specify a different region than the default so we optionaly pass in one
// via CDK Context ourselves.
const region_context = app.node.tryGetContext("ARKIME_REGION")
const aws_region: string | undefined = region_context ?? process.env.CDK_DEFAULT_REGION

const demo_env: Environment = { 
    account: aws_account, 
    region: aws_region
}

new TrafficGenStack(app, 'DemoTrafficGen01', {
    env: demo_env
});
new TrafficGenStack(app, 'DemoTrafficGen02', {
    env: demo_env
});