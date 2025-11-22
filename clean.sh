#!/bin/bash
set -e

echo "🧹 Cleaning up AgentCore Monitoring Infrastructure..."

# 1. Delete AgentCore agent
echo "📋 Step 1: Deleting AgentCore agent..."
if [ -f .bedrock_agentcore.yaml ]; then
    agentcore destroy --force || echo "⚠️  AgentCore destroy failed or already deleted"
else
    echo "⚠️  No .bedrock_agentcore.yaml found, skipping agent deletion"
fi

# 2. Delete CDK stack
echo "📦 Step 2: Destroying CDK infrastructure..."
cdk destroy --force