"""
Agent 1 — Job Collector

Fetches job postings from four free sources (no API keys required):
  - Arbeitnow:       European remote roles
  - Remotive:        US remote roles
  - RemoteOK:        US tech startups (many VC-backed)
  - HN Who's Hiring: Monthly Hacker News thread — US startups, often mention funding round

Filters all sources for data science and AI engineering roles.
Returns a combined, deduplicated list of structured job dicts.
"""

import re
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TARGET_ROLES, KEYWORDS, MAX_JOBS

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"
REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
REMOTIVE_CATEGORIES = ["data", "software-dev", "product"]
REMOTEOK_URL = "https://remoteok.com/api"
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


def collect_jobs():
    print("Agent 1 (Job Collector): Fetching job postings...")

    all_raw = []
    all_raw += _fetch_arbeitnow()
    all_raw += _fetch_remotive()
    all_raw += _fetch_remoteok()
    all_raw += _fetch_hn_hiring()

    # Deduplicate by (title, company)
    seen = set()
    relevant = []
    for job in all_raw:
        key = (job["title"], job["company"])
        if key in seen:
            continue
        seen.add(key)
        relevant.append(job)
        if len(relevant) >= MAX_JOBS:
            break

    by_source = {}
    for job in relevant:
        s = job.get("source", "unknown")
        by_source[s] = by_source.get(s, 0) + 1
    source_summary = ", ".join(f"{count} from {source}" for source, count in by_source.items())
    print(f"  Found {len(relevant)} relevant job postings ({source_summary}).")
    return relevant


def _fetch_arbeitnow():
    try:
        response = requests.get(ARBEITNOW_URL, timeout=15)
        response.raise_for_status()
        jobs = response.json().get("data", [])
    except Exception as e:
        print(f"  Warning: Arbeitnow unavailable — {e}")
        return []

    results = []
    for job in jobs:
        if not _is_relevant(job.get("title", ""), job.get("description", ""), job.get("tags", [])):
            continue
        results.append({
            "title": job.get("title"),
            "company": job.get("company_name"),
            "location": job.get("location", "Remote"),
            "remote": job.get("remote", False),
            "url": job.get("url"),
            "description": job.get("description", "")[:800],
            "tags": job.get("tags", []),
            "posted": job.get("created_at"),
            "source": "arbeitnow",
        })
    return results


def _fetch_remotive():
    results = []
    for category in REMOTIVE_CATEGORIES:
        try:
            response = requests.get(
                REMOTIVE_URL,
                params={"category": category, "limit": 50},
                timeout=15
            )
            response.raise_for_status()
            jobs = response.json().get("jobs", [])
        except Exception as e:
            print(f"  Warning: Remotive ({category}) unavailable — {e}")
            continue

        for job in jobs:
            if not _is_relevant(job.get("title", ""), job.get("description", ""), job.get("tags", [])):
                continue
            results.append({
                "title": job.get("title"),
                "company": job.get("company_name"),
                "location": job.get("candidate_required_location", "Remote"),
                "remote": True,
                "url": job.get("url"),
                "description": job.get("description", "")[:800],
                "tags": job.get("tags", []) if isinstance(job.get("tags"), list) else [],
                "posted": job.get("publication_date"),
                "source": "remotive",
            })
    return results


def _fetch_remoteok():
    try:
        response = requests.get(
            REMOTEOK_URL,
            headers={"User-Agent": "job-market-analyzer/1.0"},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        jobs = [j for j in data if isinstance(j, dict) and j.get("position")]
    except Exception as e:
        print(f"  Warning: RemoteOK unavailable — {e}")
        return []

    results = []
    for job in jobs:
        tags = job.get("tags", []) or []
        if not _is_relevant(job.get("position", ""), job.get("description", ""), tags):
            continue
        results.append({
            "title": job.get("position"),
            "company": job.get("company"),
            "location": job.get("location", "Remote"),
            "remote": True,
            "url": job.get("url"),
            "description": job.get("description", "")[:800],
            "tags": tags if isinstance(tags, list) else [],
            "posted": job.get("date"),
            "source": "remoteok",
        })
    return results


def _fetch_hn_hiring():
    """Fetch jobs from the monthly HN 'Who is Hiring' thread.

    This is one of the best sources for US-based funded startups — many companies
    mention their funding round directly in their post (e.g. 'Series B, $40M').
    """
    # Step 1: Find the latest Who's Hiring thread
    try:
        search_resp = requests.get(
            HN_SEARCH_URL,
            params={"query": "Ask HN: Who is hiring", "tags": "ask_hn", "hitsPerPage": 3},
            timeout=10
        )
        search_resp.raise_for_status()
        hits = search_resp.json().get("hits", [])
        if not hits:
            return []
        thread_id = hits[0]["objectID"]
        thread_title = hits[0].get("title", "HN Who's Hiring")
    except Exception as e:
        print(f"  Warning: HN search unavailable — {e}")
        return []

    # Step 2: Fetch the top-level comments (each one is a job posting)
    try:
        comments_resp = requests.get(
            HN_SEARCH_URL,
            params={"tags": f"comment,story_{thread_id}", "hitsPerPage": 200},
            timeout=10
        )
        comments_resp.raise_for_status()
        comments = comments_resp.json().get("hits", [])
    except Exception as e:
        print(f"  Warning: Could not fetch HN comments — {e}")
        return []

    results = []
    for comment in comments:
        raw_text = _strip_html(comment.get("comment_text", ""))
        if not raw_text:
            continue

        text_lower = raw_text.lower()

        # Only keep remote-friendly posts
        if "remote" not in text_lower:
            continue

        # Only keep posts matching our target roles or keywords
        if not _is_relevant_text(text_lower):
            continue

        # HN convention: first line is "Company | Role | Location | ..."
        first_line = raw_text.split("\n")[0]
        parts = [p.strip() for p in first_line.split("|")]
        company = parts[0] if parts else "Unknown"
        title = parts[1] if len(parts) > 1 else "See posting"

        # Extract the first URL from the post
        url_match = re.search(r'https?://\S+', raw_text)
        url = url_match.group(0).rstrip(".,)") if url_match else \
              f"https://news.ycombinator.com/item?id={comment.get('objectID', '')}"

        results.append({
            "title": title[:100],
            "company": company[:80],
            "location": "Remote (US)",
            "remote": True,
            "url": url,
            "description": raw_text[:800],
            "tags": [],
            "posted": comment.get("created_at"),
            "source": f"hn_hiring ({thread_title})",
        })

    return results


def _strip_html(text):
    """Remove HTML tags and decode common HTML entities."""
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = text.replace('&#x27;', "'").replace('&amp;', '&') \
               .replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    return re.sub(r'\s+', ' ', text).strip()


def _is_relevant(title, description, tags):
    title = title.lower()
    description = description.lower()
    tags_str = " ".join(tags).lower() if isinstance(tags, list) else ""
    title_match = any(role in title for role in TARGET_ROLES)
    keyword_match = any(kw in description or kw in tags_str for kw in KEYWORDS)
    return title_match or keyword_match


def _is_relevant_text(text_lower):
    return any(kw in text_lower for kw in KEYWORDS + TARGET_ROLES)
