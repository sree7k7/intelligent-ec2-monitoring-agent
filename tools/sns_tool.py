"""
SNS Alert Tool

Sends alert notifications to SNS topics.
"""

import boto3
from datetime import datetime
from typing import Dict
import logging

logger = logging.getLogger(__name__)


def publish_sns_alert(
    topic_arn: str,
    subject: str,
    message: str,
    region: str = "us-east-1"
) -> Dict:
    """
    Publish an alert message to an SNS topic.
    
    Args:
        topic_arn: SNS topic ARN (e.g., 'arn:aws:sns:us-east-1:123456789012:ops-alerts')
        subject: Email subject line (max 100 chars)
        message: Alert message body
        region: AWS region (default: 'us-east-1')
    
    Returns:
        dict: {
            'message_id': str,
            'topic_arn': str,
            'success': bool,
            'timestamp': str
        }
    """
    try:
        sns = boto3.client('sns', region_name=region)
        
        # Truncate subject to SNS limit (100 characters)
        if len(subject) > 100:
            subject = subject[:97] + "..."
            logger.warning(f"Subject truncated to 100 characters")
        
        # Publish to SNS
        response = sns.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
        
        message_id = response.get('MessageId')
        logger.info(f"Alert sent successfully. Message ID: {message_id}")
        
        return {
            'message_id': message_id,
            'topic_arn': topic_arn,
            'success': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error publishing to SNS: {e}")
        return {
            'topic_arn': topic_arn,
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


def format_alert_message(
    instance_id: str,
    instance_name: str,
    instance_type: str,
    current_cpu: float,
    average_cpu: float,
    max_cpu: float,
    threshold: float
) -> tuple[str, str]:
    """
    Format an intelligent alert message.
    
    Returns:
        tuple: (subject, message)
    """
    subject = f"[ALERT] High CPU Usage - {instance_name}"
    
    message = f"""Instance: {instance_name} ({instance_id})
Instance Type: {instance_type}
Current CPU: {current_cpu}%
Threshold: {threshold}%
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

Details:
- Average CPU (last 5 min): {average_cpu}%
- Peak CPU (last 5 min): {max_cpu}%

Action Required: Investigate high CPU usage.

Possible causes:
- High application load
- Runaway process
- Insufficient instance size

Next steps:
1. Check application logs
2. Review running processes
3. Consider scaling up instance size
"""
    
    return subject, message
