"""
Sub-agent implementations for the AI DevOps Operations Platform.
Refactored: shared _run_agent() eliminates duplicated retry/timeout/loop-detection logic.
"""
import json
import logging
import re
import time
from typing import Any, Dict, Optional

from openai import OpenAI
import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("sub_agents")

# Shared LLM client
_client = OpenAI(
    base_url=config.OLLAMA_BASE_URL,
    api_key=config.OLLAMA_API_KEY,
    timeout=config.TIMEOUT_SECONDS,
)


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------
def _fix_unquoted_json(json_str: str) -> str:
    result = re.sub(r'\{(\s*)(\w+):', r'{\1"\2":', json_str)
    result = re.sub(r':\s*(true)', r': "true"', result, flags=re.IGNORECASE)
    result = re.sub(r':\s*(false)', r': "false"', result, flags=re.IGNORECASE)
    result = re.sub(r':\s*(null)', r': "null"', result, flags=re.IGNORECASE)
    result = re.sub(
        r'("?\w+"?\s*:\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*[,}])',
        lambda m: m.group(1) + '"' + m.group(2) + '"' + m.group(3),
        result,
    )
    return result


def _extract_json(content: str, marker: str) -> Optional[Dict]:
    marker_pos = content.find(marker)
    if marker_pos == -1:
        return None
    json_str = content[marker_pos + len(marker):].strip()
    for attempt in [
        lambda s: json.loads(s),
        lambda s: json.loads(_fix_unquoted_json(s)),
        lambda s: json.loads(s + "}"),
        lambda s: json.loads(s[s.find("{"):s.rfind("}")+1]),
        lambda s: json.loads(_fix_unquoted_json(s[s.find("{"):s.rfind("}")+1])),
    ]:
        try:
            return attempt(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _warning(agent_name: str, reason: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    return {"status": "WARNING", "agent": agent_name, "reason": reason, "data": data}


# ---------------------------------------------------------------------------
# Generic agent runner - eliminates all duplicated retry/timeout/loop logic
# ---------------------------------------------------------------------------
def _run_agent(
    agent_name: str,
    system_prompt: str,
    user_prompt: str,
    termination_marker: str,
) -> Dict[str, Any]:
    """
    Generic LLM agent runner with:
    - exponential back-off retries
    - wall-clock timeout guard
    - loop detection
    - JSON extraction after a termination marker
    """
    start = time.time()
    seen: list = []
    retry = 0

    while retry < config.MAX_RETRIES:
        elapsed = time.time() - start
        if elapsed > config.TIMEOUT_SECONDS:
            logger.warning("[%s] TIMEOUT after %.1fs", agent_name, elapsed)
            return _warning(agent_name, f"Timeout after {elapsed:.1f}s")

        try:
            response = _client.chat.completions.create(
                model=config.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=config.MAX_TOKENS,
            )
            content = response.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("[%s] LLM error: %s", agent_name, exc)
            retry += 1
            if retry >= config.MAX_RETRIES:
                return _warning(agent_name, f"LLM error after {config.MAX_RETRIES} retries: {exc}")
            time.sleep(2 ** retry)
            continue

        if termination_marker not in content:
            logger.warning("[%s] Missing marker, retrying...", agent_name)
            retry += 1
            time.sleep(2 ** retry)
            continue

        result = _extract_json(content, termination_marker)
        if result:
            result["agent"] = agent_name
            result["status"] = "COMPLETE"
            logger.info("[%s] Completed in %.1fs", agent_name, time.time() - start)
            return result

        logger.warning("[%s] JSON parse failed, retrying...", agent_name)
        retry += 1
        time.sleep(2 ** retry)
        continue

        # Loop detection
        if content in seen:
            logger.warning("[%s] Loop detected, breaking.", agent_name)
            break
        seen.append(content)
        if len(seen) >= config.LOOP_DETECTION_THRESHOLD:
            seen.clear()

    return _warning(agent_name, f"Max retries ({config.MAX_RETRIES}) exceeded")


# ---------------------------------------------------------------------------
# Public agent API
# ---------------------------------------------------------------------------
def run_log_analyst(alarm_json: str) -> Dict[str, Any]:
    logger.info("[LogAnalyst] Starting...")
    return _run_agent(
        agent_name="LogAnalyst",
        system_prompt=(
            "You are a log analyst specializing in AWS CloudWatch logs and application logs.\n"
            "Analyze the provided alarm and respond with LOG_ANALYSIS_COMPLETE followed by a JSON object with:\n"
            "- log_source, errors_found, first_error_time, error_pattern\n"
            "Respond ONLY with the marker and JSON."
        ),
        user_prompt=f"Analyze logs for this alarm:\n{alarm_json}\n\nRespond with LOG_ANALYSIS_COMPLETE then JSON.",
        termination_marker="LOG_ANALYSIS_COMPLETE",
    )


def run_metrics_analyst(alarm_json: str) -> Dict[str, Any]:
    logger.info("[MetricsAnalyst] Starting...")
    return _run_agent(
        agent_name="MetricsAnalyst",
        system_prompt=(
            "You are a metrics analyst specializing in AWS CloudWatch metrics.\n"
            "Respond with METRICS_ANALYSIS_COMPLETE followed by a JSON object with:\n"
            "- metric_name, current_value, baseline, trend (increasing/decreasing/stable/spiking), anomaly_type (gradual/sudden/cyclical)\n"
            "Respond ONLY with the marker and JSON."
        ),
        user_prompt=f"Analyze metrics for this alarm:\n{alarm_json}\n\nRespond with METRICS_ANALYSIS_COMPLETE then JSON.",
        termination_marker="METRICS_ANALYSIS_COMPLETE",
    )


def run_remediation_planner(
    alarm_json: str, log_result: Dict, metrics_result: Dict
) -> Dict[str, Any]:
    logger.info("[RemediationPlanner] Starting...")
    context = (
        f"Log Analysis: {json.dumps(log_result.get('data', log_result))}\n"
        f"Metrics Analysis: {json.dumps(metrics_result.get('data', metrics_result))}"
    )
    return _run_agent(
        agent_name="RemediationPlanner",
        system_prompt=(
            "You are a remediation planner specializing in AWS operations.\n"
            "Respond with REMEDIATION_COMPLETE followed by a JSON object with:\n"
            "- severity (critical/high/medium/low), root_cause, immediate_action, long_term_fix, safe_to_automate (yes/no/partial)\n"
            "Respond ONLY with the marker and JSON."
        ),
        user_prompt=(
            f"Create a remediation plan for:\n{alarm_json}\n\n{context}\n\n"
            "Respond with REMEDIATION_COMPLETE then JSON."
        ),
        termination_marker="REMEDIATION_COMPLETE",
    )
