# Arkime Cloud Demo

The goals of this project are 1) provide a demonstration of how Arkime can be deployed in a cloud-native manner and 2) provide scripting to enable users to easily begin capturing the traffic in their existing AWS cloud infrastructure.

The AWS Cloud Development Kit (CDK) is used to perform infrastructure specification, setup, management, and teardown.  You can learn more about infrastructure-as-code using the CDK [here](https://docs.aws.amazon.com/cdk/v2/guide/home.html).

## How to run the demo

### Pre-requisites

* REQUIRED: A copy of the repo on your local host
* REQUIRED: A properly installed/configured copy of Node ([see instructions here](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm))
* REQUIRED: A properly installed/configured copy of Python 3.6+ and venv ([see instructions here](https://realpython.com/installing-python/))
* REQUIRED: A properly installed/configured copy of Docker (instructions vary by platform/organization)
* REQUIRED: A properly installed/configured copy of the CDK CLI ([see instructions here](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html))
* REQUIRED: Valid, accessible AWS Credentials (see [instructions here](https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html) and [here](https://docs.aws.amazon.com/sdk-for-javascript/v2/developer-guide/setting-credentials-node.html))
* HIGHLY RECOMMENDED: A properly installed/configured copy of the AWS CLI ([see instructions here](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))

Why each of these needed:
* Node is required to work with the CDK (our CDK Apps are written in TypeScript)
* The Management CLI is writting in Python, so Python is needed to run it
* Docker is required to transform our local Dockerfiles into images to be uploaded/deployed into the AWS Account by the CDK
* The CDK CLI is how we deploy/manage the underlying AWS CloudFormation Stacks that encapsulate the Arkime AWS Resoruces; the Management CLI wraps this
* The AWS CLI is recommended (but not strictly required) as a way to set up your AWS Credentials and default region, etc.  The CDK CLI needs these to be configured, but technically you can configure these manually without using the AWS CLI (see [the CDK setup guide](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_prerequisites) for details)

NOTE: By default, the CDK CLI will use the AWS Region specified as default in your AWS Configuration file; you can set this using the `aws configure` command.  It will also use the AWS Account your credentials are associated with.


### Setting up traffic generation
This demo uses Docker containers to generate traffic (`./docker-traffic-gen`).  The containers are simple Ubuntu boxes that continuously curl a selection of Alexa Top 20 websites.  You can run the container locally like so:

```
cd ./docker-traffic-gen
docker build --tag traffic-gen .
docker run --name traffic-gen traffic-gen
```

You can deploy a AWS Fargate-backed copy of this container to your AWS Account like so.  First, set up your Python virtual environment:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Next, invoke the management CLI.  It will use your default AWS Credentials and Region unless you specify otherwise (see `./manage_arkime.py --help`).

```
./manage_arkime.py deploy-demo-traffic
```

## How to run the unit tests

### Step 1 - Activate your Python virtual environment

To isolate the Python environment for the project from your local machine, create virtual environment like so:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You can exit the Python virtual environment and remove its resources like so:
```
deactivate
rm -rf .venv
```

Learn more about venv [here](https://docs.python.org/3/library/venv.html).

### Step 2 - Run Pytest
The unit tests are executed by invoking Pytest:

```
python -m pytest test_manage_arkime/
```

You can read more about running unit tests with Pytest [here](https://docs.pytest.org/en/7.2.x/how-to/usage.html).

## Performing CDK Bootstrap

Before deploying AWS Resources to your account using the CDK, you must first perform a bootstrapping step.  The management CLI should take care of this for you, but the following is provided in case you want/need to do this manually.

At a high level the CDK needs some existing resources in your AWS account before it deploys your target infrastructure, which you can [learn more about here](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html).  Examples include an AWS S3 bucket to stage deployment resources and an AWS ECR repo to receive/house locally-defined Docker images.

You can bootstrap your AWS Account/Region like so:

```
cdk bootstrap
```

## Generally useful NPM/CDK commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `cdk deploy`      deploy this stack to your default AWS account/region
* `cdk diff`        compare deployed stack with current state
* `cdk synth`       emits the synthesized CloudFormation template