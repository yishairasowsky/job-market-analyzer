# Job Market Analyzer

A multi-agent AI system that finds relevant job openings, identifies recently funded companies, analyzes the market, and writes personalized outreach messages — all in a single run.

## What it does

Five specialized AI agents work together in a pipeline:

1. **Job Collector** — Fetches remote job postings from multiple sources (HN Who's Hiring, Remotive, RemoteOK, Arbeitnow). Filters for data science, AI engineering, and ML positions. Deduplicates across runs so you only see new postings each week.

2. **Funding Detector** — For each company found, scans the job description for explicit funding mentions (common in HN posts), then falls back to a DuckDuckGo web search interpreted by Claude. Companies that recently raised money are flagged as high-priority targets — they have capital and are actively hiring.

3. **Skills Analyzer** — Uses Claude to read across all postings and extract the most in-demand technical skills, role focus areas, skills gaps, and market trends for that week.

4. **Report Writer** — Synthesizes all of the above into a clean, actionable weekly report personalized to your background and skills, with priority companies, recommended actions, and URLs.

5. **Outreach Writer** — For each top target (funded companies first, then best job matches), researches what the company actually does and generates two ready-to-send messages: a LinkedIn connection request (under 300 characters) and a personalized cold email with subject line.

## Architecture

```
main.py  (orchestrator)
│
├── Agent 1: agents/job_collector.py     ← fetches & filters job postings
├── Agent 2: agents/funding_detector.py  ← text scan + web search to find funded companies
├── Agent 3: agents/skills_analyzer.py   ← Claude extracts skill trends from postings
├── Agent 4: agents/report_writer.py     ← Claude synthesizes personalized weekly report
└── Agent 5: agents/outreach_writer.py   ← Claude writes personalized outreach per company
```

Each agent has a single responsibility and passes its output forward. The orchestrator in `main.py` coordinates the full pipeline. This is the cavalry-leader pattern: the developer sets strategy and architecture; the agents do the heavy lifting.

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

The report is saved to `reports/report_YYYY-MM-DD.txt`.
Outreach messages are saved to `outreach/outreach_YYYY-MM-DD.txt`.

## Configuration

Edit `config.py` to personalize for your own background, target roles, skills, and location preferences.

## Example output

```
JOB MARKET REPORT — May 31, 2026
==================================================

HIGHLIGHTS
Three recently funded companies are hiring this week with roles that match
your Python and LLM pipeline background. Coefficient (seed) and Opsani
(Series A, Redpoint) are both strong targets.

PRIORITY COMPANIES TO APPLY TO
- Coefficient (seed funding) — Data Engineer, Remote | https://...
- Opsani (Series A, Redpoint) — ML Engineer, Remote | https://...

IN-DEMAND SKILLS THIS WEEK
Python ✓ · LLMs ✓ · RAG ✓ · AWS (gap) · LangChain ✓

RECOMMENDED ACTIONS
1. Apply to Coefficient and Opsani this week — both have recent funding.
2. One targeted outreach message to each hiring manager (see outreach file).
3. Add a RAG project to GitHub to close the one visible skills gap.
```

```
OUTREACH MESSAGES — May 31, 2026
==================================================

COMPANY: Coefficient
ROLE:    Data Engineer
FUNDED:  seed round

MESSAGE 1 — LinkedIn (under 300 chars):
Hi [Name] — I saw Coefficient is hiring for data engineering. I've been
building AI pipelines in Python and the Claude API and would love to connect.

MESSAGE 2 — Cold email:
Subject: Data Engineer interest — Python / LLM pipelines

Hi [Name], I came across Coefficient while researching...
```

## Tech stack

- Python
- [Anthropic API](https://docs.anthropic.com) (Claude Sonnet 4.6)
- [HN Who's Hiring](https://news.ycombinator.com/jobs) via Algolia search API
- [Remotive API](https://remotive.com/api/remote-jobs) (free, no key required)
- [Arbeitnow API](https://arbeitnow.com) (free, no key required)
- [ddgs](https://pypi.org/project/ddgs/) for DuckDuckGo web search
