"""
Lead Orchestrator for the AI DevOps Operations Platform.
Coordinates sub-agents and manages overall investigation flow.
"""

import time
from typing import Dict, Any
from sub_agents import run_log_analyst, run_metrics_analyst, run_remediation_planner

# Orchestrator constants
ORCHESTRATOR_TIMEOUT = 300  # 5 minutes total


def run_investigation(alarm_json: str) -> Dict[str, Any]:
    """
    Run the full investigation by coordinating sub-agents.

    Args:
        alarm_json: The CloudWatch alarm as JSON string

    Returns:
        Final report with all sub-agent results and timing
    """
    print("\n" + "=" * 60)
    print("LEAD ORCHESTRATOR - Starting Investigation")
    print("=" * 60)

    start_time = time.time()
    report = {
        "status": "COMPLETE",
        "log_analysis": None,
        "metrics_analysis": None,
        "remediation_plan": None,
        "total_time_seconds": 0,
        "sub_agents_completed": [],
        "sub_agents_warnings": []
    }

    # Step 1: Run Log Analyst
    print("\n>>> Step 1/3: Running Log Analyst...")
    log_result = run_log_analyst(alarm_json)
    report["log_analysis"] = log_result

    # Check if log result has warning
    if log_result.get("status") == "WARNING":
        report["sub_agents_warnings"].append("LogAnalyst")
        print(f"[WARNING] LogAnalyst failed: {log_result.get('reason')}")
    else:
        report["sub_agents_completed"].append("LogAnalyst")
        print(f"Log Analyst result: {log_result}")

    # Step 2: Check orchestrator timeout after log analysis
    elapsed = time.time() - start_time
    print(f"\n[Orchestrator] Time elapsed: {elapsed:.1f}s")
    if elapsed > ORCHESTRATOR_TIMEOUT:
        print(f"[Orchestrator] TIMEOUT after {elapsed:.1f}s - aborting")
        report["status"] = "TIMEOUT"
        report["total_time_seconds"] = elapsed
        return report

    # Step 3: Run Metrics Analyst
    print("\n>>> Step 2/3: Running Metrics Analyst...")
    metrics_result = run_metrics_analyst(alarm_json)
    report["metrics_analysis"] = metrics_result

    # Check if metrics result has warning
    if metrics_result.get("status") == "WARNING":
        report["sub_agents_warnings"].append("MetricsAnalyst")
        print(f"[WARNING] MetricsAnalyst failed: {metrics_result.get('reason')}")
    else:
        report["sub_agents_completed"].append("MetricsAnalyst")
        print(f"Metrics Analyst result: {metrics_result}")

    # Step 4: Check orchestrator timeout after metrics analysis
    elapsed = time.time() - start_time
    print(f"\n[Orchestrator] Time elapsed: {elapsed:.1f}s")
    if elapsed > ORCHESTRATOR_TIMEOUT:
        print(f"[Orchestrator] TIMEOUT after {elapsed:.1f}s - aborting")
        report["status"] = "TIMEOUT"
        report["total_time_seconds"] = elapsed
        return report

    # Step 5: Run Remediation Planner with all context
    print("\n>>> Step 3/3: Running Remediation Planner...")
    remediation_result = run_remediation_planner(alarm_json, log_result, metrics_result)
    report["remediation_plan"] = remediation_result

    # Check if remediation result has warning
    if remediation_result.get("status") == "WARNING":
        report["sub_agents_warnings"].append("RemediationPlanner")
        print(f"[WARNING] RemediationPlanner failed: {remediation_result.get('reason')}")
    else:
        report["sub_agents_completed"].append("RemediationPlanner")
        print(f"Remediation Planner result: {remediation_result}")

    # Step 6: Calculate total time and finalize report
    elapsed = time.time() - start_time
    report["total_time_seconds"] = elapsed

    print("\n" + "=" * 60)
    print(f"INVESTIGATION COMPLETE - Total time: {elapsed:.1f}s")
    print("=" * 60)
    print(f"Sub-agents completed: {report['sub_agents_completed']}")
    if report['sub_agents_warnings']:
        print(f"Sub-agents with warnings: {report['sub_agents_warnings']}")

    return report