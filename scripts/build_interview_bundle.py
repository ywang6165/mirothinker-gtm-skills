#!/usr/bin/env python3
"""Build a portable interview bundle with clickable relative links and expanded GTM artifacts."""

from __future__ import annotations

import json
import os
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib import request, error

REPO_ROOT = Path(os.environ.get('MIRO_GTM_REPO_ROOT', Path(__file__).resolve().parents[1]))
AGENT_DIR = REPO_ROOT / 'output' / 'agent-team'
BUNDLE_DIR = REPO_ROOT / 'output' / 'interview-bundle'
ART_DIR = BUNDLE_DIR / 'artifacts'
EXT_DIR = REPO_ROOT / 'output' / 'agent-team-extended'
ENV_PATH = REPO_ROOT / '.env'


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def load_env(path: Path):
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()
    return env


def fetch_supabase_snapshot(env: dict):
    url = env.get('SUPABASE_URL', '').rstrip('/')
    key = env.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if not url or not key:
        return {'status': 'unavailable', 'reason': 'missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY'}

    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Accept': 'application/json',
    }

    # Count query
    count = None
    try:
        count_req = request.Request(
            f"{url}/rest/v1/leads?select=id&limit=1",
            headers={**headers, 'Prefer': 'count=exact'},
        )
        with request.urlopen(count_req, timeout=20) as resp:
            cr = resp.headers.get('Content-Range', '')
            if '/' in cr:
                count = int(cr.split('/')[-1])
    except Exception:
        count = None

    # Sample query
    sample = []
    columns = []
    try:
        sample_req = request.Request(
            f"{url}/rest/v1/leads?select=*&order=created_at.desc&limit=25",
            headers=headers,
        )
        with request.urlopen(sample_req, timeout=20) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
            sample = payload if isinstance(payload, list) else []
            if sample:
                columns = list(sample[0].keys())
    except error.HTTPError as exc:
        return {
            'status': 'error',
            'reason': f'HTTP {exc.code}',
            'count': count,
            'sample': [],
            'columns': [],
        }
    except Exception as exc:
        return {
            'status': 'error',
            'reason': str(exc),
            'count': count,
            'sample': [],
            'columns': [],
        }

    return {
        'status': 'ok',
        'fetched_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'count': count,
        'sample': sample,
        'columns': columns,
    }


def build_linkedin_sequences(accepted):
    out = []
    for lead in accepted[:10]:
        first = lead['name'].split(' ')[0] if lead['name'] else 'there'
        out.append({
            'lead_id': lead['lead_id'],
            'name': lead['name'],
            'company': lead['company'],
            'score': lead['score'],
            'connection_note': f"Hi {first} - saw your work at {lead['company']} around verification-heavy workflows.",
            'followup_1': f"Thanks for connecting, {first}. Curious how {lead['company']} currently validates high-stakes research outputs.",
            'followup_2': "If useful, I can share a 1-page pilot plan with measurable quality/turnaround criteria.",
        })
    return {
        'artifact': 'linkedin-outreach-sequences',
        'created_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'count': len(out),
        'sequences': out,
    }


def build_content_plan(accepted):
    themes = Counter()
    for lead in accepted:
        text = ' '.join(lead.get('reasons', []))
        if 'verification' in text:
            themes['Verification workflows'] += 1
        if 'risk' in text:
            themes['Risk governance in AI research'] += 1
        if 'compliance' in text:
            themes['Compliance-first AI operations'] += 1
        if 'research' in text:
            themes['Research traceability and auditability'] += 1
    if not themes:
        themes['Verification workflows'] = 1

    posts = []
    for i, (theme, _) in enumerate(themes.most_common(6), start=1):
        posts.append({
            'week': i,
            'theme': theme,
            'format': 'LinkedIn + Blog',
            'cta': 'Book a verification pilot',
            'proof_asset': 'Use accepted lead insights + QA-approved messaging snippets',
        })
    return {
        'artifact': 'content-campaign-plan',
        'created_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'posts': posts,
    }


def build_ads_matrix(icp):
    segments = icp.get('ideal_segments', [])[:4]
    tests = []
    for seg in segments:
        tests.append({
            'segment': seg,
            'pain_angle': 'Need defensible, auditable research output quality',
            'message_hypothesis': 'Verification-first workflow reduces review risk and rework',
            'channel': 'LinkedIn sponsored content',
            'success_metric': 'Qualified demo requests from target titles',
        })
    return {
        'artifact': 'ads-test-matrix',
        'created_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'tests': tests,
    }


