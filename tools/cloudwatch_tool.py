"""
CloudWatch Metrics Tool

Gets CPU usage statistics for EC2 instances from CloudWatch.
"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def get_ec2_cpu_usage(
    instance_id: str,
    minutes: int = 5,
    region: str = "us-east-1"
) -> Dict:
    """
    Get CPU usage statistics for an EC2 instance from CloudWatch.
    
    Args:
        instance_id: EC2 instance ID (e.g., 'i-0abc123')
        minutes: Time range in minutes to query (default: 5)
        region: AWS region (default: 'us-east-1')
    
    Returns:
        dict: {
            'instance_id': str,
            'current_cpu': float,  # Most recent datapoint
            'average_cpu': float,  # Average over time range
            'max_cpu': float,      # Peak over time range
            'min_cpu': float,      # Minimum over time range
            'datapoints': int,     # Number of datapoints
            'timestamp': str       # ISO 8601 timestamp
        }
    """
    try:
        cloudwatch = boto3.client('cloudwatch', region_name=region)
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes)
        
        # Query CloudWatch metrics
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[
                {'Name': 'InstanceId', 'Value': instance_id}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=60,  # 1-minute granularity
            Statistics=['Average', 'Maximum', 'Minimum']
        )
        
        datapoints = response.get('Datapoints', [])
        
        if not datapoints:
            logger.warning(f"No CPU data available for instance {instance_id}")
            return {
                'instance_id': instance_id,
                'current_cpu': None,
                'average_cpu': None,
                'max_cpu': None,
                'min_cpu': None,
                'datapoints': 0,
                'timestamp': datetime.utcnow().isoformat(),
                'error': 'No data available'
            }
        
        # Sort by timestamp to get most recent
        datapoints.sort(key=lambda x: x['Timestamp'], reverse=True)
        
        # Calculate statistics
        current_cpu = datapoints[0]['Average']
        average_cpu = sum(d['Average'] for d in datapoints) / len(datapoints)
        max_cpu = max(d['Maximum'] for d in datapoints)
        min_cpu = min(d['Minimum'] for d in datapoints)
        
        return {
            'instance_id': instance_id,
            'current_cpu': round(current_cpu, 2),
            'average_cpu': round(average_cpu, 2),
            'max_cpu': round(max_cpu, 2),
            'min_cpu': round(min_cpu, 2),
            'datapoints': len(datapoints),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting CPU usage for {instance_id}: {e}")
        return {
            'instance_id': instance_id,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
