#!/bin/bash

set -e

echo "============================================================"
echo "Cluster: $CLUSTER_NAME"
echo "Role: Viewer Node"
echo "AWS Region: $AWS_REGION"
echo "Bucket Name: $BUCKET_NAME"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "OpenSearch Secret Arn: $OPENSEARCH_SECRET_ARN"
echo "Viewer Port: $VIEWER_PORT"
echo "Viewer Password Secret Arn: $VIEWER_PASS_ARN"
echo "============================================================"

# Pull configuration from ENV and AWS in order to set up our Arkime install.  The ENV variables come from the Fargate
# Container definition.  We perform some escaping of the our replacement strings for safety.
# See: https://stackoverflow.com/questions/407523/escape-a-string-for-a-sed-replace-pattern
echo "Configuring /opt/arkime/etc/config.ini ..."
ESCAPED_ENDPOINT=$(printf '%s\n' "$OPENSEARCH_ENDPOINT" | sed -e 's/[\/&]/\\&/g')
sed -i'' "s/_ENDPOINT_/$ESCAPED_ENDPOINT/g" /opt/arkime/etc/config.ini

OPENSEARCH_PASS=$(aws secretsmanager get-secret-value --secret-id $OPENSEARCH_SECRET_ARN --output text --query SecretString)
BASE64_AUTH=$(echo -n "admin:$OPENSEARCH_PASS" | base64)
sed -i'' "s/_AUTH_/$BASE64_AUTH/g" /opt/arkime/etc/config.ini

VIEWER_PASS=$(aws secretsmanager get-secret-value --secret-id $VIEWER_PASS_ARN --output text --query SecretString)

sed -i'' "s/_VIEW_PORT_/$VIEWER_PORT/g" /opt/arkime/etc/config.ini
echo "Successfully configured /opt/arkime/etc/config.ini"

echo "Testing connection/creds to OpenSearch domain $OPENSEARCH_ENDPOINT ..."
curl -u admin:$OPENSEARCH_PASS -X GET https://$OPENSEARCH_ENDPOINT:443
echo "Successfully connected to OpenSearch domain $OPENSEARCH_ENDPOINT"

# Create some local directories for Arkime to function correctly
mkdir -p /opt/arkime/logs
mkdir -p /opt/arkime/raw

# Start Arkime Viewer
echo "Running Arkime Viewer process ..."
cd /opt/arkime/viewer
/opt/arkime/bin/node addUser.js admin admin $VIEWER_PASS --admin --packetSearch
/opt/arkime/bin/node viewer.js