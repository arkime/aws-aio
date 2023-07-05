#!/bin/bash

set -e

echo "============================================================"
echo "Cluster: $CLUSTER_NAME"
echo "Role: Capture Node"
echo "Arkime Config INI Datastore Location: $ARKIME_CONFIG_INI_LOC"
echo "Arkime Additional File Datastore Locations: $ARKIME_ADD_FILE_LOCS"
echo "AWS Region: $AWS_REGION"
echo "Bucket Name: $BUCKET_NAME"
echo "LB Healthcheck Port: $LB_HEALTH_PORT"
echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
echo "OpenSearch Secret Arn: $OPENSEARCH_SECRET_ARN"
echo "S3 Storage Class: $S3_STORAGE_CLASS"
echo "============================================================"

# Pull our configuration files from the cloud
function write_file_from_datastore() {
    datastore_location=$1

    # Retrieve our file from the cloud and account for wacky escaping
    param_val=$(aws ssm get-parameter --name "$datastore_location" --query Parameter.Value)
    corrected_string=$(echo "$param_val" | sed 's/\\\"/\"/g' | sed 's/\\\\/\\/g') # Remove extra escaping
    corrected_string=$(echo "$corrected_string" | sed 's/^"//' | sed 's/"$//') # Remove starting/ending quotes

    # Pull out the values we need
    system_path=$(echo "$corrected_string" | jq -r '.system_path')
    echo "System Path: $system_path" >&2
    contents=$(echo "$corrected_string" | jq -r '.contents')

    # Write the file to disk
    echo -e "$contents" > "$system_path"

    # Return the path to the calling context
    echo "$system_path"
}

echo "$ARKIME_ADD_FILE_LOCS" | jq -r '.[]' | while IFS= read -r path; do
    echo "Processing File in Datastore: $path"
    full_file_path=$(write_file_from_datastore "$path")
    echo "Written to: $full_file_path"
done

echo "Processing config.ini in Datastore: $ARKIME_CONFIG_INI_LOC"
config_ini_path=$(write_file_from_datastore "$ARKIME_CONFIG_INI_LOC")
echo "Written to: $config_ini_path"

# Pull configuration from ENV and AWS in order to set up our Arkime install.  The ENV variables come from the Fargate
# Container definition.  We perform some escaping of the our replacement strings for safety.
# See: https://stackoverflow.com/questions/407523/escape-a-string-for-a-sed-replace-pattern
echo "Configuring $config_ini_path ..."
ESCAPED_ENDPOINT=$(printf '%s\n' "$OPENSEARCH_ENDPOINT" | sed -e 's/[\/&]/\\&/g')
sed -i'' "s/_OS_ENDPOINT_/$ESCAPED_ENDPOINT/g" "$config_ini_path"

OPENSEARCH_PASS=$(aws secretsmanager get-secret-value --secret-id $OPENSEARCH_SECRET_ARN --output text --query SecretString)
BASE64_AUTH=$(echo -n "admin:$OPENSEARCH_PASS" | base64)
sed -i'' "s/_OS_AUTH_/$BASE64_AUTH/g" "$config_ini_path"

sed -i'' "s/_PCAP_BUCKET_/$BUCKET_NAME/g" "$config_ini_path"
sed -i'' "s/_HEALTH_PORT_/$LB_HEALTH_PORT/g" "$config_ini_path"
sed -i'' "s/_AWS_REGION_/$AWS_REGION/g" "$config_ini_path"
echo "Successfully configured $config_ini_path"

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
/opt/arkime/bin/capture --config "$config_ini_path"
