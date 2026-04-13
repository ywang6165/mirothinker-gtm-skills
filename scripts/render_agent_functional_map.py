#!/usr/bin/env python3
import json
import os
from pathlib import Path

REPO_ROOT = Path(os.environ.get('MIRO_GTM_REPO_ROOT', Path(__file__).resolve().parents[1]))
BASE = REPO_ROOT / 'output' / 'agent-team-extended'
SUMMARY = json.loads((BASE / 'run_summary.json').read_text(encoding='utf-8'))
DEPS = json.loads((BASE / 'dependencies.json').read_text(encoding='utf-8'))

AGENTS = {
    'A1': {
        'name': 'ICP Strategist',
        'type': 'Core',
        'function': 'Defines ICP policy: segments, title rules, keywords, exclusions, and threshold.',
        'input': 'Source lead count + product positioning context',
        'output': 'ICP policy artifact used by signal/scoring agents',
    },
    'A2': {
        'name': 'Signal Miner',
        'type': 'Core',
        'function': 'Transforms raw leads into normalized signal features.',
        'input': 'Source leads + ICP policy + external source adapters (A7/A9)',
        'output': 'Per-lead structured signals (keywords, role, region, profile)',
    },
    'A3': {
        'name': 'Lead Scorer',
        'type': 'Core',
        'function': 'Applies deterministic scoring and acceptance/rejection logic.',
        'input': 'Signal records from A2',
        'output': 'Accepted and rejected lead lists with reasons and scores',
    },
    'A4': {
        'name': 'Personalization Writer',
        'type': 'Core',
        'function': 'Generates personalized email drafts and blog-angle hooks.',
        'input': 'Accepted leads + enrichment (A11) + competitive narrative cues (A12)',
        'output': 'Outreach drafts and content angles',
    },
    'A5': {
        'name': 'QA Approver',
        'type': 'Core',
        'function': 'Quality-gates drafts and retries low-quality content once.',
        'input': 'Drafts from A4',
        'output': 'Approved/rejected assets with QA notes',
    },
    'A6': {
        'name': 'GTM Orchestrator',
        'type': 'Core',
        'function': 'Runs chain control, validation checks, and publishes run artifacts.',
        'input': 'All upstream core outputs',
        'output': 'Run summary, validation status, and artifact index',
    },
    'A7': {
        'name': 'OSS Community Pipeline',
        'type': 'New',
        'function': 'Scans GitHub stargazers and ranks community prospects.',
        'input': 'GitHub stargazers + profile enrichment',
        'output': 'Community prospect list (tiered) feeding A2/A11',
    },
    'A8': {
        'name': 'Benchmark Signal Watchdog',
        'type': 'New',
        'function': 'Monitors benchmark chatter and recent benchmark papers.',
        'input': 'HN benchmark queries + arXiv feed',
        'output': 'Threat/event signals for positioning via A12',
    },
    'A9': {
        'name': 'Reddit Intent Radar',
        'type': 'New',
        'function': 'Finds high-intent Reddit threads from problem/verification language.',
        'input': 'Reddit search results by GTM intent queries',
        'output': 'High-intent community signals feeding A2',
    },
    'A10': {
        'name': 'HackerNews Trend Radar',
        'type': 'New',
        'function': 'Collects and deduplicates HN trend threads by strategic keywords.',
        'input': 'HN Algolia keyword searches',
        'output': 'Thread-level trend signals feeding A8/A12',
    },
    'A11': {
        'name': 'ICP Enrichment Resolver',
        'type': 'New',
        'function': 'Enriches accepted leads with persona/domain/link fields.',
        'input': 'Accepted leads (A3) + source CSV + A7 context',
        'output': 'Enriched profile records feeding A4',
    },
    'A12': {
        'name': 'Competitive Intel Synthesizer',
        'type': 'New',
        'function': 'Builds competitor threat and counter-positioning intelligence.',
        'input': 'Watchdog signals (A8/A10) + orchestration context (A6)',
        'output': 'Competitive narratives feeding A4 and strategy',
    },
}

