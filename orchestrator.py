"""
Lead Orchestrator for the AI DevOps Operations Platform.
Coordinates sub-agents and manages overall investigation flow.
"""
import logging
import time
from typing import Any, Dict

from sub_agents import run_log_analyst, run_metrics_analyst, run_remediation_planner
import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("orchestrator")


def run_investigation(alarm_json: str) -> Dict[str, Any]:
    """
    Run the full investigation by coordinating all three sub-agents sequentially.
    Respects ORCHESTRATOR_TIMEOUT from config and short-circuits on timeout.

    Args:
        alarm_json: The CloudWatch alarm as JSON string

    Returns:
        Final report dict with sub-agent results, timing, and status.
    """
    logger.info("LEAD ORCHESTRATOR - Starting Investigation")
    start_time = time.time()

    report: Dict[str, Any] = {
        "status": "COMPLETE",
        "log_analysis": None,
        "metrics_analysis": None,
        "remediation_plan": None,
        "total_time_seconds": 0,
        "sub_agents_completed": [],
        "sub_agents_warnings": [],
    }

    def _elapsed() -> float:
        return time.time() - start_time

    def _timed_out() -> bool:
        if _elapsed() > config.ORCHESTRATOR_TIMEOUT:
            logger.error("Orchestrator TIMEOUT after %.1fs", _elapsed())
            report["status"] = "TIMEOUT"
            report["total_time_seconds"] = _elapsed()
            return True
        return False

    # Step 1: Log Analyst
    logger.info("Step 1/3: Running Log Analyst...")
    log_result = run_log_analyst(alarm_json)
    report["log_analysis"] = log_result
    if log_result.get("status") == "WARNING":
        report["sub_agents_warnings"].append("LogAnalyst")
        logger.warning("LogAnalyst returned WARNING: %s", log_result.get("reason"))
    else:
        report["sub_agents_completed"].append("LogAnalyst")
        logger.info("LogAnalyst result: %s", log_result)

    if _timed_out():
        return report

    # Step 2: Metrics Analyst
    logger.info("Step 2/3: Running Metrics Analyst...")
    metrics_result = run_metrics_analyst(alarm_json)
    report["metrics_analysis"] = metrics_result
    if metrics_result.get("status") == "WARNING":
        report["sub_agents_warnings"].append("MetricsAnalyst")
        logger.warning("MetricsAnalyst returned WARNING: %s", metrics_result.get("reason"))
    else:
        report["sub_agents_completed"].append("MetricsAnalyst")
        logger.info("MetricsAnalyst result: %s", metrics_result)

    if _timed_out():
        return report

    # Step 3: Remediation Planner
    logger.info("Step 3/3: Running Remediation Planner...")
    remediation_result = run_remediation_planner(alarm_json, log_result, metrics_result)
    report["remediation_plan"] = remediation_result
    if remediation_result.get("status") == "WARNING":
        report["sub_agents_warnings"].append("RemediationPlanner")
        logger.warning("RemediationPlanner returned WARNING: %s", remediation_result.get("reason"))
    else:
        report["sub_agents_completed"].append("RemediationPlanner")
        logger.info("RemediationPlanner result: %s", remediation_result)

    report["total_time_seconds"] = round(_elapsed(), 2)
    logger.info(
        "Investigation complete in %.2fs. Completed: %s. Warnings: %s",
        report["total_time_seconds"],
        report["sub_agents_completed"],
        report["sub_agents_warnings"],
    )
    return report
