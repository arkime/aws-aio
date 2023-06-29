#!/bin/bash

set -e

echo "============================================================"
echo "Cluster: $CLUSTER_NAME"
echo "Role: Capture Node"
echo "Arkime Config INI Path: $ARKIME_CONFIG_INI"
echo "Arkime Additional File Paths: $ARKIME_ADD_FILES"
echo "AWS Region: $AWS_REGION"
echo "Bucket Name: $BUCKET_NAME"
echo "LB Healthcheck Port: $LB_HEALTH_PORT"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "OpenSearch Secret Arn: $OPENSEARCH_SECRET_ARN"
echo "S3 Storage Class: $S3_STORAGE_CLASS"
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

sed -i'' "s/_BUCKET_/$BUCKET_NAME/g" /opt/arkime/etc/config.ini
sed -i'' "s/_HEALTH_PORT_/$LB_HEALTH_PORT/g" /opt/arkime/etc/config.ini
sed -i'' "s/_REGION_/$AWS_REGION/g" /opt/arkime/etc/config.ini
sed -i'' "s/_STORAGE_CLASS_/$S3_STORAGE_CLASS/g" /opt/arkime/etc/config.ini
echo "Successfully configured /opt/arkime/etc/config.ini"

echo "Testing connection/creds to OpenSearch domain $OPENSEARCH_ENDPOINT ..."
curl -u admin:$OPENSEARCH_PASS -X GET https://$OPENSEARCH_ENDPOINT:443
echo "Successfully connected to OpenSearch domain $OPENSEARCH_ENDPOINT"

# Initialize our OpenSearch Domain for the Arkime data if it hasn't already been initialized.
echo "Initializing Arkime Domains if not already done ..."
/opt/arkime/db/db.pl --esuser admin:$OPENSEARCH_PASS https://$OPENSEARCH_ENDPOINT:443 init --ifneeded
echo "Successfully initialized Arkime Domains"

# Create some local directories for Arkime to function correctly
mkdir -p /opt/arkime/logs
mkdir -p /opt/arkime/raw
chown nobody /opt/arkime/raw # Unneeded when using S3 offload

# Start Arkime Capture
echo "Running Arkime Capture process ..."
/opt/arkime/bin/capture