def html_escape(s):
    return (str(s)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))


def generate_index(manager, db_snapshot):
    links = [
        'artifacts/01_icp_profile.json',
        'artifacts/02_signal_miner.json',
        'artifacts/03_lead_scoring.json',
        'artifacts/04_personalization_drafts.json',
        'artifacts/05_qa_review.json',
        'artifacts/06_manager_summary.json',
        'artifacts/07_blog_post_draft.md',
        'artifacts/08_linkedin_outreach_sequences.json',
        'artifacts/09_content_campaign_plan.json',
        'artifacts/10_ads_test_matrix.json',
        'artifacts/11_db_snapshot.json',
        'artifacts/00_source_leads.csv',
        'artifacts/mirothinker-gtm-full-walkthrough.html',
        'artifacts/mirothinker-workflow-drilldown.html',
        'artifacts/mirothinker-6-agent-report.html',
        'artifacts/extended_run_summary.json',
        'artifacts/extended_dependencies.json',
        'artifacts/mirothinker-12-agent-graph.html',
        'artifacts/mirothinker-agent-functional-map.html',
        'artifacts/mirothinker-step-by-step-execution.html',
        'artifacts/extended_07_oss_community_pipeline.json',
        'artifacts/extended_08_benchmark_watchdog.json',
        'artifacts/extended_09_reddit_intent_radar.json',
        'artifacts/extended_10_hn_trend_radar.json',
        'artifacts/extended_11_icp_enrichment_resolver.json',
        'artifacts/extended_12_competitive_intel_synthesizer.json',
    ]
    links_html = ''.join(f"<li><a href='{html_escape(p)}' target='_blank'>{html_escape(p)}</a></li>" for p in links)

    db_rows = ''
    if db_snapshot.get('status') == 'ok' and db_snapshot.get('sample'):
        cols = list(db_snapshot['sample'][0].keys())[:8]
        head = ''.join(f'<th>{html_escape(c)}</th>' for c in cols)
        body_rows = []
        for row in db_snapshot['sample'][:10]:
            body_rows.append('<tr>' + ''.join(f"<td>{html_escape(row.get(c,''))}</td>" for c in cols) + '</tr>')
        db_rows = f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
    else:
        db_rows = f"<p class='muted'>DB snapshot unavailable: {html_escape(db_snapshot.get('reason','unknown'))}</p>"

    return f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8' />
