"""
Configuration for Phase 3 CPU Monitoring Agent

Simple configuration file - edit these values for your environment.
"""

import os

# SNS Configuration
# Create this topic manually in AWS Console before deploying
SNS_TOPIC_ARN = os.getenv(
    'SNS_TOPIC_ARN',
    'arn:aws:sns:us-east-1:123456789012:ops-alerts'  # Replace with your topic ARN
)

# CPU Monitoring Configuration
CPU_THRESHOLD = float(os.getenv('CPU_THRESHOLD', '80.0'))  # Alert when CPU exceeds this %
ALERT_COOLDOWN_MINUTES = int(os.getenv('ALERT_COOLDOWN_MINUTES', '15'))  # Don't spam alerts

# CloudWatch Configuration
CLOUDWATCH_LOOKBACK_MINUTES = int(os.getenv('CLOUDWATCH_LOOKBACK_MINUTES', '5'))  # How far back to check
CLOUDWATCH_METRIC_PERIOD = int(os.getenv('CLOUDWATCH_METRIC_PERIOD', '60'))  # 1-minute granularity

# AWS Region
AWS_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
