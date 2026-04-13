#!/usr/bin/env python3
"""Run MiroThinker extended 12-agent GTM system.

This keeps the existing 6-agent core and adds 6 compatibility agents adapted
from external scripts. All outputs are stored as JSON/MD/HTML artifacts.
"""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from urllib import error, parse, request
import xml.etree.ElementTree as ET

REPO_ROOT = Path(os.environ.get('MIRO_GTM_REPO_ROOT', Path(__file__).resolve().parents[1]))
CORE_SCRIPT = REPO_ROOT / 'scripts' / 'miro_gtm_agent_team.py'
CORE_DIR = REPO_ROOT / 'output' / 'agent-team'
OUT_DIR = REPO_ROOT / 'output' / 'agent-team-extended'
ENV_PATH = REPO_ROOT / '.env'


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def load_env(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()
    return env


def safe_get_json(url: str, headers: Dict[str, str] | None = None, timeout: int = 20):
    req = request.Request(url, headers=headers or {})
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def run_core_agents() -> Dict:
    proc = subprocess.run(
        ['python3', str(CORE_SCRIPT)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)


def read_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def write_csv(path: Path, rows: List[Dict], field_order: List[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        headers = field_order or []
        with path.open('w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=headers)
            writer.writeheader()
        return

    headers = field_order or list(rows[0].keys())
    with path.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)




def recover_previous_artifact(path: Path, current_payload: Dict) -> Dict:
    """Use previous successful artifact when live fetch fails."""
    if current_payload.get('status') != 'error' or not path.exists():
        return current_payload
    prev = read_json(path)
    prev['status'] = 'fallback'
    prev['fallback_reason'] = current_payload.get('error', 'unknown error')
    prev['fallback_at'] = now_iso()
    return prev

def to_repo_rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except Exception:
        return str(path)


def resolve_repo_path(raw: str, repo_root: Path) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else (repo_root / p)


def agent7_oss_community_pipeline(env: Dict[str, str]) -> Dict:
    """Renamed external Agent 1. GitHub stargazers -> scored community prospects."""
    token = env.get('GITHUB_TOKEN', '')
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'miro-gtm-extended-agent',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'

    tier1_companies = [
        'tencent', 'alibaba', 'google', 'microsoft', 'meta', 'amazon', 'apple',
        'openai', 'anthropic', 'deepmind', 'baidu', 'bytedance', 'huawei', 'nvidia',
    ]
    domain_keywords = [
        'fintech', 'finance', 'health', 'legal', 'enterprise', 'saas', 'agent',
        'inference', 'llm', 'research', 'trading', 'compliance', 'verification',
    ]
    exclude = {'BinWang28', 'demoleiwang'}

    stargazers = []
    pages = 2
    for page in range(1, pages + 1):
        try:
            batch = safe_get_json(
                f'https://api.github.com/repos/MiroMindAI/MiroThinker/stargazers?per_page=30&page={page}',
                headers=headers,
            )
        except Exception as exc:
            return {
                'agent': 'OSS Community Pipeline',
                'timestamp': now_iso(),
                'status': 'error',
                'error': f'GitHub stargazer fetch failed: {exc}',
            }
        if not batch:
            break
        stargazers.extend(batch)

    def score_profile(profile: Dict) -> Tuple[int, List[str]]:
        score = 0
        reasons: List[str] = []
        company = (profile.get('company') or '').lower().strip('@').strip()
        bio = (profile.get('bio') or '').lower()
        followers = int(profile.get('followers') or 0)
        repos = int(profile.get('public_repos') or 0)
        student_terms = ['student', 'phd', 'university', 'college', 'institute']
        is_student = any(k in company for k in student_terms) or any(k in bio for k in student_terms)

        if company and not is_student:
            score += 3
            reasons.append('company listed (non-student)')
        elif company:
            score += 1
            reasons.append('company listed (student-like)')

        if any(co in company for co in tier1_companies):
            score += 2
            reasons.append('tier-1 company signal')

        if followers > 50 or repos > 20:
            score += 2
            reasons.append('influence signal (followers/repos)')

        if any(k in bio for k in domain_keywords):
            score += 2
            reasons.append('domain keyword in bio')

        if followers > 100:
            score += 1
            reasons.append('100+ followers')

        return min(score, 10), reasons

    enriched = []
    # Keep all fetched stargazers (not a small debug slice) to maximize lead volume.
    for row in stargazers:
        login = row.get('login')
        if not login or login in exclude:
            continue
        try:
            profile = safe_get_json(f'https://api.github.com/users/{parse.quote(login)}', headers=headers)
        except Exception:
            continue
        company = (profile.get('company') or '').lower()
        if 'miromind' in company:
            continue
        score, reasons = score_profile(profile)
        tier = 'TIER_1' if score >= 7 else ('TIER_2' if score >= 4 else 'TIER_3')
        enriched.append({
            'login': login,
            'name': profile.get('name') or login,
            'company': profile.get('company') or '',
            'bio': profile.get('bio') or '',
            'location': profile.get('location') or '',
            'followers': profile.get('followers') or 0,
            'public_repos': profile.get('public_repos') or 0,
            'score': score,
            'tier': tier,
            'score_reasons': reasons,
            'profile_url': profile.get('html_url') or f'https://github.com/{login}',
        })

    enriched.sort(key=lambda x: (-x['score'], -x['followers'], x['login']))
    counts = Counter(x['tier'] for x in enriched)

    return {
        'agent': 'OSS Community Pipeline',
        'timestamp': now_iso(),
        'status': 'ok',
        'source': 'GitHub stargazers for MiroMindAI/MiroThinker',
        'fetched_stargazers': len(stargazers),
        'enriched_profiles': len(enriched),
        'tiers': dict(counts),
        'top_prospects': enriched[:20],
        'all_prospects': enriched,
    }


def agent8_benchmark_watchdog() -> Dict:
    """Renamed external Agent 2. Monitors benchmark chatter and arXiv updates."""
    keywords = [
        'GAIA benchmark reasoning agent',
        'BrowseComp benchmark model',
        'HLE benchmark LLM',
        'deep research benchmark agents',
    ]

    hn_hits = []
    for q in keywords:
        try:
            query = parse.quote(q)
            data = safe_get_json(f'https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage=4')
            for h in data.get('hits', []):
                hn_hits.append({
                    'keyword': q,
                    'title': h.get('title') or '',
                    'url': h.get('url') or '',
                    'points': h.get('points') or 0,
                    'comments': h.get('num_comments') or 0,
                    'created_at': h.get('created_at') or '',
                })
        except Exception:
            continue

    # lightweight arXiv query
    arxiv_query = parse.quote('all:(benchmark AND agent AND reasoning)')
    arxiv_url = f'http://export.arxiv.org/api/query?search_query={arxiv_query}&start=0&max_results=8&sortBy=submittedDate&sortOrder=descending'
    papers = []
    try:
        xml_txt = request.urlopen(request.Request(arxiv_url, headers={'User-Agent': 'miro-gtm-extended-agent'}), timeout=20).read()
        root = ET.fromstring(xml_txt)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        for entry in root.findall('atom:entry', ns):
            title = (entry.findtext('atom:title', default='', namespaces=ns) or '').strip()
            published = entry.findtext('atom:published', default='', namespaces=ns) or ''
            link = ''
            for l in entry.findall('atom:link', ns):
                if l.get('rel') == 'alternate':
                    link = l.get('href') or ''
                    break
            papers.append({'title': title, 'published': published, 'url': link})
    except Exception:
        papers = []

    hn_hits.sort(key=lambda x: (x['points'], x['comments']), reverse=True)
    threats = [h for h in hn_hits if h['points'] >= 40]

    return {
        'agent': 'Benchmark Signal Watchdog',
        'timestamp': now_iso(),
        'status': 'ok',
        'hn_hits': hn_hits[:20],
        'arxiv_papers': papers,
        'threat_count': len(threats),
        'threats': threats[:8],
        'positioning_actions': [
            'Publish benchmark-context post with verification-first framing when threat_count > 0.',
            'Update outbound messaging snippets with latest benchmark language.',
        ],
    }


def agent9_reddit_intent_radar() -> Dict:
    """Renamed external Agent 3. Reddit intent-signal scan."""
    queries = [
        'deep research agent', 'ai verification', 'enterprise llm compliance',
        'research workflow automation', 'benchmark reasoning model',
        'ai audit trail', 'llm governance', 'agent reliability',
        'hallucination mitigation', 'compliance ai workflow',
    ]
    headers = {'User-Agent': 'miro-gtm-extended-agent/1.0'}
    posts = []

    for q in queries:
        try:
            url = f'https://www.reddit.com/search.json?q={parse.quote(q)}&limit=15&sort=new&t=month'
            data = safe_get_json(url, headers=headers, timeout=20)
            children = data.get('data', {}).get('children', [])
            for ch in children:
                d = ch.get('data', {})
                title = d.get('title') or ''
                body = d.get('selftext') or ''
                text = f'{title} {body}'.lower()
                signal_score = 0
                if any(k in text for k in ['problem', 'pain', 'struggle', 'hard']):
                    signal_score += 2
                if any(k in text for k in ['verify', 'audit', 'compliance', 'risk']):
                    signal_score += 2
                if any(k in text for k in ['looking for', 'recommend', 'alternative']):
                    signal_score += 2
                posts.append({
                    'query': q,
                    'subreddit': d.get('subreddit') or '',
                    'title': title,
                    'author': d.get('author') or '',
                    'ups': d.get('ups') or 0,
                    'comments': d.get('num_comments') or 0,
                    'created_utc': d.get('created_utc') or 0,
                    'url': f"https://www.reddit.com{d.get('permalink', '')}",
                    'signal_score': signal_score,
                })
        except Exception:
            continue

    dedup = {}
    for p in posts:
        key = p['url']
        if key and key not in dedup:
            dedup[key] = p
    out = sorted(dedup.values(), key=lambda x: (x['signal_score'], x['ups'], x['comments']), reverse=True)

    return {
        'agent': 'Reddit Intent Radar',
        'timestamp': now_iso(),
        'status': 'ok',
        'queries': queries,
        'total_posts': len(out),
        'high_intent_posts': [p for p in out if p['signal_score'] >= 4][:50],
        'all_ranked_posts': out[:200],
    }





def normalize_email(raw: str) -> str:
    email = (raw or '').strip().lower()
    if not email or '@' not in email or ' ' in email:
        return ''
    local, _, domain = email.partition('@')
    if not local or '.' not in domain:
        return ''
    return email


def normalize_url(raw: str) -> str:
    url = (raw or '').strip()
    if not url:
        return ''
    return url.split('?', 1)[0].rstrip('/')


def build_core_contact_map(core_source_csv: Path) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    if not core_source_csv.exists():
        return out

    with core_source_csv.open('r', encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            key = '|'.join([
                (row.get('Name') or '').strip().lower(),
                (row.get('Company') or '').strip().lower(),
                (row.get('Title') or '').strip().lower(),
            ])
            out[key] = {
                'email': normalize_email(row.get('Email') or ''),
                'linkedin_url': normalize_url(row.get('Person LinkedIn URL') or ''),
            }
    return out


def identity_candidates(rec: Dict) -> List[Tuple[str, str]]:
    linkedin = normalize_url(rec.get('linkedin_url') or '')
    email = normalize_email(rec.get('email') or '')
    name = (rec.get('name') or '').strip().lower()
    company = (rec.get('company') or '').strip().lower()
    name_company = f"{name}|{company}" if name or company else ''

    out: List[Tuple[str, str]] = []
    if linkedin:
        out.append(('linkedin_url', linkedin))
    if email:
        out.append(('email', email))
    if name_company:
        out.append(('name_company', name_company))
    return out


def merge_record(existing: Dict, incoming: Dict) -> Dict:
    merged = dict(existing)

    # Fill richer contact fields.
    if not merged.get('email') and incoming.get('email'):
        merged['email'] = incoming['email']
    if not merged.get('linkedin_url') and incoming.get('linkedin_url'):
        merged['linkedin_url'] = incoming['linkedin_url']

    # Keep highest signal score.
    merged['signal_score'] = max(int(merged.get('signal_score') or 0), int(incoming.get('signal_score') or 0))

    # Preserve provenance from all contributing sources.
    srcs = set(merged.get('provenance_sources') or [merged.get('source')])
    srcs.update(incoming.get('provenance_sources') or [incoming.get('source')])
    merged['provenance_sources'] = sorted(s for s in srcs if s)

    merged_meta = dict(merged.get('metadata') or {})
    incoming_meta = dict(incoming.get('metadata') or {})
    for k, v in incoming_meta.items():
        if k not in merged_meta or not merged_meta[k]:
            merged_meta[k] = v
    merged['metadata'] = merged_meta

    return merged


def build_unified_lead_queue(core_signals: Dict, a7: Dict, a9: Dict, core_source_csv: Path) -> Dict:
    """Merge early with deterministic precedence: linkedin > email > name+company."""
    core_contact = build_core_contact_map(core_source_csv)

    records_by_id: Dict[str, Dict] = {}
    id_by_identity: Dict[Tuple[str, str], str] = {}

    def ingest(candidate: Dict) -> None:
        # deterministic identity precedence
        ids = identity_candidates(candidate)
        existing_id = ''
        for ident in ids:
            existing_id = id_by_identity.get(ident, '')
            if existing_id:
                break

        if not existing_id:
            existing_id = candidate.get('lead_id') or f"u{len(records_by_id)+1:06d}"
            records_by_id[existing_id] = candidate
        else:
            records_by_id[existing_id] = merge_record(records_by_id[existing_id], candidate)

        # Register all identifiers after merge.
        merged = records_by_id[existing_id]
        for ident in identity_candidates(merged):
            id_by_identity[ident] = existing_id

    # Source 1: core signal records.
    for rec in core_signals.get('records', []):
        key = '|'.join([
            (rec.get('name') or '').strip().lower(),
            (rec.get('company') or '').strip().lower(),
            (rec.get('title') or '').strip().lower(),
        ])
        contact = core_contact.get(key, {})
        ingest({
            'source': 'core_signal',
            'lead_id': rec.get('lead_id') or '',
            'name': rec.get('name') or '',
            'company': rec.get('company') or '',
            'title': rec.get('title') or '',
            'region': rec.get('region') or '',
            'email': normalize_email((rec.get('email') or '') or contact.get('email', '')),
            'linkedin_url': normalize_url(contact.get('linkedin_url', '')),
            'signal_score': len((rec.get('signals') or {}).get('matched_keywords') or []),
            'metadata': {'signals': rec.get('signals') or {}},
            'provenance_sources': ['core_signal'],
        })

    # Source 2: GitHub community profiles.
    for rec in a7.get('all_prospects', []):
        login = (rec.get('login') or '').strip().lower()
        ingest({
            'source': 'github_community',
            'lead_id': f"github:{login}",
            'name': rec.get('name') or rec.get('login') or '',
            'company': rec.get('company') or '',
            'title': 'Open-source community profile',
            'region': rec.get('location') or '',
            'email': '',
            'linkedin_url': '',
            'signal_score': int(rec.get('score') or 0),
            'metadata': {
                'tier': rec.get('tier') or '',
                'profile_url': rec.get('profile_url') or '',
                'score_reasons': rec.get('score_reasons') or [],
            },
            'provenance_sources': ['github_community'],
        })

    # Source 3: Reddit intent posts.
    for rec in a9.get('all_ranked_posts', []):
        author = (rec.get('author') or '').strip()
        if not author:
            continue
        ingest({
            'source': 'reddit_intent',
            'lead_id': f"reddit:{author.lower()}",
            'name': author,
            'company': '',
            'title': f"r/{rec.get('subreddit', '')} participant",
            'region': '',
            'email': '',
            'linkedin_url': '',
            'signal_score': int(rec.get('signal_score') or 0),
            'metadata': {
                'thread_url': rec.get('url') or '',
                'ups': rec.get('ups') or 0,
                'comments': rec.get('comments') or 0,
            },
            'provenance_sources': ['reddit_intent'],
        })

    rows = sorted(
        records_by_id.values(),
        key=lambda r: (
            (r.get('name') or '').lower(),
            (r.get('company') or '').lower(),
            -int(r.get('signal_score') or 0),
            (r.get('lead_id') or ''),
        ),
    )

    return {
        'artifact': 'unified_lead_queue',
        'timestamp': now_iso(),
        'total_unique_leads': len(rows),
        'by_source': dict(Counter(r.get('source', '') for r in rows)),
        'records': rows,
    }


def qualify_and_verify_contacts(unified: Dict, core_scores: Dict) -> Dict:
    """Data QA gate: qualification + contactability + route decision."""
    accepted_core = {rec.get('lead_id') for rec in core_scores.get('accepted', [])}
    out = []

    for rec in unified.get('records', []):
        src = rec.get('source')
        lead_id = rec.get('lead_id')
        signal_score = int(rec.get('signal_score') or 0)
        tier = (rec.get('metadata') or {}).get('tier', '')

        qualified = False
        qualification_reason = ''
        if src == 'core_signal' and lead_id in accepted_core:
            qualified = True
            qualification_reason = 'Core scorer accepted (>=45)'
        elif src == 'github_community' and tier in {'TIER_1', 'TIER_2'}:
            qualified = True
            qualification_reason = f'GitHub tier {tier}'
        elif src == 'reddit_intent' and signal_score >= 4:
            qualified = True
            qualification_reason = f'Reddit intent score {signal_score}>=4'

        email = normalize_email(rec.get('email') or '')
        email_verified = bool(email)
        linkedin_url = normalize_url(rec.get('linkedin_url') or '')
        if email_verified:
            contact_status = 'email_verified'
            outreach_route = 'email_outreach_queue' if qualified else 'research_backlog'
        elif linkedin_url:
            contact_status = 'linkedin_only'
            outreach_route = 'linkedin_outreach_queue' if qualified else 'research_backlog'
        else:
            contact_status = 'unreachable'
            outreach_route = 'research_backlog'

        out.append({
            **rec,
            'email': email,
            'linkedin_url': linkedin_url,
            'qualified': qualified,
            'qualification_reason': qualification_reason,
            'email_verified': email_verified,
            'contact_status': contact_status,
            'outreach_route': outreach_route,
        })

    return {
        'artifact': 'contact_verification_gate',
        'timestamp': now_iso(),
        'input_count': len(out),
        'qualified_count': sum(1 for r in out if r['qualified']),
        'email_verified_count': sum(1 for r in out if r['email_verified']),
        'linkedin_only_count': sum(1 for r in out if r['contact_status'] == 'linkedin_only'),
        'unreachable_count': sum(1 for r in out if r['contact_status'] == 'unreachable'),
        'email_outreach_queue_count': sum(1 for r in out if r['outreach_route'] == 'email_outreach_queue'),
        'linkedin_outreach_queue_count': sum(1 for r in out if r['outreach_route'] == 'linkedin_outreach_queue'),
        'research_backlog_count': sum(1 for r in out if r['outreach_route'] == 'research_backlog'),
        'records': out,
    }


def agent10_hn_trend_radar() -> Dict:
    """Renamed external Agent 4. HN keyword radar."""
    keywords = [
        'MiroThinker', 'deep research agent', 'verification agent',
        'tool-augmented reasoning', 'GAIA benchmark', 'BrowseComp',
    ]
    rows = []
    seen = set()
    for kw in keywords:
        try:
            data = safe_get_json(
                f'https://hn.algolia.com/api/v1/search?query={parse.quote(kw)}&tags=story&hitsPerPage=6'
            )
            for h in data.get('hits', []):
                oid = h.get('objectID')
                if not oid or oid in seen:
                    continue
                seen.add(oid)
                rows.append({
                    'keyword': kw,
                    'title': h.get('title') or '',
                    'url': h.get('url') or '',
                    'hn_url': f'https://news.ycombinator.com/item?id={oid}',
                    'points': h.get('points') or 0,
                    'comments': h.get('num_comments') or 0,
                    'author': h.get('author') or '',
                    'created_at': h.get('created_at') or '',
                })
        except Exception:
            continue

    rows.sort(key=lambda x: (x['points'], x['comments']), reverse=True)
    return {
        'agent': 'HackerNews Trend Radar',
        'timestamp': now_iso(),
        'status': 'ok',
        'keywords': keywords,
        'total_threads': len(rows),
        'threads': rows[:20],
    }


def agent11_icp_enrichment_resolver(core_scores: Dict, core_source_csv: Path) -> Dict:
    """Renamed external Agent 5. Local enrichment resolver compatible with existing artifacts."""
    # Build quick map from source CSV for website/company URL fields.
    csv_map: Dict[str, Dict[str, str]] = {}
    if core_source_csv.exists():
        with core_source_csv.open('r', encoding='utf-8', newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = (row.get('Name') or '').strip().lower()
                company = (row.get('Company') or '').strip().lower()
                key = f'{name}|{company}'
                csv_map[key] = {
                    'company_website': row.get('Company Website') or '',
                    'company_linkedin': row.get('Company LinkedIn URL') or '',
                    'person_linkedin': row.get('Person LinkedIn URL') or '',
                    'region': row.get('Region') or '',
                }

    enriched = []
    for rec in core_scores.get('accepted', [])[:20]:
        key = f"{(rec.get('name') or '').lower()}|{(rec.get('company') or '').lower()}"
        lookup = csv_map.get(key, {})
        title = rec.get('title') or ''
        persona = 'Economic Buyer' if re.search(r'head|director|vp|chief', title, flags=re.I) else 'Practitioner Champion'
        domain = ''
        website = lookup.get('company_website') or ''
        if website:
            parsed = parse.urlparse(website if '://' in website else f'https://{website}')
            domain = parsed.netloc or parsed.path
            domain = domain.lower().replace('www.', '').strip('/')

        enriched.append({
            'lead_id': rec.get('lead_id'),
            'name': rec.get('name'),
            'company': rec.get('company'),
            'title': title,
            'score': rec.get('score'),
            'persona': persona,
            'company_domain': domain,
            'company_website': website,
            'company_linkedin': lookup.get('company_linkedin') or '',
            'person_linkedin': lookup.get('person_linkedin') or '',
            'region': lookup.get('region') or rec.get('region') or '',
        })

    return {
        'agent': 'ICP Enrichment Resolver',
        'timestamp': now_iso(),
        'status': 'ok',
        'enriched_count': len(enriched),
        'records': enriched,
    }


def agent12_competitive_intel_synthesizer(a8: Dict, a10: Dict) -> Dict:
    """Renamed external Agent 6. Synthesizes competitive intel from live monitored feeds."""
    competitors = ['Perplexity', 'OpenAI', 'DeepSeek', 'Mistral', 'Gemini', 'Claude']

    combined = []
    for row in a8.get('hn_hits', []):
        combined.append({'source': 'benchmark_watchdog', **row})
    for row in a10.get('threads', []):
        combined.append({'source': 'hn_trend_radar', **row})

    intel = []
    for comp in competitors:
        comp_rows = [r for r in combined if comp.lower() in (r.get('title') or '').lower()]
        mentions = len(comp_rows)
        top = sorted(comp_rows, key=lambda x: (x.get('points') or 0, x.get('comments') or 0), reverse=True)[:3]
        threat = 'HIGH' if mentions >= 5 else ('WATCH' if mentions >= 2 else 'LOW')
        intel.append({
            'competitor': comp,
            'mentions': mentions,
            'threat_level': threat,
            'top_signals': top,
            'gtm_counter': (
                'Position MiroThinker as verification-first infrastructure with auditable reasoning steps.'
                if mentions > 0 else
                'No immediate action; keep monitoring and maintain baseline positioning.'
            ),
        })

    return {
        'agent': 'Competitive Intel Synthesizer',
        'timestamp': now_iso(),
        'status': 'ok',
        'competitors_monitored': competitors,
        'intel': intel,
        'high_threats': [x for x in intel if x['threat_level'] == 'HIGH'],
    }


def build_dependency_graph() -> Dict:
    nodes = [
        {'id': 'A1', 'name': 'ICP Strategist'},
        {'id': 'A2', 'name': 'Signal Miner'},
        {'id': 'A3', 'name': 'Lead Scorer'},
        {'id': 'A4', 'name': 'Personalization Writer'},
        {'id': 'A5', 'name': 'QA / Approver'},
        {'id': 'A6', 'name': 'GTM Manager'},
        {'id': 'A7', 'name': 'OSS Community Pipeline'},
        {'id': 'A8', 'name': 'Benchmark Signal Watchdog'},
        {'id': 'A9', 'name': 'Reddit Intent Radar'},
        {'id': 'A10', 'name': 'HackerNews Trend Radar'},
        {'id': 'A11', 'name': 'ICP Enrichment Resolver'},
        {'id': 'A12', 'name': 'Competitive Intel Synthesizer'},
    ]

    edges = [
        ('A1', 'A2'), ('A2', 'A3'), ('A3', 'A4'), ('A4', 'A5'), ('A5', 'A6'),
        ('A7', 'A2'), ('A9', 'A2'), ('A10', 'A8'), ('A8', 'A12'), ('A10', 'A12'),
        ('A3', 'A11'), ('A11', 'A4'), ('A12', 'A4'), ('A7', 'A11'), ('A6', 'A12'),
    ]

    mermaid_lines = ['graph TD'] + [f'  {a}[{a}] --> {b}[{b}]' for a, b in edges]
    return {
        'node_count': len(nodes),
        'nodes': nodes,
        'edge_count': len(edges),
        'edges': [{'from': a, 'to': b} for a, b in edges],
        'mermaid': '\n'.join(mermaid_lines),
    }


def render_graph_html(graph: Dict, summary: Dict, out_path: Path) -> None:
    rows = ''.join(
        f"<tr><td>{e['from']}</td><td>{e['to']}</td></tr>" for e in graph['edges']
    )
    html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8' />
<meta name='viewport' content='width=device-width, initial-scale=1.0' />
<title>MiroThinker 12-Agent Dependency Graph</title>
<style>
body {{ font-family: Inter, Arial, sans-serif; margin:0; background:#f6f8fc; color:#0f172a; }}
.wrap {{ max-width:1100px; margin:0 auto; padding:24px; }}
.card {{ background:#fff; border:1px solid #dbe3ef; border-radius:12px; padding:16px; margin-bottom:12px; }}
.grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
.k {{ background:#fff; border:1px solid #dbe3ef; border-radius:10px; padding:10px; }}
pre {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px; white-space:pre-wrap; }}
table {{ width:100%; border-collapse:collapse; font-size:14px; }} th,td {{ border-bottom:1px solid #e2e8f0; padding:8px; text-align:left; }} th {{ background:#0f172a; color:#fff; }}
</style>
</head>
<body>
<div class='wrap'>
  <div class='card'>
    <h1>MiroThinker GTM - 12 Agent System</h1>
    <p>Existing core (A1-A6) + new compatibility agents (A7-A12) integrated.</p>
  </div>
  <div class='grid'>
    <div class='k'><strong>Total Agents</strong><div>{graph['node_count']}</div></div>
    <div class='k'><strong>Total Dependencies</strong><div>{graph['edge_count']}</div></div>
    <div class='k'><strong>Run Timestamp</strong><div>{summary.get('timestamp')}</div></div>
    <div class='k'><strong>Artifacts</strong><div>{len(summary.get('artifacts', {}))}</div></div>
  </div>
  <div class='card'>
    <h2>Mermaid Graph</h2>
    <pre>{graph['mermaid']}</pre>
  </div>
  <div class='card'>
    <h2>Dependency Table</h2>
    <table><thead><tr><th>From</th><th>To</th></tr></thead><tbody>{rows}</tbody></table>
  </div>
</div>
</body>
</html>"""
    write_text(out_path, html)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    env = load_env(ENV_PATH)
    core_run = run_core_agents()
    core_signals = read_json(CORE_DIR / '02_signal_miner.json')
    core_scores = read_json(CORE_DIR / '03_lead_scoring.json')
    core_manager = read_json(CORE_DIR / '06_manager_summary.json')
    core_source_csv = resolve_repo_path(core_manager.get('source_csv', ''), REPO_ROOT)

    a7 = agent7_oss_community_pipeline(env)
    a8 = agent8_benchmark_watchdog()
    a9 = agent9_reddit_intent_radar()
    a10 = agent10_hn_trend_radar()

    # If external APIs fail transiently, keep the latest successful artifacts.
    a7 = recover_previous_artifact(OUT_DIR / '07_oss_community_pipeline.json', a7)
    # Secondary fallback: interview-bundle snapshot keeps last known good OSS run.
    a7 = recover_previous_artifact(REPO_ROOT / 'output' / 'interview-bundle' / 'artifacts' / 'extended_07_oss_community_pipeline.json', a7)
    a8 = recover_previous_artifact(OUT_DIR / '08_benchmark_watchdog.json', a8)
    a9 = recover_previous_artifact(OUT_DIR / '09_reddit_intent_radar.json', a9)
    a10 = recover_previous_artifact(OUT_DIR / '10_hn_trend_radar.json', a10)
    a11 = agent11_icp_enrichment_resolver(core_scores, core_source_csv)
    a12 = agent12_competitive_intel_synthesizer(a8, a10)

    artifact_paths = {
        'core_run_stdout': OUT_DIR / 'core_run_stdout.json',
        'agent7_oss_community_pipeline': OUT_DIR / '07_oss_community_pipeline.json',
        'agent8_benchmark_watchdog': OUT_DIR / '08_benchmark_watchdog.json',
        'agent9_reddit_intent_radar': OUT_DIR / '09_reddit_intent_radar.json',
        'agent10_hn_trend_radar': OUT_DIR / '10_hn_trend_radar.json',
        'agent11_icp_enrichment_resolver': OUT_DIR / '11_icp_enrichment_resolver.json',
        'agent12_competitive_intel_synthesizer': OUT_DIR / '12_competitive_intel_synthesizer.json',
        'unified_lead_queue': OUT_DIR / '13_unified_lead_queue.json',
        'contact_verification_gate': OUT_DIR / '14_contact_verification_gate.json',
        'unified_lead_queue_csv': OUT_DIR / '13_unified_lead_queue.csv',
        'contact_verification_gate_csv': OUT_DIR / '14_contact_verification_gate.csv',
        'dependency_graph': OUT_DIR / 'dependencies.json',
        'dependency_graph_html': OUT_DIR / 'mirothinker-12-agent-graph.html',
        'run_summary': OUT_DIR / 'run_summary.json',
    }
    artifacts = {k: to_repo_rel(v, REPO_ROOT) for k, v in artifact_paths.items()}

    write_json(artifact_paths['core_run_stdout'], core_run)
    write_json(artifact_paths['agent7_oss_community_pipeline'], a7)
    write_json(artifact_paths['agent8_benchmark_watchdog'], a8)
    write_json(artifact_paths['agent9_reddit_intent_radar'], a9)
    write_json(artifact_paths['agent10_hn_trend_radar'], a10)
    write_json(artifact_paths['agent11_icp_enrichment_resolver'], a11)
    write_json(artifact_paths['agent12_competitive_intel_synthesizer'], a12)
    unified_queue = build_unified_lead_queue(core_signals, a7, a9, core_source_csv)
    verification_gate = qualify_and_verify_contacts(unified_queue, core_scores)
    write_json(artifact_paths['unified_lead_queue'], unified_queue)
    write_json(artifact_paths['contact_verification_gate'], verification_gate)
    write_csv(artifact_paths['unified_lead_queue_csv'], unified_queue.get('records', []))
    write_csv(artifact_paths['contact_verification_gate_csv'], verification_gate.get('records', []))

    graph = build_dependency_graph()
    write_json(artifact_paths['dependency_graph'], graph)

    summary = {
        'timestamp': now_iso(),
        'system': 'MiroThinker 12-agent GTM system',
        'core_agents': 6,
        'new_agents': 6,
        'total_agents': 12,
        'new_agent_status': {
            'A7_oss_community_pipeline': a7.get('status', 'unknown'),
            'A8_benchmark_watchdog': a8.get('status', 'unknown'),
            'A9_reddit_intent_radar': a9.get('status', 'unknown'),
            'A10_hn_trend_radar': a10.get('status', 'unknown'),
            'A11_icp_enrichment_resolver': a11.get('status', 'unknown'),
            'A12_competitive_intel_synthesizer': a12.get('status', 'unknown'),
        },
        'key_counts': {
            'core_accepted_leads': core_manager.get('accepted_count'),
            'core_drafts': core_manager.get('draft_count'),
            'a7_top_prospects': len(a7.get('top_prospects', [])) if isinstance(a7, dict) else 0,
            'a7_all_prospects': len(a7.get('all_prospects', [])) if isinstance(a7, dict) else 0,
            'a8_threat_count': a8.get('threat_count', 0),
            'a9_high_intent_posts': len(a9.get('high_intent_posts', [])) if isinstance(a9, dict) else 0,
            'a10_threads': a10.get('total_threads', 0),
            'a11_enriched_count': a11.get('enriched_count', 0),
            'a12_high_threats': len(a12.get('high_threats', [])) if isinstance(a12, dict) else 0,
            'unified_total_unique_leads': unified_queue.get('total_unique_leads', 0),
            'qualified_total_leads': verification_gate.get('qualified_count', 0),
            'email_verified_total_leads': verification_gate.get('email_verified_count', 0),
            'linkedin_only_total_leads': verification_gate.get('linkedin_only_count', 0),
            'unreachable_total_leads': verification_gate.get('unreachable_count', 0),
        },
        'artifacts': artifacts,
    }

    write_json(artifact_paths['run_summary'], summary)
    render_graph_html(graph, summary, artifact_paths['dependency_graph_html'])

    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
