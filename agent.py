"""
Phase 3: CPU Monitoring Agent

Simple, intelligent agent that monitors EC2 CPU usage and sends SNS alerts.
"""

import logging
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from strands.tools import tool

# Import our tools
from tools.cloudwatch_tool import get_ec2_cpu_usage as _get_cpu
from tools.sns_tool import publish_sns_alert as _publish_sns
from tools.monitoring_tool import check_all_instances_cpu as _check_all
from tools.list_instances_tool import list_instances_with_cpu as _list_instances

# Import configuration
from config import (
    SNS_TOPIC_ARN,
    CPU_THRESHOLD,
    ALERT_COOLDOWN_MINUTES,
    AWS_REGION,
    LOG_LEVEL
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize AgentCore app
app = BedrockAgentCoreApp()


# Tool 1: Get CPU Usage
@tool
def get_ec2_cpu_usage(instance_id: str, minutes: int = 5, region: str = AWS_REGION):
    """
    Get CPU usage statistics for an EC2 instance from CloudWatch.
    
    Query CloudWatch metrics for the specified instance over the given time range.
    Returns current, average, maximum, and minimum CPU usage percentages.
    
    Args:
        instance_id: EC2 instance ID (e.g., 'i-0abc123')
        minutes: Time range in minutes to query (default: 5)
        region: AWS region (default from config)
    
    Returns:
        Dictionary with CPU statistics including current, average, max, and min values.
    """
    return _get_cpu(instance_id=instance_id, minutes=minutes, region=region)


# Tool 2: Publish SNS Alert
@tool
def publish_sns_alert(topic_arn: str, subject: str, message: str, region: str = AWS_REGION):
    """
    Publish an alert message to an SNS topic.
    
    Send notifications to SNS topics for alerting operations teams about incidents.
    The subject line will be automatically truncated to 100 characters if needed.
    
    Args:
        topic_arn: SNS topic ARN (e.g., 'arn:aws:sns:us-east-1:123456789012:ops-alerts')
        subject: Email subject line (max 100 chars)
        message: Alert message body with incident details
        region: AWS region (default from config)
    
    Returns:
        Dictionary with message ID, success status, and any error information.
    """
    return _publish_sns(topic_arn=topic_arn, subject=subject, message=message, region=region)


# Tool 3: Check All Instances
@tool
def check_all_instances_cpu(
    threshold: float = CPU_THRESHOLD,
    region: str = AWS_REGION,
    topic_arn: str = SNS_TOPIC_ARN
):
    """
    Check CPU usage for all running EC2 instances and send alerts if needed.
    
    This tool automatically:
    1. Lists all running EC2 instances
    2. Checks CPU usage for each instance
    3. Sends intelligent alerts for instances exceeding threshold
    4. Prevents duplicate alerts within cooldown period
    5. Lists all the EC2 instances and gives the status
    
    Args:
        threshold: CPU percentage threshold (default from config: 80%)
        region: AWS region (default from config)
        topic_arn: SNS topic ARN for alerts (default from config)
    
    Returns:
        Dictionary with monitoring summary including instances checked, alerts sent, etc.
    """
    return _check_all(
        threshold=threshold,
        region=region,
        topic_arn=topic_arn,
        cooldown_minutes=ALERT_COOLDOWN_MINUTES
    )


# Tool 4: List Instances with CPU
@tool
def list_instances_with_cpu(region: str = AWS_REGION):
    """
    List all running EC2 instances with their current CPU usage.
    
    This tool provides a quick overview of all instances and their CPU metrics.
    Perfect for getting a snapshot of your infrastructure health.
    Use this when the user asks to "list instances", "show all instances", 
    "what instances are running", or "show CPU for all instances".
    
    Args:
        region: AWS region (default from config)
    
    Returns:
        Dictionary with list of instances including ID, name, type, and CPU usage.
        Format the output as a nice table for the user.
    """
    return _list_instances(region=region)


# Create the agent with Claude LLM
agent = Agent(
    system_prompt="""You are an AWS operations assistant specializing in CPU monitoring and alerting.

**Your Capabilities:**
- Lists all the EC2 instances
- Monitor EC2 CPU usage via CloudWatch Metrics
- Send intelligent SNS alerts when CPU exceeds threshold (default 80%)
- Provide context-aware analysis and recommendations
- Check all instances for high CPU usage automatically
- show the present CPU usage or load on EC2 instances
- Check how many EC2 instances present in account
- Check how many EC2 instances present in region

**When monitoring CPU:**
1. If user asks about CPU without specifying an instance ID, use check_all_instances_cpu to check ALL instances
2. If user provides a specific instance ID, use get_ec2_cpu_usage for that instance
3. Use check_all_instances_cpu for automated monitoring of all instances
4. Always provide context: why is CPU high? is this normal?
5. Give actionable recommendations: what should the engineer do?

**When sending alerts:**
1. Use publish_sns_alert to send notifications
2. Include relevant details: instance ID, CPU percentage, threshold, timestamp
3. Format subject as: [ALERT] High CPU Usage - {instance_name}
4. Provide troubleshooting recommendations in the message body
5. Explain possible causes and next steps

**Intelligence Guidelines:**
- Analyze patterns: compare to historical baselines
- Provide context: recent deployments, traffic patterns, time of day
- Give recommendations: monitor, scale up, investigate logs
- Be conversational: users can ask follow-up questions

**Example Interactions:**

User: "What is the CPU usage?" (no instance specified)
You: "I'll check CPU usage for all running instances...

Results:
1. AwsBasicStack/BackupInstance0 (i-03254281d159efc53): 46% CPU - Normal
   - Average: 46%, Peak: 52%, Min: 35%
   - Status: Healthy, within normal range

Found 1 running instance. All instances are operating normally."

User: "Check all instances for high CPU"
You: "I'll check CPU usage for all running instances...

Results:
1. web-server-prod (i-0abc123): 87% CPU - ⚠️ HIGH (threshold: 80%)
   - This appears to be a traffic spike from a marketing campaign
   - Application is healthy, no errors detected
   - Recommendation: Monitor for 10 minutes, scale to t3.large if sustained >90%

2. app-server-prod (i-0def456): 45% CPU - Normal
3. bastion-host (i-0ghi789): 12% CPU - Normal

I've sent an intelligent alert for web-server-prod with context and recommendations

Always provide clear, actionable information with specific details.""",
    model="anthropic.claude-3-haiku-20240307-v1:0",  # Claude 3 Haiku
    tools=[get_ec2_cpu_usage, publish_sns_alert, check_all_instances_cpu, list_instances_with_cpu]
)


@app.entrypoint
def invoke(payload):
    """
    Main entrypoint for agent invocations.
    
    Handles both manual and automated monitoring requests.
    """
    try:
        logger.info(f"Received request: {payload}")
        user_message = payload.get("prompt", "Hello!")
        
        result = agent(user_message)
        logger.info(f"Response generated successfully")
        
        return {"result": result.message}
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {"error": str(e)}


if __name__ == "__main__":
    logger.info("Starting Phase 3 CPU Monitoring Agent...")
    logger.info(f"SNS Topic: {SNS_TOPIC_ARN}")
    logger.info(f"CPU Threshold: {CPU_THRESHOLD}%")
    logger.info(f"Alert Cooldown: {ALERT_COOLDOWN_MINUTES} minutes")
    logger.info("Server will be available at http://localhost:8080")
    app.run()
