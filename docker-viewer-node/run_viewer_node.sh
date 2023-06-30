#!/bin/bash

set -e

echo "============================================================"
echo "Cluster: $CLUSTER_NAME"
echo "Role: Viewer Node"
echo "Arkime Config INI Path: $ARKIME_CONFIG_INI"
echo "Arkime Additional File Paths: $ARKIME_ADD_FILES"
echo "AWS Region: $AWS_REGION"
echo "Bucket Name: $BUCKET_NAME"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "OpenSearch Secret Arn: $OPENSEARCH_SECRET_ARN"
echo "Viewer Port: $VIEWER_PORT"
echo "Viewer Password Secret Arn: $VIEWER_PASS_ARN"
echo "Viewer User: $VIEWER_USER"
echo "============================================================"

# Pull our configuration files from the cloud
function write_file_from_param() {
    path=$1

    # Retrieve our file from the cloud and account for wacky escaping
    param_val=$(aws ssm get-parameter --name "$path" --query Parameter.Value)
    corrected_string=$(echo "$param_val" | sed 's/\\\"/\"/g' | sed 's/\\\\/\\/g') # Remove extra escaping
    corrected_string=$(echo "$corrected_string" | sed 's/^"//' | sed 's/"$//') # Remove starting/ending quotes

    # Pull out the values we need
    file_name=$(echo "$corrected_string" | jq -r '.file_name')
    echo "File Name: $file_name" >&2
    path_prefix=$(echo "$corrected_string" | jq -r '.path_prefix')
    echo "File Path Prefix: $path_prefix" >&2
    contents=$(echo "$corrected_string" | jq -r '.contents')
    full_path="$path_prefix/$file_name"

    # Write the file to disk
    echo -e "$contents" > "$full_path"

    # Return the path to the calling context
    echo "$full_path"
}

echo "$ARKIME_ADD_FILES" | jq -r '.[]' | while IFS= read -r path; do
    echo "Processing File in Param: $path"
    full_file_path=$(write_file_from_param "$path")
    echo "Written to: $full_file_path"
done

echo "Processing config.ini in Param: $ARKIME_CONFIG_INI"
config_ini_path=$(write_file_from_param "$ARKIME_CONFIG_INI")
echo "Written to: $config_ini_path"

# Pull configuration from ENV and AWS in order to set up our Arkime install.  The ENV variables come from the Fargate
# Container definition.  We perform some escaping of the our replacement strings for safety.
# See: https://stackoverflow.com/questions/407523/escape-a-string-for-a-sed-replace-pattern
echo "Configuring /opt/arkime/etc/config.ini ..."
ESCAPED_ENDPOINT=$(printf '%s\n' "$OPENSEARCH_ENDPOINT" | sed -e 's/[\/&]/\\&/g')
sed -i'' "s/_OS_ENDPOINT_/$ESCAPED_ENDPOINT/g" /opt/arkime/etc/config.ini

OPENSEARCH_PASS=$(aws secretsmanager get-secret-value --secret-id $OPENSEARCH_SECRET_ARN --output text --query SecretString)
BASE64_AUTH=$(echo -n "admin:$OPENSEARCH_PASS" | base64)
sed -i'' "s/_OS_AUTH_/$BASE64_AUTH/g" /opt/arkime/etc/config.ini

VIEWER_PASS=$(aws secretsmanager get-secret-value --secret-id $VIEWER_PASS_ARN --output text --query SecretString)

sed -i'' "s/_VIEWER_PORT_/$VIEWER_PORT/g" /opt/arkime/etc/config.ini
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
/opt/arkime/bin/node addUser.js $VIEWER_USER $VIEWER_USER $VIEWER_PASS --admin --packetSearch
/opt/arkime/bin/node viewer.js