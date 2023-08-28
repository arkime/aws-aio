#!/bin/bash

# Move the files we pulled from the cloud to their correct locations
mv /arkime_config/config.ini /opt/arkime/etc/config.ini

# Pull configuration from ENV and AWS in order to set up our Arkime install.  The ENV variables come from the Fargate
# Container definition.  We perform some escaping of the our replacement strings for safety.
# See: https://stackoverflow.com/questions/407523/escape-a-string-for-a-sed-replace-pattern
echo "Configuring /opt/arkime/etc/config.ini ..."
ESCAPED_ENDPOINT=$(printf '%s\n' "$OPENSEARCH_ENDPOINT" | sed -e 's/[\/&]/\\&/g')
sed -i'' "s/_OS_ENDPOINT_/$ESCAPED_ENDPOINT/g" /opt/arkime/etc/config.ini

OPENSEARCH_PASS=$(aws secretsmanager get-secret-value --secret-id $OPENSEARCH_SECRET_ARN --output text --query SecretString)
BASE64_AUTH=$(echo -n "admin:$OPENSEARCH_PASS" | base64)
sed -i'' "s/_OS_AUTH_/$BASE64_AUTH/g" /opt/arkime/etc/config.ini

VIEWER_PASS_OBJ=$(aws secretsmanager get-secret-value --secret-id $VIEWER_PASS_ARN --output text --query SecretString)
ADMIN_PASSWORD=$(echo $VIEWER_PASS_OBJ | jq -r .adminPassword)
AUTH_SECRET=$(echo $VIEWER_PASS_OBJ | jq -r .authSecret)

sed -i'' "s/_VIEWER_PORT_/$VIEWER_PORT/g" /opt/arkime/etc/config.ini
sed -i'' "s/_AUTH_SECRET_/$AUTH_SECRET/g" /opt/arkime/etc/config.ini
sed -i'' "s/_VIEWER_DNS_/$VIEWER_DNS/g" /opt/arkime/etc/config.ini
echo "Successfully configured /opt/arkime/etc/config.ini"

echo "Testing connection/creds to OpenSearch domain $OPENSEARCH_ENDPOINT ..."
curl -u admin:$OPENSEARCH_PASS -X GET https://$OPENSEARCH_ENDPOINT:443
echo "Successfully connected to OpenSearch domain $OPENSEARCH_ENDPOINT"

# Create some local directories for Arkime to function correctly
mkdir -p /opt/arkime/logs
mkdir -p /opt/arkime/raw