<meta name='viewport' content='width=device-width, initial-scale=1.0' />
<title>MiroThinker Interview Bundle</title>
<style>
body{{font-family:Inter,Arial,sans-serif;margin:0;background:#f5f7fb;color:#0f172a}}
.wrap{{max-width:1200px;margin:0 auto;padding:24px}}
.card{{background:#fff;border:1px solid #dbe3ef;border-radius:12px;padding:16px;margin-bottom:12px}}
.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}}
.k{{background:#fff;border:1px solid #dbe3ef;border-radius:10px;padding:10px}}
a{{color:#0f766e}} .muted{{color:#475569;font-size:13px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{border-bottom:1px solid #e2e8f0;padding:8px;text-align:left}}
th{{background:#0f172a;color:#fff}}
@media(max-width:900px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr));}}}}
</style>
</head>
<body>
<div class='wrap'>
  <div class='card'>
    <h1>MiroThinker GTM Interview Bundle (Shareable)</h1>
    <p class='muted'>All links below are relative and clickable for interviewers once this folder is hosted (or opened locally).</p>
    <p><strong>Run timestamp:</strong> {html_escape(manager.get('timestamp'))}</p>
  </div>

  <div class='grid'>
    <div class='k'><strong>Input leads</strong><div>{manager.get('lead_input_count')}</div></div>
    <div class='k'><strong>Accepted</strong><div>{manager.get('accepted_count')}</div></div>
    <div class='k'><strong>Rejected</strong><div>{manager.get('rejected_count')}</div></div>
    <div class='k'><strong>QA Approved</strong><div>{manager.get('qa_approved')}</div></div>
  </div>

  <div class='card'>
    <h2>Clickable Evidence Links</h2>
    <ul>{links_html}</ul>
  </div>

  <div class='card'>
    <h2>Database Snapshot (from Supabase)</h2>
    <p class='muted'>Status: {html_escape(db_snapshot.get('status'))} | Count: {html_escape(db_snapshot.get('count'))}</p>
    {db_rows}
  </div>

  <div class='card'>
    <h2>Share Instructions</h2>
    <ol>
      <li>Zip this folder: <code>{html_escape(str(BUNDLE_DIR))}</code></li>
      <li>Host it on any static host (Netlify drop, Vercel static, GitHub Pages).</li>
      <li>Send interviewers the hosted <code>index.html</code> URL.</li>
    </ol>
  </div>
</div>
</body>
</html>"""


def main():
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)

    # Copy core artifacts + reports
    copy_files = [
        '01_icp_profile.json',
        '02_signal_miner.json',
        '03_lead_scoring.json',
        '04_personalization_drafts.json',
        '05_qa_review.json',
        '06_manager_summary.json',
        '07_blog_post_draft.md',
        'mirothinker-6-agent-report.html',
        'mirothinker-workflow-drilldown.html',
        'mirothinker-gtm-full-walkthrough.html',
        'latest_run_stdout.json',
    ]
    for name in copy_files:
        src = AGENT_DIR / name
        if src.exists():
            shutil.copy2(src, ART_DIR / name)

    manager = read_json(AGENT_DIR / '06_manager_summary.json')
    scored = read_json(AGENT_DIR / '03_lead_scoring.json')
    icp = read_json(AGENT_DIR / '01_icp_profile.json')

    source_csv = Path(manager.get('source_csv', ''))
    if source_csv and not source_csv.is_absolute():
        source_csv = REPO_ROOT / source_csv
    if source_csv.exists():
        shutil.copy2(source_csv, ART_DIR / '00_source_leads.csv')

    # Generate expanded non-email artifacts
    linkedin = build_linkedin_sequences(scored.get('accepted', []))
    content = build_content_plan(scored.get('accepted', []))
    ads = build_ads_matrix(icp)

    (ART_DIR / '08_linkedin_outreach_sequences.json').write_text(json.dumps(linkedin, indent=2), encoding='utf-8')
    (ART_DIR / '09_content_campaign_plan.json').write_text(json.dumps(content, indent=2), encoding='utf-8')
    (ART_DIR / '10_ads_test_matrix.json').write_text(json.dumps(ads, indent=2), encoding='utf-8')

    env = load_env(ENV_PATH)
    db_snapshot = fetch_supabase_snapshot(env)
    (ART_DIR / '11_db_snapshot.json').write_text(json.dumps(db_snapshot, indent=2), encoding='utf-8')
    index_html = generate_index(manager, db_snapshot)


    # Copy extended 12-agent artifacts when available
    extended_map = {
        'run_summary.json': 'extended_run_summary.json',
        'dependencies.json': 'extended_dependencies.json',
        'mirothinker-12-agent-graph.html': 'mirothinker-12-agent-graph.html',
        'mirothinker-agent-functional-map.html': 'mirothinker-agent-functional-map.html',
        'mirothinker-step-by-step-execution.html': 'mirothinker-step-by-step-execution.html',
        '07_oss_community_pipeline.json': 'extended_07_oss_community_pipeline.json',
        '08_benchmark_watchdog.json': 'extended_08_benchmark_watchdog.json',
        '09_reddit_intent_radar.json': 'extended_09_reddit_intent_radar.json',
        '10_hn_trend_radar.json': 'extended_10_hn_trend_radar.json',
        '11_icp_enrichment_resolver.json': 'extended_11_icp_enrichment_resolver.json',
        '12_competitive_intel_synthesizer.json': 'extended_12_competitive_intel_synthesizer.json',
    }
    for src_name, dst_name in extended_map.items():
        src = EXT_DIR / src_name
        if src.exists():
            shutil.copy2(src, ART_DIR / dst_name)

    (BUNDLE_DIR / 'index.html').write_text(index_html, encoding='utf-8')

    print(json.dumps({
        'bundle_dir': str(BUNDLE_DIR),
        'index': str(BUNDLE_DIR / 'index.html'),
        'db_status': db_snapshot.get('status'),
        'db_count': db_snapshot.get('count'),
    }, indent=2))


if __name__ == '__main__':
    main()
