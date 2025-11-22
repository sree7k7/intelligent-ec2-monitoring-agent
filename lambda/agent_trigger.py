import json
import boto3
import os

# Get configuration from environment variables
REGION = os.environ.get('AWS_REGION', 'us-east-1')
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']  # Provided by CDK
CPU_THRESHOLD = float(os.environ.get('CPU_THRESHOLD', '80.0'))

# Initialize AWS clients
ec2 = boto3.client('ec2', region_name=REGION)
cloudwatch = boto3.client('cloudwatch', region_name=REGION)
sns = boto3.client('sns', region_name=REGION)


def get_running_instances():
    """Get all running EC2 instances"""
    response = ec2.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )
    
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            name = 'Unknown'
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
                    break
            
            instances.append({
                'id': instance['InstanceId'],
                'name': name,
                'type': instance['InstanceType']
            })
    
    return instances


def get_cpu_usage(instance_id):
    """Get current CPU usage for an instance"""
    from datetime import datetime, timedelta
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=5)
    
    response = cloudwatch.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=300,
        Statistics=['Average', 'Maximum']
    )
    
    if response['Datapoints']:
        datapoint = sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)[0]
        return {
            'average': round(datapoint['Average'], 2),
            'maximum': round(datapoint['Maximum'], 2)
        }
    
    return {'average': 0, 'maximum': 0}


def send_alert(instance_id, instance_name, cpu_usage):
    """Send SNS alert for high CPU"""
    from datetime import datetime
    
    subject = f"[ALERT] High CPU on {instance_name}"
    message = f"""High CPU Usage Detected!

Instance: {instance_name} ({instance_id})
Current CPU: {cpu_usage['average']}% (Peak: {cpu_usage['maximum']}%)
Threshold: {CPU_THRESHOLD}%

This instance has exceeded the CPU threshold and may need attention.

Recommendations:
- Check application logs for errors
- Review recent deployments
- Consider scaling up if sustained high usage
- Investigate any unusual processes

Time: {datetime.utcnow().isoformat()}Z
"""
    
    try:
        response = sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject[:100],  # SNS subject limit
            Message=message
        )
        print(f"✓ Alert sent for {instance_name}: MessageId={response['MessageId']}")
        return True
    except Exception as e:
        print(f"✗ Failed to send alert for {instance_name}: {e}")
        return False


def lambda_handler(event, context):
    """
    Lambda handler triggered by EventBridge.
    Checks all EC2 instances for high CPU and sends alerts.
    """
    
    print(f"Starting CPU monitoring check (threshold: {CPU_THRESHOLD}%)")
    
    try:
        # Get all running instances
        instances = get_running_instances()
        print(f"Found {len(instances)} running instances")
        
        if not instances:
            print("No running instances found")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No running instances to monitor'})
            }
        
        # Check each instance
        alerts_sent = 0
        high_cpu_instances = []
        
        for instance in instances:
            cpu = get_cpu_usage(instance['id'])
            print(f"{instance['name']} ({instance['id']}): {cpu['average']}% CPU")
            
            if cpu['average'] >= CPU_THRESHOLD:
                high_cpu_instances.append({
                    'instance': instance,
                    'cpu': cpu
                })
                
                # Send alert
                if send_alert(instance['id'], instance['name'], cpu):
                    alerts_sent += 1
        
        # Summary
        summary = {
            'instances_checked': len(instances),
            'high_cpu_count': len(high_cpu_instances),
            'alerts_sent': alerts_sent,
            'threshold': CPU_THRESHOLD,
            'high_cpu_instances': [
                f"{i['instance']['name']}: {i['cpu']['average']}%" 
                for i in high_cpu_instances
            ]
        }
        
        print(f"✓ Monitoring complete: {summary}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(summary)
        }
    
    except Exception as e:
        error_msg = f"Error during monitoring: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }
