
# config.py
AGENT_ROLE_NAME = "AgentRole"
SNS_TOPIC_NAME = "AgentNotificationTopic"
LAMBDA_FUNCTION_NAME = "AgentInvocationFunction"
EVENT_RULE_NAME = "AgentScheduleRule"

# cdk_stack.py
from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_sns as sns,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as targets,
    Duration
)
from constructs import Construct
from config import *

import yaml
from pathlib import Path

# Try to load agent_id from config
agent_id = "NOT_FOUND"
config_path = Path(__file__).parent.parent / '.bedrock_agentcore.yaml'

if config_path.exists():
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        default_agent = config.get('default_agent', 'cpu')
        agent_config = config.get('agents', {}).get(default_agent, {})
        bedrock_config = agent_config.get('bedrock_agentcore', {})
        agent_id = bedrock_config.get('agent_id', 'NOT_FOUND')
        agent_arn = bedrock_config.get('agent_arn', 'NOT_FOUND')
        
        print(f"✓ Found agent_id: {agent_id}")
        print(f"✓ Found agent_arn: {agent_arn}")
    except Exception as e:
        print(f"⚠️  Could not read agent_id: {e}")
        agent_id = "NOT_FOUND"
else:
    print("⚠️  .bedrock_agentcore.yaml not found, using placeholder")


class AgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create IAM role for agent
        agent_role = iam.Role(
            self,
            AGENT_ROLE_NAME,
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
                iam.ServicePrincipal("bedrock.amazonaws.com"),
                iam.ServicePrincipal("bedrock-agentcore.amazonaws.com")
            ),
            role_name=AGENT_ROLE_NAME
        )

        agent_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
        )
        agent_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2FullAccess")
        )
        agent_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchReadOnlyAccess")
        )

        # Add basic Lambda execution policy
        agent_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )

        # Create SNS Topic
        topic = sns.Topic(
            self,
            "AgentTopic",
            topic_name=SNS_TOPIC_NAME
        )

        # Note: Subscribe to this topic manually via AWS Console or CLI
        # to avoid resubscription emails on every deployment
        # Command: aws sns subscribe --topic-arn <topic-arn> --protocol email --notification-endpoint sreefriend7k7@gmail.com

        # Create Lambda function
        agent_lambda = lambda_.Function(
            self,
            "AgentLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="agent_trigger.lambda_handler",
            code=lambda_.Code.from_asset("lambda"),
            role=agent_role,
            function_name=LAMBDA_FUNCTION_NAME,
            timeout=Duration.minutes(5),
            environment={
            'SNS_TOPIC_ARN': topic.topic_arn,
            'CPU_THRESHOLD': '80.0'
        }
        )

        # Create EventBridge rule to trigger Lambda every 5 minutes
        rule = events.Rule(
            self,
            "AgentScheduleRule",
            rule_name=EVENT_RULE_NAME,
            schedule=events.Schedule.rate(Duration.minutes(5))
        )

        # Add Lambda as target for the EventBridge rule
        rule.add_target(targets.LambdaFunction(
            agent_lambda,
            event=events.RuleTargetInput.from_object({"prompt": "Check all instances for high CPU and send alerts if needed"})
            )
            )

        # Grant Lambda permission to publish to SNS
        topic.grant_publish(agent_lambda)

        # Output the role name
        from aws_cdk import CfnOutput
        CfnOutput(
            self,
            "AgentRoleOutput",
            value=agent_role.role_name,
            description="Agent Execution Role Name"
        )
        CfnOutput(
            self,
            "AgentId",
            value=agent_id if agent_id else "NOT_FOUND",
            description="AgentCore Agent ID"
        )