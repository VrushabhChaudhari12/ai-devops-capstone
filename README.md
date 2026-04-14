# AI DevOps Operations Platform — Capstone Project

> **End-to-end multi-agent AIOps platform** — a Lead Orchestrator receives CloudWatch alarms and coordinates three specialist LLM sub-agents (LogAnalyst, MetricsAnalyst, RemediationPlanner) to autonomously investigate incidents and generate Slack-ready remediation reports in under 5 minutes.

---

## Problem

When a CloudWatch alarm fires, the on-call engineer manually pulls logs, checks metrics dashboards, identifies root cause, and writes a remediation plan — a process that takes 45–90 minutes and requires deep system knowledge. Nights and weekends make this worse.

## Solution

A **multi-agent AI system** that mirrors the mental model of a senior SRE: one orchestrator receives the alarm context and dispatches specialist agents in sequence. Each agent has full termination safety (retries, timeout, loop detection) so the system never hangs. The result is a comprehensive Slack investigation report in under 5 minutes.

---

## Architecture

```
CloudWatch Alarm (JSON)
        │
        ▼
  orchestrator.py          ← Lead Orchestrator
  (coordinates all agents)   ─ total timeout: 300s
        │
        ├── 1. LogAnalyst        ← Reads CloudWatch logs — identifies errors, patterns
        │        └─► LOG_ANALYSIS_COMPLETE
        │
        ├── 2. MetricsAnalyst    ← Reads metric baselines, trends, anomaly type
        │        └─► METRICS_ANALYSIS_COMPLETE
        │
        └── 3. RemediationPlanner ← Synthesizes findings → severity + fix plan
                 └─► REMEDIATION_PLAN_COMPLETE
                        │
                        ▼
               slack_reporter.py    ← Formats + posts final Slack report
```

---

## Sub-Agents

| Agent | Responsibility | Termination Signal |
|---|---|---|
| **LogAnalyst** | Scans CloudWatch logs for error patterns, first-occurrence timestamps, error frequency | `LOG_ANALYSIS_COMPLETE` |
| **MetricsAnalyst** | Compares current metric vs baseline, identifies trend (spiking/dropping/steady), anomaly type | `METRICS_ANALYSIS_COMPLETE` |
| **RemediationPlanner** | Synthesizes log + metric findings into a severity-rated remediation plan with immediate + long-term actions | `REMEDIATION_PLAN_COMPLETE` |

---

## Four-Layer Termination Safety (Per Agent)

Every sub-agent implements independent, non-blocking safety:

| Layer | Mechanism | Value |
|---|---|---|
| **1. Named termination** | Agent must echo a specific completion string | Agent-specific signal |
| **2. Max retries** | Hard ceiling on retry attempts | 3 retries |
| **3. Per-agent timeout** | Wall-clock limit per LLM call | 60 seconds |
| **4. Loop detection** | Detects repeated identical outputs | Last 3 responses |

**Orchestrator total timeout**: 300 seconds (5 minutes) for entire investigation.

**Graceful degradation**: if any sub-agent fails, investigation continues with remaining agents and final report includes a `WARNING` banner for affected sections.

---

## Alarm Scenarios

| Scenario | Trigger | Sub-agents Involved |
|---|---|---|
| `cpu_spike` | EC2 CPUUtilization > 85% for 5 min | All 3 |
| `rds_connections` | DB connections at max pool limit | All 3 |
| `pipeline_failure` | CodePipeline execution failed | LogAnalyst + RemediationPlanner |

---

## Sample Slack Report Output

```
======================================================================
              SLACK INVESTIGATION REPORT
======================================================================

INCIDENT SUMMARY
----------------------------------------------------------------------
  Alarm Name  : HighCPU - production-api (i-0abc123)
  Status      : COMPLETE
  Duration    : 45.2s
  Agents done : LogAnalyst, MetricsAnalyst, RemediationPlanner

LOG ANALYSIS
----------------------------------------------------------------------
  Log Source  : /aws/ec2/production-api
  Errors      : 3  |  First seen: 2026-04-14T10:25:00Z
  Pattern     : Connection pool exhaustion - "too many clients"

METRICS ANALYSIS
----------------------------------------------------------------------
  Metric      : CPUUtilization
  Current     : 96%  |  Baseline: 45%  |  Trend: spiking
  Anomaly     : sudden - correlated with deploy at 10:22Z

REMEDIATION PLAN
----------------------------------------------------------------------
  Severity        : HIGH
  Root Cause      : Application not releasing DB connections after deploy
  Immediate       : Restart application servers + scale out ASG by 2
  Long-term       : Fix connection pool leak in auth-service v2.3
  Safe to automate: PARTIAL - requires monitoring after restart
======================================================================
```

---

## Tech Stack

- **Language**: Python 3.11+
- **LLM runtime**: Ollama (`llama3.2`) — fully local, no external API
- **LLM client**: `openai` SDK (OpenAI-compatible endpoint)
- **Alerting**: Slack Incoming Webhooks
- **Config**: `config.py` + environment variables

---

## Setup & Run

```bash
# 1. Start Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama run llama3.2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run all alarm scenarios
python main.py

# Optional env vars
export BASE_URL=http://localhost:11434/v1
export MODEL=llama3.2
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
export LOG_LEVEL=INFO
```

---

## Why This Matters (Resume Context)

This is the capstone project — it pulls together every pattern from the portfolio:
- **Multi-agent orchestration** with real termination safety → production-ready agentic design
- **AIOps at scale**: handles CPU, DB, and pipeline incidents in a single platform
- Demonstrates **SRE thinking**: MTTR reduction, graceful degradation, partial-result tolerance
- Local LLM → incident data stays in VPC, enterprise-compliant
- Directly analogous to: AWS Systems Manager Automation, PagerDuty Event Intelligence, Datadog Watchdog

---

## Project Structure

```
ai-devops-capstone/
├── config.py           # Centralized config (env vars, defaults)
├── main.py             # CLI entrypoint: runs all alarm scenarios
├── orchestrator.py     # Lead Orchestrator: coordinates sub-agents, enforces timeouts
├── sub_agents.py       # LogAnalyst, MetricsAnalyst, RemediationPlanner agents
├── mock_data.py        # Simulated CloudWatch alarm + log + metric scenarios
├── slack_reporter.py   # Formats and posts final Slack investigation report
└── requirements.txt
```

---

*MIT License*
