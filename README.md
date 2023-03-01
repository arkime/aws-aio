# Arkime Cloud Demo

The goals of this project are 1) provide a demonstration of how Arkime can be deployed in a cloud-native manner and 2) provide scripting to enable users to easily begin capturing the traffic in their existing AWS cloud infrastructure.

The AWS Cloud Development Kit (CDK) is used to perform infrastructure specification, setup, management, and teardown.  You can learn more about infrastructure-as-code using the CDK [here](https://docs.aws.amazon.com/cdk/v2/guide/home.html).

## How to run the demo

### Pre-requisites

* REQUIRED: A copy of the repo on your local host
* REQUIRED: A properly installed/configured copy of Node ([see instructions here](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm))
* REQUIRED: A properly installed/configured copy of the CDK CLI ([see instructions here](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html))
* REQUIRED: Valid, accessible AWS Credentials (see [instructions here](https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html) and [here](https://docs.aws.amazon.com/sdk-for-javascript/v2/developer-guide/setting-credentials-node.html))
* HIGHLY RECOMMENDED: A properly installed/configured copy of the AWS CLI ([see instructions here](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))

NOTE: By default, the CDK CLI will use the AWS Region specified as default in your AWS Configuration file; you can set this using the `aws configure` command.  It will also use the AWS Account your credentials are associated with.

### Perform CDK Bootstrap

Before deploying AWS Resources to your account using the CDK, you must first perform a bootstrapping step.  While you can [learn more about that step here](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html), at a high level the CDK needs some existing resources in your AWS account before it deploys your target infrastructure.  Examples include an AWS S3 bucket to stage deployment resources and an AWS ECR repo to receive/house locally-defined Docker images.

You can bootstrap your AWS Account/Region like so:

```
cdk bootstrap
```

### Setting up traffic generation
This demo uses Docker containers to generate traffic (`./docker-traffic-gen`).  The containers are simple Ubuntu boxes that continuously curl a selection of Alexa Top 20 websites.  You can run the container locally like so:

```
cd ./docker-traffic-gen
docker build --tag traffic-gen .
docker run --name traffic-gen traffic-gen
```

You can deploy a AWS Fargate-backed copy of this container to your AWS Account like so:

```
cdk deploy TrafficGen01
```

## Generally useful NPM/CDK commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `cdk deploy`      deploy this stack to your default AWS account/region
* `cdk diff`        compare deployed stack with current state
* `cdk synth`       emits the synthesized CloudFormation template