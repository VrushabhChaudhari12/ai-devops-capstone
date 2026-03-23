"""
Sub-agent implementations for the AI DevOps Operations Platform.
Each sub-agent makes ONE LLM call to Ollama with full termination safety.
"""

import json
import re
import time
from typing import Dict, Any, Optional
from openai import OpenAI

# Configuration constants
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY = "ollama"
OLLAMA_MODEL = "llama3.2"
MAX_TOKENS = 400

# Per-sub-agent constants
TERMINATION_CONDITION_LOG = "LOG_ANALYSIS_COMPLETE"
TERMINATION_CONDITION_METRICS = "METRICS_ANALYSIS_COMPLETE"
TERMINATION_CONDITION_REMEDIATION = "REMEDIATION_COMPLETE"
MAX_RETRIES = 3
TIMEOUT_SECONDS = 60
LOOP_DETECTION_THRESHOLD = 3


def _fix_unquoted_json(json_str: str) -> str:
    """Fix unquoted string values in JSON (like keys without quotes or string values without quotes)."""
    import re

    # Fix unquoted keys: change {key: to {"key":
    result = re.sub(r'\{(\s*)(\w+):', r'{\1"\2":', json_str)

    # Fix unquoted string values (simple cases: word characters not starting with quote)
    # This is tricky - we need to be careful not to break numbers, booleans, null
    # Pattern: :, then whitespace, then word not in [true, false, null, number]
    result = re.sub(r':\s*(true)', r': "true"', result, flags=re.IGNORECASE)
    result = re.sub(r':\s*(false)', r': "false"', result, flags=re.IGNORECASE)
    result = re.sub(r':\s*(null)', r': "null"', result, flags=re.IGNORECASE)

    # For other unquoted words after colons (but not after quotes)
    # This handles cases like "trend": increasing -> "trend": "increasing"
    result = re.sub(r'("?\w+"?\s*:\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*[,}])',
                     lambda m: m.group(1) + '"' + m.group(2) + '"' + m.group(3),
                     result)

    return result


def _extract_json(content: str, marker: str) -> Optional[Dict]:
    """
    Extract JSON from content after the termination marker.
    Tries multiple parsing approaches.
    """
    # Find the marker and get everything after it
    marker_pos = content.find(marker)
    if marker_pos == -1:
        return None

    json_str = content[marker_pos + len(marker):].strip()

    # Try 1: Direct parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Try 2: Fix unquoted values and parse
    fixed = _fix_unquoted_json(json_str)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Try 3: If missing closing brace, try adding it
    if not json_str.rstrip().endswith('}'):
        try_with_brace = json_str + '}'
        try:
            return json.loads(try_with_brace)
        except json.JSONDecodeError:
            pass

    # Try 4: Find first { and last } and extract just that portion
    first_brace = json_str.find('{')
    last_brace = json_str.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        # Only take from first { to last }
        extracted = json_str[first_brace:last_brace + 1]
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass

        # Try with fix
        fixed_extracted = _fix_unquoted_json(extracted)
        try:
            return json.loads(fixed_extracted)
        except json.JSONDecodeError:
            pass

    # Print debug info if all failed
    # print(f"[DEBUG] Raw response after marker: {json_str[:200]}")

    return None


def _create_warning_response(agent_name: str, reason: str, partial_data: Optional[Dict] = None) -> Dict[str, Any]:
    """Create a warning response dict."""
    result = {
        "status": "WARNING",
        "agent": agent_name,
        "reason": reason,
        "data": partial_data
    }
    return result


