#!/bin/bash

set -e

# Pull configuration from ENV and AWS in order to set up our Arkime install.  The ENV variables come from the Fargate
# Container definition.  We perform some escaping of the our replacement strings for safety.
# See: https://stackoverflow.com/questions/407523/escape-a-string-for-a-sed-replace-pattern
ESCAPED_ENDPOINT=$(printf '%s\n' "$OPENSEARCH_ENDPOINT" | sed -e 's/[\/&]/\\&/g')
sed -i'' "s/_ENDPOINT_/$ESCAPED_ENDPOINT/g" /opt/arkime/etc/config.ini

OPENSEARCH_PASS=$(aws secretsmanager get-secret-value --secret-id $OPENSEARCH_SECRET_ARN --region $AWS_REGION --output text --query SecretString)
ESCAPED_PASS=$(printf '%s\n' "$OPENSEARCH_PASS" | sed -e 's/[\/&]/\\&/g')
sed -i'' "s/_PASSWORD_/$ESCAPED_PASS/g" /opt/arkime/etc/config.ini

# Initialize our OpenSearch Domain for the Arkime data if it hasn't already been initialized.  This code creates a
# a potential race condition among the containers on initial setup, but it's not clear that's actually a problem.
# The init command wipes out the existing Arkime data on the Domain but there's none there when the first set of
# containers all try to do this process at the same time, so I don't think we care if they clobber each other.
IS_INITIALIZED=$(aws ssm get-parameter --name $SSM_INITIALIZED_PARAM --query "Parameter.Value" --output text)
if [[ "$IS_INITIALIZED" = "false" ]]; then
    echo "Running cluster initialization actions..."
    # TODO: I can't get this command to work; it hangs on the initial cluster health check (see db.pl line 301-ish)
    # /opt/arkime/db/db.pl -v -v -v --esuser admin:$OPENSEARCH_PASS https://$OPENSEARCH_ENDPOINT:9200 init
    aws ssm put-parameter --overwrite --name $SSM_INITIALIZED_PARAM --value true
else
    echo "Cluster already initialized, skipping those actions"
fi

# Start Arkime Capture
# TODO: Some command that uses /opt/arkime/bin/capture

sleep 36000