up = {k: [] for k in AGENTS}
down = {k: [] for k in AGENTS}
for e in DEPS.get('edges', []):
    a = e['from']
    b = e['to']
    if a in AGENTS and b in AGENTS:
        down[a].append(b)
        up[b].append(a)

cards = []
for aid in AGENTS:
    a = AGENTS[aid]
    cards.append(
        f"""
        <article class='card'>
          <div class='tag {'new' if a['type']=='New' else 'core'}'>{a['type']}</div>
          <h3>{aid} — {a['name']}</h3>
          <p><strong>Main functionality:</strong> {a['function']}</p>
          <p><strong>Input:</strong> {a['input']}</p>
          <p><strong>Output:</strong> {a['output']}</p>
          <p><strong>Depends on:</strong> {', '.join(up[aid]) if up[aid] else 'None (source agent)'}</p>
          <p><strong>Feeds:</strong> {', '.join(down[aid]) if down[aid] else 'Terminal output'}</p>
        </article>
        """
    )

mermaid = DEPS.get('mermaid', '')

key_counts = SUMMARY.get('key_counts', {})

html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8' />
<meta name='viewport' content='width=device-width, initial-scale=1.0' />
<title>MiroThinker Agent Functional Map</title>
<style>
body{{font-family:Inter,Arial,sans-serif;margin:0;background:#f6f8fc;color:#0f172a}}
.wrap{{max-width:1300px;margin:0 auto;padding:24px}}
.panel{{background:#fff;border:1px solid #dbe3ef;border-radius:14px;padding:16px;margin-bottom:12px}}
.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}}
.k{{background:#fff;border:1px solid #dbe3ef;border-radius:10px;padding:10px}}
.cards{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}
.card{{background:#fff;border:1px solid #dbe3ef;border-radius:12px;padding:12px}}
.tag{{display:inline-block;font-size:12px;font-weight:700;border-radius:999px;padding:4px 8px;margin-bottom:8px}}
.tag.core{{background:#dbeafe;color:#1d4ed8}}
.tag.new{{background:#dcfce7;color:#166534}}
pre{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px;white-space:pre-wrap}}
.muted{{color:#475569;font-size:13px}}
@media(max-width:1000px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr));}} .cards{{grid-template-columns:1fr;}}}}
</style>
</head>
<body>
<div class='wrap'>
  <div class='panel'>
    <h1>MiroThinker GTM Agent Functional Map (12 Agents)</h1>
    <p class='muted'>This page renames agents by functionality and shows exact dependency relationships.</p>
    <p><strong>Important:</strong> The 25-lead count is from the current CrustData batch. The added 6 agents mainly add signal/intel/enrichment channels; they do not replace the source lead batch size by themselves.</p>
  </div>

  <div class='grid'>
    <div class='k'><strong>Total agents</strong><div>{SUMMARY.get('total_agents')}</div></div>
    <div class='k'><strong>Core agents</strong><div>{SUMMARY.get('core_agents')}</div></div>
    <div class='k'><strong>New agents</strong><div>{SUMMARY.get('new_agents')}</div></div>
    <div class='k'><strong>Dependency edges</strong><div>{DEPS.get('edge_count')}</div></div>
    <div class='k'><strong>Core accepted leads</strong><div>{key_counts.get('core_accepted_leads')}</div></div>
    <div class='k'><strong>Community prospects (A7)</strong><div>{key_counts.get('a7_top_prospects')}</div></div>
    <div class='k'><strong>Reddit high-intent (A9)</strong><div>{key_counts.get('a9_high_intent_posts')}</div></div>
    <div class='k'><strong>HN threads (A10)</strong><div>{key_counts.get('a10_threads')}</div></div>
  </div>

  <div class='panel'>
    <h2>Dependency Graph (Mermaid)</h2>
    <pre>{mermaid}</pre>
  </div>

  <div class='panel'>
    <h2>Agent Names + Functionality + Dependencies</h2>
    <div class='cards'>
      {''.join(cards)}
    </div>
  </div>
</div>
</body>
</html>
"""

out = BASE / 'mirothinker-agent-functional-map.html'
out.write_text(html, encoding='utf-8')
print(out)
