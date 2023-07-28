#!/bin/bash

set -e

echo "============================================================"
echo "Cluster: $CLUSTER_NAME"
echo "Role: Viewer Node"
echo "Viewer Config SSM Param: $VIEWER_CONFIG_SSM_PARAM"
echo "Arkime Config INI Datastore Location: $ARKIME_CONFIG_INI_LOC"
echo "Arkime Additional File Datastore Locations: $ARKIME_ADD_FILE_LOCS"
echo "AWS Region: $AWS_REGION"
echo "Bucket Name: $BUCKET_NAME"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "OpenSearch Secret Arn: $OPENSEARCH_SECRET_ARN"
echo "Viewer Dashboard DNS: $VIEWER_DNS"
echo "Viewer Port: $VIEWER_PORT"
echo "Viewer Password Secret Arn: $VIEWER_PASS_ARN"
echo "Viewer User: $VIEWER_USER"
echo "============================================================"

# Pull all required configuration files, scripts, etc from the cloud
source /bootstrap_config.sh

# Perform any final setup tasks
# It's expected that this file should be placed on disk by /bootstrap_config.sh
source /initialize_arkime.sh

# Start Arkime Viewer
echo "Running Arkime Viewer process ..."
cd /opt/arkime/viewer
/opt/arkime/bin/node addUser.js $VIEWER_USER $VIEWER_USER $VIEWER_PASS --admin --packetSearch
/opt/arkime/bin/node viewer.js -c /opt/arkime/etc/config.ini