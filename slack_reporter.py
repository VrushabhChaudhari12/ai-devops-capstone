"""
Slack reporter for posting final investigation reports.
"""

from typing import Dict


def post_final_report(report: Dict, alarm_name: str) -> None:
    """
    Print formatted Slack-style investigation report.

    Args:
        report: The investigation report from orchestrator
        alarm_name: The name of the alarm that triggered the investigation
    """
    print("\n" + "=" * 70)
    print("                    SLACK INVESTIGATION REPORT")
    print("=" * 70)

    # Warning banner if any sub-agent had issues
    if report.get("sub_agents_warnings"):
        print("\n" + "!" * 70)
        print("  WARNING: Partial investigation results  ")
        print(f"  Affected sub-agents: {', '.join(report['sub_agents_warnings'])}")
        print("!" * 70)

    # INCIDENT SUMMARY section
    print("\n[INCIDENT SUMMARY]")
    print("-" * 70)
    print(f"*Alarm Name:* {alarm_name}")
    print(f"*Status:* {report.get('status', 'UNKNOWN')}")
    print(f"*Total Investigation Time:* {report.get('total_time_seconds', 0):.1f}s")
    print(f"*Sub-agents Completed:* {', '.join(report.get('sub_agents_completed', [])) or 'None'}")

    # LOG ANALYSIS section
    print("\n[LOG ANALYSIS]")
    print("-" * 70)
    log_analysis = report.get("log_analysis", {})
    if log_analysis.get("status") == "WARNING":
        print(f"[!] Log Analysis: FAILED - {log_analysis.get('reason')}")
    else:
        print(f"*Log Source:* {log_analysis.get('log_source', 'N/A')}")
        print(f"*Errors Found:* {log_analysis.get('errors_found', 'N/A')}")
        print(f"*First Error Time:* {log_analysis.get('first_error_time', 'N/A')}")
        print(f"*Error Pattern:* {log_analysis.get('error_pattern', 'N/A')}")

    # METRICS ANALYSIS section
    print("\n[METRICS ANALYSIS]")
    print("-" * 70)
    metrics_analysis = report.get("metrics_analysis", {})
    if metrics_analysis.get("status") == "WARNING":
        print(f"[!] Metrics Analysis: FAILED - {metrics_analysis.get('reason')}")
    else:
        print(f"*Metric Name:* {metrics_analysis.get('metric_name', 'N/A')}")
        print(f"*Current Value:* {metrics_analysis.get('current_value', 'N/A')}")
        print(f"*Baseline:* {metrics_analysis.get('baseline', 'N/A')}")
        print(f"*Trend:* {metrics_analysis.get('trend', 'N/A')}")
        print(f"*Anomaly Type:* {metrics_analysis.get('anomaly_type', 'N/A')}")

    # REMEDIATION PLAN section
    print("\n[REMEDIATION PLAN]")
    print("-" * 70)
    remediation = report.get("remediation_plan", {})
    if remediation.get("status") == "WARNING":
        print(f"[!] Remediation Planning: FAILED - {remediation.get('reason')}")
    else:
        print(f"*Severity:* {remediation.get('severity', 'N/A')}")
        print(f"*Root Cause:* {remediation.get('root_cause', 'N/A')}")
        print(f"*Immediate Action:* {remediation.get('immediate_action', 'N/A')}")
        print(f"*Long-term Fix:* {remediation.get('long_term_fix', 'N/A')}")
        print(f"*Safe to Automate:* {remediation.get('safe_to_automate', 'N/A')}")

    print("\n" + "=" * 70)
    print(f"Investigation completed in {report.get('total_time_seconds', 0):.1f} seconds")
    print("=" * 70)