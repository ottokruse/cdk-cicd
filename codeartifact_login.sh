#!/bin/bash -e

DOMAIN=$1

if [ -z $AWS_REGION ]; then
    export AWS_REGION="us-east-1"
fi

AWS_ACCOUNT_ID="$(aws sts get-caller-identity | jq -r .Account)"

CODEARTIFACT_TOKEN="$(aws codeartifact get-authorization-token --domain ${DOMAIN} | jq -r .authorizationToken)"
REGISTRY_URL="https://aws:${CODEARTIFACT_TOKEN}@${DOMAIN}-${AWS_ACCOUNT_ID}.d.codeartifact.${AWS_REGION}.amazonaws.com/pypi/epr-ml-python/simple/"

cat <<EOF > pip.conf
[global]
index-url = ${REGISTRY_URL}

EOF

echo '# Run this script through eval to execute exports:'
echo '# eval "$(./codeartifact_login.sh)"'
echo 'export PIP_CONFIG_FILE=pip.conf'
echo 'export TWINE_USERNAME=aws'
echo "export TWINE_PASSWORD=\"${CODEARTIFACT_TOKEN}\""
echo "export TWINE_REPOSITORY_URL=\"https://${DOMAIN}-${AWS_ACCOUNT_ID}.d.codeartifact.${AWS_REGION}.amazonaws.com/pypi/epr-ml-python/\""
echo "echo \"pip url  : https://aws:CODEARTIFACT_TOKEN@${DOMAIN}-${AWS_ACCOUNT_ID}.d.codeartifact.${AWS_REGION}.amazonaws.com/pypi/epr-ml-python/simple/\""
echo "echo \"twine url: https://${DOMAIN}-${AWS_ACCOUNT_ID}.d.codeartifact.${AWS_REGION}.amazonaws.com/pypi/epr-ml-python/\""
