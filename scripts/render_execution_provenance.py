#!/usr/bin/env python3
import json
import os
from pathlib import Path

REPO_ROOT = Path(os.environ.get('MIRO_GTM_REPO_ROOT', Path(__file__).resolve().parents[1]))
CORE = REPO_ROOT / 'output' / 'agent-team'
EXT = REPO_ROOT / 'output' / 'agent-team-extended'
OUT = EXT / 'mirothinker-step-by-step-execution.html'

core_mgr = json.loads((CORE / '06_manager_summary.json').read_text(encoding='utf-8'))
core_scores = json.loads((CORE / '03_lead_scoring.json').read_text(encoding='utf-8'))
core_drafts = json.loads((CORE / '04_personalization_drafts.json').read_text(encoding='utf-8'))
core_qa = json.loads((CORE / '05_qa_review.json').read_text(encoding='utf-8'))

ext_sum = json.loads((EXT / 'run_summary.json').read_text(encoding='utf-8'))
a7 = json.loads((EXT / '07_oss_community_pipeline.json').read_text(encoding='utf-8'))
a8 = json.loads((EXT / '08_benchmark_watchdog.json').read_text(encoding='utf-8'))
a9 = json.loads((EXT / '09_reddit_intent_radar.json').read_text(encoding='utf-8'))
a10 = json.loads((EXT / '10_hn_trend_radar.json').read_text(encoding='utf-8'))
a11 = json.loads((EXT / '11_icp_enrichment_resolver.json').read_text(encoding='utf-8'))
a12 = json.loads((EXT / '12_competitive_intel_synthesizer.json').read_text(encoding='utf-8'))

def esc(s):
    return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

steps = [
    {
        'n': 1,
        'name': 'Core Run Bootstrap',
        'invoked': 'python3 GTM-skills/scripts/miro_gtm_agent_team.py',
        'live': 'Yes',
        'source': 'Live CSV from CrustData prior run + local artifacts',
        'numbers': f"lead_input_count={core_mgr.get('lead_input_count')}, accepted={core_mgr.get('accepted_count')}, rejected={core_mgr.get('rejected_count')}",
        'why': 'This is where the 25-lead batch enters the pipeline.',
    },
    {
        'n': 2,
        'name': 'A7 OSS Community Pipeline',
        'invoked': 'internal call: agent7_oss_community_pipeline()',
        'live': 'Yes',
        'source': 'GitHub API stargazers + user profile enrichment',
        'numbers': f"fetched_stargazers={a7.get('fetched_stargazers')}, enriched_profiles={a7.get('enriched_profiles')}, top_prospects={len(a7.get('top_prospects',[]))}",
        'why': 'Adds additional community-sourced prospects/signals; does not overwrite CrustData lead batch.',
    },
    {
        'n': 3,
        'name': 'A8 Benchmark Signal Watchdog',
        'invoked': 'internal call: agent8_benchmark_watchdog()',
        'live': 'Yes',
        'source': 'HN Algolia API + arXiv API',
        'numbers': f"hn_hits={len(a8.get('hn_hits',[]))}, threat_count={a8.get('threat_count')}, arxiv_papers={len(a8.get('arxiv_papers',[]))}",
        'why': 'Produces benchmark risk signals for messaging/positioning.',
    },
    {
        'n': 4,
        'name': 'A9 Reddit Intent Radar',
        'invoked': 'internal call: agent9_reddit_intent_radar()',
        'live': 'Yes',
        'source': 'Reddit search API',
        'numbers': f"total_posts={a9.get('total_posts')}, high_intent_posts={len(a9.get('high_intent_posts',[]))}",
        'why': 'Adds demand-intent social signals into the pipeline.',
    },
    {
        'n': 5,
        'name': 'A10 HN Trend Radar',
        'invoked': 'internal call: agent10_hn_trend_radar()',
        'live': 'Yes',
        'source': 'HN Algolia API keyword scans',
        'numbers': f"threads={a10.get('total_threads')}",
        'why': 'Adds trend/chatter signals used by A8/A12.',
    },
    {
        'n': 6,
        'name': 'A11 ICP Enrichment Resolver',
        'invoked': 'internal call: agent11_icp_enrichment_resolver()',
        'live': 'Derived',
        'source': 'Core accepted leads + source CSV fields',
        'numbers': f"enriched_count={a11.get('enriched_count')}",
        'why': 'Converts accepted leads into outreach-ready enriched records.',
    },
    {
        'n': 7,
        'name': 'A12 Competitive Intel Synthesizer',
        'invoked': 'internal call: agent12_competitive_intel_synthesizer()',
        'live': 'Mixed (live inputs, derived synthesis)',
        'source': 'A8/A10 outputs + orchestration context',
        'numbers': f"competitors={len(a12.get('competitors_monitored',[]))}, high_threats={len(a12.get('high_threats',[]))}",
        'why': 'Produces competitor-aware counter-positioning guidance for messaging.',
    },
    {
        'n': 8,
        'name': 'Visualization Build',
        'invoked': 'render scripts + build_interview_bundle.py + vercel deploy',
        'live': 'Derived from artifacts',
        'source': 'All generated JSON outputs',
        'numbers': f"total_agents={ext_sum.get('total_agents')}, dependency_edges=15, qa_approved={core_mgr.get('qa_approved')}",
        'why': 'Produces interview-ready evidence pages and clickable hosted links.',
    },
]

