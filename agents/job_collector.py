"""
Agent 1 — Job Collector

Fetches job postings from four free sources (no API keys required):
  - Arbeitnow:       European remote roles
  - Remotive:        US remote roles
  - RemoteOK:        US tech startups (many VC-backed)
  - HN Who's Hiring: Monthly Hacker News thread — US startups, often mention funding

Applies location filtering to skip jobs that require EU work authorization.
Deduplicates against previously seen jobs so each run surfaces new postings.
"""

import re
import json
import requests
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TARGET_ROLES, KEYWORDS, MAX_JOBS, EXCLUDED_LOCATION_PHRASES, HN_THREADS_TO_FETCH

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"
REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
REMOTIVE_CATEGORIES = ["data", "software-dev", "product"]
REMOTEOK_URL = "https://remoteok.com/api"
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"

SEEN_JOBS_FILE = Path(__file__).parent.parent / "data" / "seen_jobs.json"


def collect_jobs():
    print("Agent 1 (Job Collector): Fetching job postings...")

    seen_urls = _load_seen_urls()

    # HN first — highest quality US startup jobs with funding mentions
    # Remotive and RemoteOK next — US remote
    # Arbeitnow last — European, lower signal for this user
    all_raw = []
    all_raw += _fetch_hn_hiring()
    all_raw += _fetch_remotive()
    all_raw += _fetch_remoteok()
    all_raw += _fetch_arbeitnow()

    # Filter out excluded locations and already-seen jobs
    filtered = []
    for job in all_raw:
        if _is_excluded_location(job):
            continue
        url = job.get("url", "")
        if url and url in seen_urls:
            continue
        filtered.append(job)

    # Deduplicate within this run by (title, company)
    seen_this_run = set()
    relevant = []
    for job in filtered:
        key = (job.get("title", ""), job.get("company", ""))
        if key in seen_this_run:
            continue
        seen_this_run.add(key)
        relevant.append(job)
        if len(relevant) >= MAX_JOBS:
            break

    # Save the URLs we are about to report so next run skips them
    new_urls = [j["url"] for j in relevant if j.get("url")]
    _save_seen_urls(seen_urls | set(new_urls))

    by_source = {}
    for job in relevant:
        s = job.get("source", "unknown")
        by_source[s] = by_source.get(s, 0) + 1
    source_summary = ", ".join(f"{count} from {source}" for source, count in by_source.items())
    print(f"  Found {len(relevant)} new job postings ({source_summary}).")
    return relevant


# ---------------------------------------------------------------------------
# Source fetchers
# ---------------------------------------------------------------------------

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
    """Fetch jobs from recent HN 'Who is Hiring' threads.

    HN companies are often VC-backed US startups that explicitly mention
    their funding round in the post text.
    """
    # Find the most recent threads
    try:
        search_resp = requests.get(
            HN_SEARCH_URL,
            params={"query": "Ask HN: Who is hiring", "tags": "ask_hn", "hitsPerPage": HN_THREADS_TO_FETCH + 2},
            timeout=10
        )
        search_resp.raise_for_status()
        hits = search_resp.json().get("hits", [])
        # Keep only actual "Who is hiring" threads
        threads = [h for h in hits if "who is hiring" in h.get("title", "").lower()][:HN_THREADS_TO_FETCH]
    except Exception as e:
        print(f"  Warning: HN search unavailable — {e}")
        return []

    results = []
    for thread in threads:
        thread_id = thread["objectID"]
        thread_label = thread.get("title", "HN Hiring")
        try:
            comments_resp = requests.get(
                HN_SEARCH_URL,
                params={"tags": f"comment,story_{thread_id}", "hitsPerPage": 200},
                timeout=10
            )
            comments_resp.raise_for_status()
            comments = comments_resp.json().get("hits", [])
        except Exception as e:
            print(f"  Warning: Could not fetch HN comments for {thread_label} — {e}")
            continue

        for comment in comments:
            raw_text = _strip_html(comment.get("comment_text", ""))
            if not raw_text:
                continue
            text_lower = raw_text.lower()
            if "remote" not in text_lower:
                continue
            if not _is_relevant_text(text_lower):
                continue

            first_line = raw_text.split("\n")[0]
            parts = [p.strip() for p in first_line.split("|")]
            company = parts[0] if parts else "Unknown"
            title = parts[1] if len(parts) > 1 else "See posting"

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
                "source": f"hn_hiring",
            })

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_excluded_location(job):
    location = (job.get("location") or "").lower()
    description = (job.get("description") or "").lower()
    combined = location + " " + description[:200]
    return any(phrase in combined for phrase in EXCLUDED_LOCATION_PHRASES)


def _is_relevant(title, description, tags):
    title = title.lower()
    description = description.lower()
    tags_str = " ".join(tags).lower() if isinstance(tags, list) else ""

    # A title match is strong signal — accept immediately
    if any(role in title for role in TARGET_ROLES):
        return True

    # A tag match is also strong
    if any(kw in tags_str for kw in KEYWORDS):
        return True

    # Description-only match requires at least 2 keyword hits to reduce noise
    hits = sum(1 for kw in KEYWORDS if kw in description)
    return hits >= 2


def _is_relevant_text(text_lower):
    # For free-text (HN posts), require at least 2 keyword hits
    hits = sum(1 for kw in KEYWORDS + TARGET_ROLES if kw in text_lower)
    return hits >= 2


def _strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = text.replace('&#x27;', "'").replace('&amp;', '&') \
               .replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    return re.sub(r'\s+', ' ', text).strip()


def _load_seen_urls():
    try:
        if SEEN_JOBS_FILE.exists():
            return set(json.loads(SEEN_JOBS_FILE.read_text()))
    except Exception:
        pass
    return set()


def _save_seen_urls(urls):
    try:
        SEEN_JOBS_FILE.parent.mkdir(exist_ok=True)
        SEEN_JOBS_FILE.write_text(json.dumps(list(urls)))
    except Exception:
        pass
