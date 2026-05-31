# Job Market Analyzer

A multi-agent AI system that produces a weekly report of relevant job openings, with priority given to companies that recently received funding.

## What it does

Four specialized AI agents work together in a pipeline:

1. **Job Collector** — Fetches remote job postings from two public APIs (Arbeitnow + Remotive), covering both European and US-based remote roles. Filters for data science, AI engineering, and ML positions.

2. **Funding Detector** — For each company found, searches the web for recent funding news (2024–2026). Companies that recently raised money are flagged as high-priority targets — they have capital and are in growth mode.

3. **Skills Analyzer** — Uses Claude to read across all postings and extract the most in-demand technical skills, role focus areas, and market trends for that week.

4. **Report Writer** — Synthesizes all of the above into a clean, actionable weekly report with recommended companies to apply to and specific actions to take.

## Architecture

```
main.py
│
├── Agent 1: agents/job_collector.py     ← fetches & filters job postings
├── Agent 2: agents/funding_detector.py  ← web search + Claude to find funded companies
├── Agent 3: agents/skills_analyzer.py   ← Claude extracts skill trends from postings
└── Agent 4: agents/report_writer.py     ← Claude synthesizes final report
```

Each agent has a single responsibility and passes its output to the next. The orchestrator in `main.py` coordinates the full pipeline.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your Anthropic API key to .env
```

Get an API key at [console.anthropic.com](https://console.anthropic.com).

## Run

```bash
python main.py
```

The report is printed to the terminal and saved to `reports/report_YYYY-MM-DD.txt`.

## Configuration

Edit `config.py` to change target roles, keywords, and how many companies to check for funding.

## Example output

```
JOB MARKET REPORT
Week of May 31, 2026
==================================================

HIGHLIGHTS
No newly funded companies this week, but the remote market is active for
senior AI and GenAI talent — particularly around LLMs, RAG pipelines, and
AWS-based AI systems.

PRIORITY COMPANIES TO APPLY TO
- FNTIO — Senior AI Systems Engineer (AWS), 100% Remote
- Talents2Germany — Senior GenAI Engineer (LLMs/RAG/Python), Remote

IN-DEMAND SKILLS THIS WEEK
Python · LLMs · RAG · GenAI · AWS · LangChain

RECOMMENDED ACTIONS
1. Apply to FNTIO and Talents2Germany this week.
2. Make RAG and LLM project work visible on GitHub and LinkedIn.
3. Prepare a one-paragraph "AI in production" story for interviews.
```

## Tech stack

- Python
- [Anthropic API](https://docs.anthropic.com) (Claude Sonnet)
- [Arbeitnow API](https://arbeitnow.com) (free, no key required)
- [Remotive API](https://remotive.com/api/remote-jobs) (free, no key required)
- [ddgs](https://pypi.org/project/ddgs/) for web search
