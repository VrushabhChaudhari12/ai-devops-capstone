"""
Mock CloudWatch alarm data for the AI DevOps Operations Platform.
Three alarm scenarios simulating real CloudWatch alarms.
"""

import json
from datetime import datetime

# Base timestamp for generating realistic timestamps
BASE_TIME = datetime(2024, 3, 15, 14, 30, 0)


def get_alarm(scenario: str) -> str:
    """
    Get the CloudWatch alarm as a formatted JSON string.

    Args:
        scenario: The alarm scenario name ('cpu_spike_alarm', 'rds_connection_alarm', 'pipeline_failure_alarm')

    Returns:
        Alarm as formatted JSON string
    """
    alarms = {
        "cpu_spike_alarm": {
            "alarm_name": "HighCPU utilization on production instance",
            "metric_name": "CPUUtilization",
            "threshold": 90,
            "current_value": 96,
            "instance_id": "i-0abc1234567890def",
            "region": "ap-south-1",
            "timestamp": BASE_TIME.isoformat(),
            "alarm_state": "ALARM",
            "namespace": "AWS/EC2",
            "statistic": "Average",
            "period": 300,
            "evaluation_periods": 2,
            "comparison_operator": "GreaterThanThreshold"
        },
        "rds_connection_alarm": {
            "alarm_name": "RDS connection threshold exceeded",
            "metric_name": "DatabaseConnections",
            "threshold": 95,
            "current_value": 100,
            "db_instance_id": "prod-db-01",
            "region": "us-east-1",
            "timestamp": BASE_TIME.isoformat(),
            "alarm_state": "ALARM",
            "namespace": "AWS/RDS",
            "statistic": "Maximum",
            "period": 300,
            "evaluation_periods": 1,
            "comparison_operator": "GreaterThanThreshold"
        },
        "pipeline_failure_alarm": {
            "alarm_name": "CodePipeline build failure alert",
            "metric_name": "FailedBuilds",
            "threshold": 0,
            "current_value": 1,
            "project_name": "payment-service",
            "build_id": "build-12345",
            "phase": "BUILD",
            "region": "us-east-1",
            "timestamp": BASE_TIME.isoformat(),
            "alarm_state": "ALARM",
            "namespace": "AWS/CodePipeline",
            "statistic": "Sum",
            "period": 60,
            "evaluation_periods": 1,
            "comparison_operator": "GreaterThanThreshold"
        }
    }

    alarm = alarms.get(scenario, {})
    return json.dumps(alarm, indent=2)


def get_alarm_name(scenario: str) -> str:
    """
    Get just the alarm name for a scenario.

    Args:
        scenario: The alarm scenario name

    Returns:
        Alarm name string
    """
    alarms = {
        "cpu_spike_alarm": "HighCPU utilization on production instance",
        "rds_connection_alarm": "RDS connection threshold exceeded",
        "pipeline_failure_alarm": "CodePipeline build failure alert"
    }
    return alarms.get(scenario, "Unknown Alarm")