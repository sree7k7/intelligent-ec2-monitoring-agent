#!/bin/bash
set -e

UPDATE_ONLY=${1:-false}

echo "🚀 Deploying AgentCore Monitoring Infrastructure..."

# 1. Deploy CDK stack
echo "📦 Step 1: Deploying CDK infrastructure..."
cdk deploy --require-approval never --outputs-file cdk-outputs.json

# 2. Extract role ARN or role name from outputs
ROLE_ARN=$(cat cdk-outputs.json | jq -r '.[].AgentRoleArn // empty')
ROLE_NAME=$(cat cdk-outputs.json | jq -r '.[].AgentRoleOutput // empty')

# If ARN not found, construct it from role name
if [ -z "$ROLE_ARN" ] && [ ! -z "$ROLE_NAME" ]; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
    echo "✓ Constructed role ARN from name: $ROLE_ARN"
elif [ ! -z "$ROLE_ARN" ]; then
    echo "✓ Found role ARN: $ROLE_ARN"
else
    echo "❌ Could not find role ARN or role name in CDK outputs"
    echo "Available outputs:"
    cat cdk-outputs.json | jq
    exit 1
fi

# 3. Configure AgentCore with the role
echo "📋 Step 2: Configuring AgentCore..."
if [ "$UPDATE_ONLY" != "true" ]; then
    echo "📋 Step 2: Configuring AgentCore..."
    agentcore configure --execution-role "$ROLE_ARN"
fi

# 4. Launch agent
echo "🚀 Step 3: Launching AgentCore agent..."
uv run agentcore launch

# 5. Re-deploy to update Lambda with agent_id
echo "🔄 Step 4: Updating Lambda with agent_id..."
cdk deploy --require-approval never

echo "✅ Deployment complete!"