def run_log_analyst(alarm_json: str) -> Dict[str, Any]:
    """
    Run the Log Analyst sub-agent to analyze logs for the alarm.

    Args:
        alarm_json: The CloudWatch alarm as JSON string

    Returns:
        Dictionary with log analysis results or WARNING dict
    """
    print("\n[LogAnalyst] Starting log analysis...")

    system_prompt = """You are a log analyst specializing in AWS CloudWatch logs and application logs.
Analyze the provided alarm and respond with LOG_ANALYSIS_COMPLETE followed by a JSON object with these exact keys:
- log_source: where the logs came from (e.g., CloudWatch, application logs, system logs)
- errors_found: number of errors found in logs
- first_error_time: timestamp of first error (or 'N/A')
- error_pattern: description of error pattern observed (or 'none')

Respond ONLY with the completion marker and JSON, no other text."""

    user_prompt = f"""Analyze logs for this CloudWatch alarm:
{alarm_json}

Provide your analysis with LOG_ANALYSIS_COMPLETE followed by the JSON."""

    client = OpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key=OLLAMA_API_KEY,
        timeout=TIMEOUT_SECONDS
    )

    start_time = time.time()
    previous_outputs = []
    retry_count = 0

    while retry_count < MAX_RETRIES:
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > TIMEOUT_SECONDS:
            print(f"[LogAnalyst] TIMEOUT after {elapsed:.1f}s")
            return _create_warning_response("LogAnalyst", f"Timeout after {elapsed:.1f}s")

        try:
            response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=MAX_TOKENS
            )

            content = response.choices[0].message.content.strip()

            # Layer 1: Check termination condition
            if TERMINATION_CONDITION_LOG not in content:
                print(f"[LogAnalyst] Warning: Missing termination condition. Retrying...")
                retry_count += 1
                time.sleep(2 ** retry_count)
                continue

            # Extract JSON after the termination marker
            result = _extract_json(content, TERMINATION_CONDITION_LOG)

            if result:
                result["agent"] = "LogAnalyst"
                result["status"] = "COMPLETE"
                print(f"[LogAnalyst] Completed in {time.time() - start_time:.1f}s")
                return result
            else:
                print(f"[LogAnalyst] JSON parse error. Retrying...")
                retry_count += 1
                time.sleep(2 ** retry_count)
                continue

            # Layer 4: Loop detection
            if content in previous_outputs:
                print("[LogAnalyst] Loop detected. Breaking.")
                break

            previous_outputs.append(content)
            if len(previous_outputs) >= LOOP_DETECTION_THRESHOLD:
                previous_outputs.clear()

        except Exception as e:
            print(f"[LogAnalyst] Error: {e}")
            retry_count += 1
            if retry_count >= MAX_RETRIES:
                return _create_warning_response("LogAnalyst", f"Failed after {MAX_RETRIES} retries: {e}")
            time.sleep(2 ** retry_count)

    return _create_warning_response("LogAnalyst", f"Max retries ({MAX_RETRIES}) exceeded")


def run_metrics_analyst(alarm_json: str) -> Dict[str, Any]:
    """
    Run the Metrics Analyst sub-agent to analyze metrics for the alarm.

    Args:
        alarm_json: The CloudWatch alarm as JSON string

    Returns:
        Dictionary with metrics analysis results or WARNING dict
    """
    print("\n[MetricsAnalyst] Starting metrics analysis...")

    system_prompt = """You are a metrics analyst specializing in AWS CloudWatch metrics.
Analyze the provided alarm and respond with METRICS_ANALYSIS_COMPLETE followed by a JSON object with these exact keys:
- metric_name: the CloudWatch metric name
- current_value: the current metric value from the alarm
- baseline: what the normal baseline value should be
- trend: increasing, decreasing, stable, or spiking
- anomaly_type: gradual, sudden, or cyclical

Respond ONLY with the completion marker and JSON, no other text."""

    user_prompt = f"""Analyze metrics for this CloudWatch alarm:
{alarm_json}

Provide your analysis with METRICS_ANALYSIS_COMPLETE followed by the JSON."""

    client = OpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key=OLLAMA_API_KEY,
        timeout=TIMEOUT_SECONDS
    )

    start_time = time.time()
    previous_outputs = []
    retry_count = 0

    while retry_count < MAX_RETRIES:
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > TIMEOUT_SECONDS:
            print(f"[MetricsAnalyst] TIMEOUT after {elapsed:.1f}s")
            return _create_warning_response("MetricsAnalyst", f"Timeout after {elapsed:.1f}s")

        try:
            response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=MAX_TOKENS
            )

            content = response.choices[0].message.content.strip()

            # Layer 1: Check termination condition
            if TERMINATION_CONDITION_METRICS not in content:
                print(f"[MetricsAnalyst] Warning: Missing termination condition. Retrying...")
                retry_count += 1
                time.sleep(2 ** retry_count)
                continue

            # Extract JSON after the termination marker
            result = _extract_json(content, TERMINATION_CONDITION_METRICS)

            if result:
                result["agent"] = "MetricsAnalyst"
                result["status"] = "COMPLETE"
                print(f"[MetricsAnalyst] Completed in {time.time() - start_time:.1f}s")
                return result
            else:
                print(f"[MetricsAnalyst] JSON parse error. Retrying...")
                retry_count += 1
                time.sleep(2 ** retry_count)
                continue

            # Layer 4: Loop detection
            if content in previous_outputs:
                print("[MetricsAnalyst] Loop detected. Breaking.")
                break

            previous_outputs.append(content)
            if len(previous_outputs) >= LOOP_DETECTION_THRESHOLD:
                previous_outputs.clear()

        except Exception as e:
            print(f"[MetricsAnalyst] Error: {e}")
            retry_count += 1
            if retry_count >= MAX_RETRIES:
                return _create_warning_response("MetricsAnalyst", f"Failed after {MAX_RETRIES} retries: {e}")
            time.sleep(2 ** retry_count)

    return _create_warning_response("MetricsAnalyst", f"Max retries ({MAX_RETRIES}) exceeded")


