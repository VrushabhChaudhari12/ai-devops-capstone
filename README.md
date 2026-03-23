# AI DevOps Operations Platform - Capstone Project

An End-to-End AI DevOps Operations Platform with a multi-agent system where a Lead Orchestrator receives CloudWatch alarms and delegates to specialist sub-agents.

## Overview

This project implements a sophisticated multi-agent AI system for automated incident investigation and remediation planning. The system uses a Lead Orchestrator that receives CloudWatch alarms and delegates to three specialized sub-agents in sequence.

## Architecture

```
Lead Orchestrator
    │
    ├──► LogAnalyst (analyzes logs)
    │
    ├──► MetricsAnalyst (analyzes metrics)
    │
    └──► RemediationPlanner (creates remediation plan)
              │
              ▼
        Final Slack Report
```

## Sub-Agents

1. **LogAnalyst**: Analyzes CloudWatch and application logs to identify errors and patterns
2. **MetricsAnalyst**: Analyzes metric baselines, trends, and anomaly types
3. **RemediationPlanner**: Creates remediation plans with severity, root cause, and fix recommendations

## Key Features

- **Multi-Agent Coordination**: Lead Orchestrator manages three sub-agents
- **Four-Layer Termination Safety on EVERY agent**:
  1. Named termination condition (e.g., "LOG_ANALYSIS_COMPLETE")
  2. MAX_RETRIES=3 with exponential backoff
  3. TIMEOUT_SECONDS=60 per sub-agent
  4. Loop detection (tracks last 3 responses)
- **Total Orchestrator Timeout**: 300 seconds (5 minutes) wall clock
- **Graceful Degradation**: Returns partial results with WARNING flag if any sub-agent fails
- **Token Budget**: max_tokens=400 per LLM call

## Supported Alarm Scenarios

1. **CPU Spike Alarm**: EC2 CPU utilization exceeding threshold
2. **RDS Connection Alarm**: Database connections at maximum
3. **Pipeline Failure Alarm**: CodePipeline build failure

## Stack

- **Language**: Python 3.10+
- **LLM**: Ollama (localhost:11434) with llama3.2 model
- **Dependencies**: openai

## Installation

1. Install the required Python packages:

```bash
pip install -r requirements.txt
```

2. Ensure Ollama is running with the llama3.2 model:

```bash
ollama serve
# In another terminal:
ollama pull llama3.2
```

## Usage

Run the platform for all three alarm scenarios:

```bash
py main.py
```

This will:
1. Process each CloudWatch alarm scenario
2. Run the Lead Orchestrator to coordinate investigation
3. Execute all three sub-agents in sequence
4. Generate a final Slack-style report

## Output Format

The platform generates a comprehensive Slack report with these sections:

- **INCIDENT SUMMARY**: Alarm name, status, total investigation time
- **LOG ANALYSIS**: Log source, errors found, error patterns
- **METRICS ANALYSIS**: Metric name, current value, baseline, trend
- **REMEDIATION PLAN**: Severity, root cause, immediate action, long-term fix

## Termination Rules

Each sub-agent implements these termination layers:

| Layer | Description | Value |
|-------|-------------|-------|
| Termination Condition | Named string in response | Agent-specific |
| Max Retries | Hard ceiling on retries | 3 |
| Timeout | Wall clock limit | 60 seconds |
| Loop Detection | Track repeated outputs | Last 3 responses |

The Lead Orchestrator has a total timeout of 300 seconds (5 minutes) for the entire investigation.

## Error Handling

If any sub-agent hits MAX_RETRIES or TIMEOUT:
- Returns a partial result with WARNING flag
- Investigation continues with remaining sub-agents
- Final report includes WARNING banner for affected sub-agents
- Never hangs or blocks indefinitely

## Example Output

```
======================================================================
                    SLACK INVESTIGATION REPORT
======================================================================

📋 *INCIDENT SUMMARY*
----------------------------------------------------------------------
*Alarm Name:* HighCPU utilization on production instance
*Status:* COMPLETE
*Total Investigation Time:* 45.2s
*Sub-agents Completed:* LogAnalyst, MetricsAnalyst, RemediationPlanner

📊 *LOG ANALYSIS*
----------------------------------------------------------------------
*Log Source:* CloudWatch Logs
*Errors Found:* 3
*First Error Time:* 2024-03-15T14:25:00Z
*Error Pattern:* Connection pool exhaustion

📈 *METRICS ANALYSIS*
----------------------------------------------------------------------
*Metric Name:* CPUUtilization
*Current Value:* 96
*Baseline:* 45
*Trend:* spiking
*Anomaly Type:* sudden

🔧 *REMEDIATION PLAN*
----------------------------------------------------------------------
*Severity:* high
*Root Cause:* Application not releasing connections properly
*Immediate Action:* Scale up EC2 instances
*Long-term Fix:* Fix connection pool leak in application code
*Safe to Automate:* partial - requires monitoring

======================================================================
```

## License

MIT