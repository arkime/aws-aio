# Arkime AWS All-in-One

The goals of this project are 1) provide a demonstration of how Arkime can be deployed in a cloud-native manner and 2) provide scripting to enable users to easily begin capturing the traffic in their existing AWS cloud infrastructure.

The AWS Cloud Development Kit (CDK) is used to perform infrastructure specification, setup, management, and teardown.  You can learn more about infrastructure-as-code using the CDK [here](https://docs.aws.amazon.com/cdk/v2/guide/home.html).


## Architecture and Design

This tool provides a Python CLI which the user can interact with to manage the Arkime installation(s) in their account.  The Python CLI wraps a CDK App.  The CLI provides orchestration; the CDK App provides the CloudFormation Templates based on inputs from the CLI and performs CloudFormation create/update/destroy operations.  State about the user's deployed Arkime Clusters is stored in the user's AWS Account using [the AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html).  The capture itself is performed by using [VPC Traffic Mirroring](https://docs.aws.amazon.com/vpc/latest/mirroring/what-is-traffic-mirroring.html) to mirror traffic to/from [the elastic network interfaces](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-eni.html) in the user's VPC through [a Gateway Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/introduction.html) and into another VPC (the Capture VPC), created by the CLI, in the user's account.  The Arkime Capture Nodes live in the Capture VPC.

When a VPC is added to a Cluster with the `vpc-add` command, we attempt to set up monitoring for all network interfaces in the target VPC.  After initial this setup, we listen for changes in the VPC [using AWS EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html) and attempt to automatically create/destroy mirroring accordingly.  This should enable the user's fleet to scale naturally while still having its traffic captured/monitored by Arkime.  We currently provide automated, on-going monitoring of the following resource types:
* EC2 Instances
* EC2 Autoscaling Groups
* ECS-on-EC2 Container Instances
* Fargate Tasks

Resources of those types should have capture configured for them when they are brought online and taken offline.

**Figure 1:** Current high level design of the Arkime AWS All-in-One Project

![High Level Design](./cloud_arkime_design.png?raw=true)


**Figure 2:** Current detailed design of the Arkime AWS All-in-One Project

![Detailed Design](./cloud_arkime_design_detailed.png?raw=true)


## How to run the AWS All-in-One CLI

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

# To build the docker container
npm run build

# To run the docker container
npm run start

# To stop the docker container
npm run stop
```

You can deploy copies of this container to your AWS Account like so.  First, set up your Python virtual environment:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Next, pull in the Node dependencies required for the CDK:

```
npm ci
```

Finally, invoke the management CLI.  It will use your default AWS Credentials and Region unless you specify otherwise (see `./manage_arkime.py --help`).

```
./manage_arkime.py demo-traffic-deploy
```

You can tear down the demo stacks using an additional command:

```
./manage_arkime.py demo-traffic-deploy
```

### Setting up your Arkime Cluster

You can deploy the Arkime Cluster into your AWS account like so:

```
./manage_arkime.py cluster-create --name MyCluster
```

**NOTE:** You must perform a manual action in your AWS Account in order for this deployment to succeed.  Specifically you must [create an IAM Service Linked Role for AWS OpenSearch](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/slr.html) to be able to manage the OpenSearch Domain.  This is very easy to do with the AWS CLI, and only needs to be done once per AWS Account:

```
aws iam create-service-linked-role --aws-service-name es.amazonaws.com
```

You can see your created cluster and the VPCs it is currently monitoring using the `clusters-list` command, like so:

```
./manage_arkime.py clusters-list
```

By default, you will be given the minimum-size Capture Cluster.  You can provision a Cluster that will serve your expected usage using a set of optional command-line parameters, which will ensure the EC2 Capture Nodes and OpenSearch Domain are suitably provisioned (plus a little extra for safety):

```
./manage_arkime.py cluster-create --name MyCluster --expected-traffic 1 --spi-days 30 --replicas 1
```

### Setting up capture for a VPC

Once you have an Arkime Cluster, you can begin capturing traffic in a target VPC using the `vpc-add` command, like so:

```
./manage_arkime.py vpc-add --cluster-name MyCluster --vpc-id vpc-123456789
```

**NOTE:** There are some caveats you need to be aware of.  First, the VPC must be in the same AWS Account and Region as the Arkime Cluster.  Second, the capture setup is currently static, meaning if the network configuration of your VPC changes or your compute fleet changes (due to instance replacement, scaling events, etc), those changes will not be reflected in the capture.  We're working on a solution for this.

### Viewing the captured sessions

You can log into your Viewer Dashboard using credentials from the `get-login-details` command, which will provide the URL, username, and password of the Arkime Cluster.

```
./manage_arkime.py get-login-details --name MyCluster
```

**NOTE:** By default, we set up HTTPS using a self-signed certificate which your browser will give you a warning about when you visit the dashboard URL.  In \*most\* situations, you can just acknowledge the risk and click through.  However, if you're using Chrome on Mac OS you might not be allowed to click through ([see here](https://stackoverflow.com/questions/58802767/no-proceed-anyway-option-on-neterr-cert-invalid-in-chrome-on-macos)).  In that case, you'll need to click on the browser window so it's in focus and type the exact phrase `thisisunsafe` and it will let you through.

### Changing Arkime Configuration

We deploy default configuration for the Arkime Capture and Viewer processes that work "out of the box".  However, you can customize the configuration for those processes - and add custom behavior to your Capture and Viewer Nodes.

As part of running `cluster-create`, the CLI will create a new, cluster-specific directory at the root of this repo on-disk that contains the configuration/scripts that will be deployed into your containers (currently at: `./config-YourClusterName-AccountNum-AwsRegion`).  This directory contains two sub directories which contain all the scripts/configuration that are copied onto the Capture (`./config-YourClusterName-AccountNum-AwsRegion/capture/`) and Viewer (`./config-YourClusterName-AccountNum-AwsRegion/viewer/`) Nodes as part of their startup process.  By default, these directories will just contain the aforementioned "default configuration", but you're free to edit the files there or even add new ones.  Any files in the `./config-YourClusterName-AccountNum-AwsRegion/capture/` will end copied to your Capture Nodes; any files in the `./config-YourClusterName/viewer/` will end copied to your Viewer Nodes.

```
chelma@3c22fba4e266 aws-aio % tree config-YourClusterName-111111111111-us-east-2
config-YourClusterName-111111111111-us-east-2
├── capture
│   ├── config.ini
│   ├── default.rules
│   └── initialize_arkime.sh
├── viewer
│   ├── config.ini
│   └── initialize_arkime.sh
```

To help understand how this process works (and how to leverage the system to your benefit), here's an overview of how this currently works:
1. During `cluster-create`, we turn the `capture/` and `viewer/` config directories into archives and stick them in AWS S3.
2. When ECS starts the Capture and Viewer Nodes, it invokes the `run_*_node.sh` scripts embedded in their Docker Image
3. The `run_*_node.sh` script invokes the `bootstrap_config.sh` script, also embedded in their Docker Image, which pulls the configuration tarball from S3 and unpacks it onto disk
4. The `run_*_node.sh` script invokes the `initialize_arkime.sh` script, which is one of the files in your `capture/` and `viewer/` config directories locally, and sent to the container via the tarball in S3.  By default, it performs some final initialization to make the pre-canned behavior "go".  You can modify this script to perform any steps you'd like, and stick any new files you need in the container in the `capture/` and `viewer/` config directories.
5. The `run_*_node.sh` script starts the Arkime Capture/Viewer process

After running `cluster-create` and uploading the initial configuration, you'll need to use the `config-update` CLI call to deploy changed configuration to your Capture/Viewer Nodes.  This is to improve deployment safety by providing a clearer rollback path in the event the new configuration doesn't work out as expected.

`config-update` will take a look at the local configuration and compare it what is currently deployed on your Nodes.  If the local configuration is different, it will be archived, sent to S3, and your ECS Containers recycled to pull down the new configuration.  If we see that Containers with the new configuration fail to start up correctly, we automatically revert to the previously deployed configuration.

### Viewing the Deployed Clusters

To see the clusters you currently have deployed, you can use the `clusters-list` CLI command.  This will return a list of clusters and their associated details like so:
```
[
    {
        "cluster_name": "MyCluster",
        "opensearch_domain": "arkimedomain872-1nzuztrqm7dl",
        "configuration_capture": {
            "aws_aio_version": "1",
            "config_version": "7",
            "md5_version": "64295265159ac577cf741bb4d1966fcc",
            "source_version": "v0.1.1-10-g3487548",
            "time_utc": "2023-07-27 18:26:23"
        },
        "configuration_viewer": {
            "aws_aio_version": "1",
            "config_version": "1",
            "md5_version": "be13e172a6440fcd6a7e73c8ae41457b",
            "source_version": "v0.1.1-7-g9c2d7ca",
            "time_utc": "2023-07-24 17:04:25"
        },
        "monitored_vpcs": [
            {
                "vpc_id": "vpc-008d258d7c536384b",
                "vni": "15"
            }
        ]
    }
]
```

An explanation of the returned fields is as follows:
* **cluster_name:** The name of your Arkime Cluster
* **opensearch_domain:** The name of your Arkime Cluster's OpenSearch Domain
* **configuration_capture:** The details of your Capture Nodes' deployed configuration
    * **aws_aio_version:** A version number used to track backwards compatibility within the AWS AIO project
    * **config_version:** An integer that's incremented every time new Arkime Configuration is deployed (e.g. whenever you run `config-update` with new configuration).  Used to keep track of which configuration archive in S3 is deployed to your ECS Containers.
    * **md5_version:** The md5 hash of the deployed Arkime Configuration archive.  Used to find changes in configuration.
    * **source_version:** A version tracker for the AWS AIO CLI source code running on the client machine.
    * **time_utc:** A UTC timestamp for when the Arkime Configuration archive deployed to your Nodes was created.
* **configuration_viewer:** The details of your Viewer Nodes' deployed configuration
* **monitored_vpcs:** The VPCs your Arkime Cluster is currently monitoring
    * **vpc_id:** The AWS VPC ID of the VPC being monitored
    * **vni:** The Virtual Network Identifier (VNI) assigned to this VPC within Arkime.  Makes it possible to uniquely identify traffic from each VPC being monitored.

### Tearing down your Arkime Cluster

You can destroy the Arkime Cluster in your AWS account by first turning off traffic capture for all VPCs:

```
./manage_arkime.py vpc-remove --cluster-name MyCluster --vpc-id vpc-123456789
```

and then terminating the Arkime Cluster:

```
./manage_arkime.py cluster-destroy --name MyCluster
```

By default, this will tear down the Capture/Viewer Nodes and leave the OpenSearch Domain and Capture Bucket intact.  Consequently, it will also leave a number of CloudFormation stacks in place as well.  

If you want to tear down **EVERYTHING** and are willing to blow away all your data, you can use the "nuke" option:

```
./manage_arkime.py cluster-destroy --name MyCluster --destroy-everything
```

## How to shell into the ECS containers

It's possible to create interactive terminal sessions inside the ECS Docker containers deployed into your account.  The official documentation/blog posts are a bit confusing, so we explain the process here.  The ECS tasks we spin up have all been pre-configured on the server-side to enable this, so what you need to do is the stuff on the client-side (e.g. your laptop).  This process involves using the ECS Exec capability to perform a remote Docker Exec, and works even if your Tasks are running in private subnets.  You can learn way more in [this (verbose/confusing) blog post](https://aws.amazon.com/blogs/containers/new-using-amazon-ecs-exec-access-your-containers-fargate-ec2/).

First, you need a recent version of the AWS CLI that has the required commands.  You can install/update your installation with [the instructions here](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).

Second, you need to install the Session Manager Plugin for the AWS CLI using [the instructions here](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html).

Finally, you can create an interactive session using the AWS CLI.  You'll need to know the ECS Cluster ID and the Task ID, which you can find either using the AWS CLI or the AWS Console.

```
aws ecs execute-command --cluster <your cluster ID> --container CaptureContainer --task <your task id> --interactive --command "/bin/bash"
```

## How to run the unit tests

### Step 1 - Activate your Python virtual environment

To isolate the Python environment for the project from your local machine, create virtual environment like so:
```
python3 -m venv .venv
source .venv/bin/activate
cd manage_arkime/
pip install -r requirements.txt
cd ../
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


## Account Limits, Scaling, and Other Concerns

In general, it should be assumed that this setup is intended for "light to medium usage".  In other words, don't expect to pour massive amounts of data through it.  The wording here is intentionally vague to encourage the reader to assess for themselves whether it will scale for their use-case.  Ideally, load testing will be performed on the setup to give a bit more specifity here but that is not guaranteed.

Here are some scaling things that you'll want to consider:
* The compute/memory capacity of individual Capture Nodes
* The maximum scaling limit of the Capture Nodes ECS Service as well as the scaling conditions
* The number of availability zones the setup launches in, and whether specific zones are required
* The max throughput of a single Gateway Load Balancer Endpoint is 100 Gbps, and we provision one per User subnet
* The max number of CIDR ranges a User VPC can have is 4, due to the hard cap on Traffic Mirroring Filter Rules

Here are some account limits you'll want to watch out for:
* Number of EIPs per region is small, and we spin up several for each Arkime Cluster
* There's a max of 10,000 Traffic Mirroring Sessions.  We use one per traffic source.
* There's a max of 10,000 Standard SSM Parameters per account/region.  We use at least one for each User ENI, several for each Subnet in a User VPC, and several for each User VPC and Cluster.


## Generally useful NPM/CDK commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `cdk deploy`      deploy this stack to your default AWS account/region
* `cdk diff`        compare deployed stack with current state
* `cdk synth`       emits the synthesized CloudFormation template
