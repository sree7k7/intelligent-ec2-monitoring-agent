"""
Automated Monitoring Tool

Checks all EC2 instances for high CPU and sends alerts.
"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from .cloudwatch_tool import get_ec2_cpu_usage
from .sns_tool import publish_sns_alert, format_alert_message

logger = logging.getLogger(__name__)

# In-memory alert state (tracks recent alerts to prevent spam)
alert_state = {}


def check_all_instances_cpu(
    threshold: float = 80.0,
    region: str = "us-east-1",
    topic_arn: str = None,
    cooldown_minutes: int = 15
) -> Dict:
    """
    Check CPU usage for all running EC2 instances and send alerts if needed.
    
    Args:
        threshold: CPU percentage threshold (default: 80.0)
        region: AWS region (default: 'us-east-1')
        topic_arn: SNS topic ARN for alerts
        cooldown_minutes: Minutes to wait before sending duplicate alert (default: 15)
    
    Returns:
        dict: {
            'instances_checked': int,
            'high_cpu_instances': list[dict],
            'alerts_sent': int,
            'alerts_skipped': int,
            'timestamp': str
        }
    """
    try:
        ec2 = boto3.client('ec2', region_name=region)
        
        # Get all running instances
        response = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append(instance)
        
        logger.info(f"Checking {len(instances)} running instances")
        
        high_cpu_instances = []
        alerts_sent = 0
        alerts_skipped = 0
        
        for instance in instances:
            instance_id = instance['InstanceId']
            instance_type = instance['InstanceType']
            
            # Get instance name from tags
            instance_name = instance_id
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Name':
                    instance_name = tag['Value']
                    break
            
            # Get CPU usage
            cpu_data = get_ec2_cpu_usage(instance_id, minutes=5, region=region)
            
            if cpu_data.get('error'):
                logger.warning(f"Skipping {instance_id}: {cpu_data['error']}")
                continue
            
            current_cpu = cpu_data.get('current_cpu')
            if current_cpu is None:
                continue
            
            # Check if CPU exceeds threshold
            if current_cpu > threshold:
                high_cpu_instances.append({
                    'instance_id': instance_id,
                    'instance_name': instance_name,
                    'instance_type': instance_type,
                    'current_cpu': current_cpu,
                    'average_cpu': cpu_data.get('average_cpu'),
                    'max_cpu': cpu_data.get('max_cpu')
                })
                
                # Check if we should send alert (deduplication)
                if should_send_alert(instance_id, cooldown_minutes):
                    # Send alert
                    if topic_arn:
                        subject, message = format_alert_message(
                            instance_id=instance_id,
                            instance_name=instance_name,
                            instance_type=instance_type,
                            current_cpu=current_cpu,
                            average_cpu=cpu_data.get('average_cpu'),
                            max_cpu=cpu_data.get('max_cpu'),
                            threshold=threshold
                        )
                        
                        result = publish_sns_alert(
                            topic_arn=topic_arn,
                            subject=subject,
                            message=message,
                            region=region
                        )
                        
                        if result.get('success'):
                            alerts_sent += 1
                            update_alert_state(instance_id, current_cpu)
                            logger.info(f"Alert sent for {instance_name} ({current_cpu}% CPU)")
                        else:
                            logger.error(f"Failed to send alert for {instance_name}")
                    else:
                        logger.warning("No SNS topic ARN provided, skipping alert")
                else:
                    alerts_skipped += 1
                    logger.info(f"Alert skipped for {instance_name} (cooldown period)")
        
        return {
            'instances_checked': len(instances),
            'high_cpu_instances': high_cpu_instances,
            'alerts_sent': alerts_sent,
            'alerts_skipped': alerts_skipped,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking instances: {e}")
        return {
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


def should_send_alert(instance_id: str, cooldown_minutes: int) -> bool:
    """
    Check if we should send an alert for this instance (deduplication).
    
    Args:
        instance_id: EC2 instance ID
        cooldown_minutes: Minutes to wait before sending duplicate alert
    
    Returns:
        bool: True if alert should be sent, False if in cooldown period
    """
    if instance_id not in alert_state:
        return True
    
    last_alert_time = alert_state[instance_id]['last_alert_time']
    time_since_alert = datetime.utcnow() - last_alert_time
    
    if time_since_alert.total_seconds() / 60 >= cooldown_minutes:
        return True
    
    return False


def update_alert_state(instance_id: str, cpu: float):
    """
    Update alert state after sending an alert.
    
    Args:
        instance_id: EC2 instance ID
        cpu: Current CPU percentage
    """
    alert_state[instance_id] = {
        'last_alert_time': datetime.utcnow(),
        'last_cpu': cpu,
        'alert_count': alert_state.get(instance_id, {}).get('alert_count', 0) + 1
    }


def clear_alert_state(instance_id: str):
    """
    Clear alert state when CPU returns to normal.
    
    Args:
        instance_id: EC2 instance ID
    """
    if instance_id in alert_state:
        del alert_state[instance_id]
        logger.info(f"Alert state cleared for {instance_id}")
