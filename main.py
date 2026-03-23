"""
Main entry point for the AI DevOps Operations Platform.
Runs all three alarm scenarios sequentially.
"""

import sys
import os

# Add the current directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mock_data import get_alarm, get_alarm_name
from orchestrator import run_investigation
from slack_reporter import post_final_report


# List of scenarios to run
SCENARIOS = ["cpu_spike_alarm", "rds_connection_alarm", "pipeline_failure_alarm"]


def main():
    """
    Run all three alarm scenarios and generate investigation reports.
    """
    print("\n" + "=" * 70)
    print("   AI DEVOPS OPERATIONS PLATFORM - CAPSTONE PROJECT")
    print("=" * 70)
    print("\nMulti-agent system with Lead Orchestrator and 3 sub-agents:")
    print("  - LogAnalyst: Analyzes CloudWatch and application logs")
    print("  - MetricsAnalyst: Analyzes metric baselines and trends")
    print("  - RemediationPlanner: Creates remediation plans")
    print("\n" + "=" * 70)

    for scenario in SCENARIOS:
        alarm_name = get_alarm_name(scenario)
        alarm_json = get_alarm(scenario)

        print(f"\n\n{'#' * 70}")
        print(f"# SCENARIO: {scenario}")
        print(f"# ALARM: {alarm_name}")
        print(f"# {'#' * 70}")

        print(f"\nStarting investigation at: ", end="")
        # Run the investigation
        report = run_investigation(alarm_json)

        # Post final report to Slack
        post_final_report(report, alarm_name)

        # Print summary of sub-agents
        print(f"\n--- Sub-agent Summary ---")
        print(f"Completed: {report.get('sub_agents_completed', [])}")
        if report.get('sub_agents_warnings'):
            print(f"Warnings: {report.get('sub_agents_warnings', [])}")

    print("\n\n" + "=" * 70)
    print("ALL SCENARIOS COMPLETED")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()