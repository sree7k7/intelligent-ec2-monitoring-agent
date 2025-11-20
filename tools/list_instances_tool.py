"""
List Instances Tool

Lists all EC2 instances with their CPU usage in a structured format.
"""

import boto3
from typing import Dict, List
import logging
from .cloudwatch_tool import get_ec2_cpu_usage

logger = logging.getLogger(__name__)


def list_instances_with_cpu(region: str = "us-east-1") -> Dict:
    """
    List all running EC2 instances with their current CPU usage.
    
    Args:
        region: AWS region (default: 'us-east-1')
    
    Returns:
        dict: {
            'instances': [
                {
                    'instance_id': str,
                    'instance_name': str,
                    'instance_type': str,
                    'state': str,
                    'current_cpu': float,
                    'average_cpu': float
                }
            ],
            'total_instances': int,
            'region': str
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
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                state = instance['State']['Name']
                
                # Get instance name from tags
                instance_name = instance_id
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
                
                # Get CPU usage
                cpu_data = get_ec2_cpu_usage(instance_id, minutes=5, region=region)
                
                instances.append({
                    'instance_id': instance_id,
                    'instance_name': instance_name,
                    'instance_type': instance_type,
                    'state': state,
                    'current_cpu': cpu_data.get('current_cpu'),
                    'average_cpu': cpu_data.get('average_cpu'),
                    'max_cpu': cpu_data.get('max_cpu'),
                    'min_cpu': cpu_data.get('min_cpu')
                })
        
        return {
            'instances': instances,
            'total_instances': len(instances),
            'region': region
        }
        
    except Exception as e:
        logger.error(f"Error listing instances: {e}")
        return {
            'error': str(e),
            'instances': [],
            'total_instances': 0
        }


def format_instances_table(instances_data: Dict) -> str:
    """
    Format instances data as a nice table.
    
    Args:
        instances_data: Output from list_instances_with_cpu()
    
    Returns:
        str: Formatted table
    """
    instances = instances_data.get('instances', [])
    
    if not instances:
        return "No running instances found."
    
    # Build table
    table = []
    table.append("┌─────────────────────┬──────────────────────────────┬──────────────┬─────────────┐")
    table.append("│ Instance ID         │ Name                         │ Type         │ CPU Usage   │")
    table.append("├─────────────────────┼──────────────────────────────┼──────────────┼─────────────┤")
    
    for inst in instances:
        instance_id = inst['instance_id'][:19].ljust(19)
        name = inst['instance_name'][:28].ljust(28)
        inst_type = inst['instance_type'][:12].ljust(12)
        
        cpu = inst.get('current_cpu')
        if cpu is not None:
            cpu_str = f"{cpu:>5.1f}%".ljust(11)
        else:
            cpu_str = "N/A".ljust(11)
        
        table.append(f"│ {instance_id} │ {name} │ {inst_type} │ {cpu_str} │")
    
    table.append("└─────────────────────┴──────────────────────────────┴──────────────┴─────────────┘")
    
    return "\n".join(table)
