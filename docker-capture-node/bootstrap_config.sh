#!/bin/bash

echo "Retrieving config details from SSM Parameter $CAPTURE_CONFIG_SSM_PARAM"
param_value=$(aws ssm get-parameter --name "$CAPTURE_CONFIG_SSM_PARAM" --query Parameter.Value)

echo "Raw config details from SSM: $param_value"

no_begin_end_quotes=$(echo "$param_value" | sed 's/^"//' | sed 's/"$//')
no_quote_escapes=$(echo "$no_begin_end_quotes" | sed 's/\\\"/\"/g')

s3_bucket=$(echo "$no_quote_escapes" | jq -r '.s3.bucket')
s3_key=$(echo "$no_quote_escapes" | jq -r '.s3.key')
s3_path="s3://$s3_bucket/$s3_key"

echo "Setting up temp directory for the config"
config_dir=/arkime_config
config_path="$config_dir/archive.zip"
rm -rf $config_dir
mkdir $config_dir

echo "Retrieving configuration archive from $s3_path and writing to $config_path"
aws s3 cp $s3_path $config_path

echo "Unpacking the archive..."
unzip $config_path -d $config_dir

mv "$config_dir/initialize_arkime.sh" /initialize_arkime.sh
