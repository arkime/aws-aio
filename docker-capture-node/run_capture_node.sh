#!/bin/bash

set -e

echo "============================================================"
echo "Cluster: $CLUSTER_NAME"
echo "Role: Capture Node"
echo "Capture Config SSM Param: $CAPTURE_CONFIG_SSM_PARAM"
echo "AWS Region: $AWS_REGION"
echo "Bucket Name: $BUCKET_NAME"
echo "LB Healthcheck Port: $LB_HEALTH_PORT"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "OpenSearch Secret Arn: $OPENSEARCH_SECRET_ARN"
echo "S3 Storage Class: $S3_STORAGE_CLASS"
echo "============================================================"

# Pull all required configuration files, scripts, etc from the cloud
source /bootstrap_config.sh

# Perform any final setup tasks
# It's expected that this file should be placed on disk by /bootstrap_config.sh
source /initialize_arkime.sh

# Start Arkime Capture
echo "Running Arkime Capture process ..."
/opt/arkime/bin/capture --config /opt/arkime/etc/config.ini