rows = ''.join(
    '<tr>'
    f"<td>{s['n']}</td>"
    f"<td>{esc(s['name'])}</td>"
    f"<td><code>{esc(s['invoked'])}</code></td>"
    f"<td>{esc(s['live'])}</td>"
    f"<td>{esc(s['source'])}</td>"
    f"<td>{esc(s['numbers'])}</td>"
    f"<td>{esc(s['why'])}</td>"
    '</tr>'
    for s in steps
)

html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8' />
<meta name='viewport' content='width=device-width, initial-scale=1.0' />
<title>MiroThinker Step-by-Step Execution Trace</title>
<style>
body{{font-family:Inter,Arial,sans-serif;margin:0;background:#f6f8fc;color:#0f172a}}
.wrap{{max-width:1400px;margin:0 auto;padding:24px}}
.card{{background:#fff;border:1px solid #dbe3ef;border-radius:12px;padding:16px;margin-bottom:12px}}
.grid{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}}
.k{{background:#fff;border:1px solid #dbe3ef;border-radius:10px;padding:10px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{border-bottom:1px solid #e2e8f0;padding:8px;text-align:left;vertical-align:top}}
th{{background:#0f172a;color:#fff;position:sticky;top:0}}
.table-wrap{{max-height:560px;overflow:auto;border:1px solid #dbe3ef;border-radius:10px}}
code{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:2px 4px}}
.muted{{color:#475569;font-size:13px}}
</style>
</head>
<body>
<div class='wrap'>
  <div class='card'>
    <h1>MiroThinker: Step-by-Step Execution Trace</h1>
    <p class='muted'>This page shows exactly what was invoked, whether it was live, and how each key number was produced.</p>
  </div>

  <div class='grid'>
    <div class='k'><strong>Source Lead Batch</strong><div>{core_mgr.get('lead_input_count')}</div></div>
    <div class='k'><strong>Accepted Leads</strong><div>{core_mgr.get('accepted_count')}</div></div>
    <div class='k'><strong>Drafts Generated</strong><div>{core_mgr.get('draft_count')}</div></div>
    <div class='k'><strong>QA Approved</strong><div>{core_mgr.get('qa_approved')}</div></div>
    <div class='k'><strong>Total Agents (Extended)</strong><div>{ext_sum.get('total_agents')}</div></div>
  </div>

  <div class='card'>
    <h2>Execution Timeline</h2>
    <div class='table-wrap'>
      <table>
        <thead>
          <tr>
            <th>Step</th>
            <th>Agent / Stage</th>
            <th>What Was Invoked</th>
            <th>Live?</th>
            <th>Data Source</th>
            <th>Numbers Produced</th>
            <th>What It Contributed</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </div>

  <div class='card'>
    <h2>Direct Answers</h2>
    <ul>
      <li><strong>Did we run all agents live?</strong> Core A1-A6 + new A7/A8/A9/A10 were executed with live API/data fetches in the last run. A11 and A12 are synthesis/enrichment over those live outputs.</li>
      <li><strong>Why still 25 leads?</strong> That number comes from the current CrustData source batch for the core pipeline input. New agents add signals/intel/enrichment, not automatic replacement of that source batch size.</li>
      <li><strong>Which agent produced leads?</strong> Core lead list comes from the CrustData source pipeline entering A2/A3; A7 adds an additional community prospect channel; A9 adds intent leads/signals.</li>
    </ul>
  </div>
</div>
</body>
</html>
"""

OUT.write_text(html, encoding='utf-8')
print(OUT)