def run_remediation_planner(alarm_json: str, log_result: Dict, metrics_result: Dict) -> Dict[str, Any]:
    """
    Run the Remediation Planner sub-agent to create a remediation plan.

    Args:
        alarm_json: The CloudWatch alarm as JSON string
        log_result: Results from LogAnalyst
        metrics_result: Results from MetricsAnalyst

    Returns:
        Dictionary with remediation plan or WARNING dict
    """
    print("\n[RemediationPlanner] Starting remediation planning...")

    context_summary = f"""
Log Analysis: {json.dumps(log_result.get('data', log_result) if 'data' in log_result else log_result)}
Metrics Analysis: {json.dumps(metrics_result.get('data', metrics_result) if 'data' in metrics_result else metrics_result)}
"""

    system_prompt = """You are a remediation planner specializing in AWS operations.
Create a remediation plan based on log and metrics analysis and respond with REMEDIATION_COMPLETE followed by a JSON object with these exact keys:
- severity: critical, high, medium, or low
- root_cause: description of the root cause
- immediate_action: what to do right now to mitigate
- long_term_fix: what to do to prevent recurrence
- safe_to_automate: yes, no, or partial (with reason)

Respond ONLY with the completion marker and JSON, no other text."""

    user_prompt = f"""Create a remediation plan for this CloudWatch alarm:
{alarm_json}

{context_summary}

Provide your plan with REMEDIATION_COMPLETE followed by the JSON."""

    client = OpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key=OLLAMA_API_KEY,
        timeout=TIMEOUT_SECONDS
    )

    start_time = time.time()
    previous_outputs = []
    retry_count = 0

    while retry_count < MAX_RETRIES:
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > TIMEOUT_SECONDS:
            print(f"[RemediationPlanner] TIMEOUT after {elapsed:.1f}s")
            return _create_warning_response("RemediationPlanner", f"Timeout after {elapsed:.1f}s")

        try:
            response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=MAX_TOKENS
            )

            content = response.choices[0].message.content.strip()

            # Layer 1: Check termination condition
            if TERMINATION_CONDITION_REMEDIATION not in content:
                print(f"[RemediationPlanner] Warning: Missing termination condition. Retrying...")
                retry_count += 1
                time.sleep(2 ** retry_count)
                continue

            # Extract JSON after the termination marker
            result = _extract_json(content, TERMINATION_CONDITION_REMEDIATION)

            if result:
                result["agent"] = "RemediationPlanner"
                result["status"] = "COMPLETE"
                print(f"[RemediationPlanner] Completed in {time.time() - start_time:.1f}s")
                return result
            else:
                print(f"[RemediationPlanner] JSON parse error. Retrying...")
                retry_count += 1
                time.sleep(2 ** retry_count)
                continue

            # Layer 4: Loop detection
            if content in previous_outputs:
                print("[RemediationPlanner] Loop detected. Breaking.")
                break

            previous_outputs.append(content)
            if len(previous_outputs) >= LOOP_DETECTION_THRESHOLD:
                previous_outputs.clear()

        except Exception as e:
            print(f"[RemediationPlanner] Error: {e}")
            retry_count += 1
            if retry_count >= MAX_RETRIES:
                return _create_warning_response("RemediationPlanner", f"Failed after {MAX_RETRIES} retries: {e}")
            time.sleep(2 ** retry_count)

    return _create_warning_response("RemediationPlanner", f"Max retries ({MAX_RETRIES}) exceeded")