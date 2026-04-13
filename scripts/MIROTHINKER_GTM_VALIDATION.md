# MiroThinker GTM Validation Guide

This guide lets another engineer run and validate the full workflow on their own machine.

## 1) Fast Repro (no secrets required)

- Python 3.9+

```bash
python3 scripts/run_portable_validation.py
```

This path uses committed artifacts plus `scripts/fixtures/mirothinker-source-leads.csv` so a fresh clone reproduces the interview bundle without API keys.

## 2) Full Live Re-run (requires API credentials)

- Node.js 18+
- Vercel CLI access (optional, only for deployment)
- API credentials:
  - `CRUSTDATA_API_TOKEN`
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - Optional: `GITHUB_TOKEN` (improves GitHub API limits)

Create `.env` at repo root (`GTM-skills/.env`) with those values.

## 3) Generate source leads (CrustData + Supabase)

```bash
python3 skills/capabilities/crustdata-supabase/scripts/prospect_search.py \
  --config skills/capabilities/crustdata-supabase/configs/mirothinker.json \
  --yes
```

Optional preview count:

```bash
python3 skills/capabilities/crustdata-supabase/scripts/prospect_search.py \
  --config skills/capabilities/crustdata-supabase/configs/mirothinker.json \
  --preview
```

## 4) Run the core 6-agent workflow

```bash
python3 scripts/miro_gtm_agent_team.py
```

Outputs: `output/agent-team/`

## 5) Run the extended 12-agent workflow

```bash
python3 scripts/miro_gtm_extended_agents.py
```

Outputs: `output/agent-team-extended/`

## 6) Build interview bundle

```bash
python3 scripts/build_interview_bundle.py
```

Outputs: `output/interview-bundle/`

## 7) Deploy interview bundle (optional)

```bash
bash scripts/one_click_vercel_publish.sh
```

## 8) Key validation artifacts

- `output/agent-team/06_manager_summary.json`
- `output/agent-team-extended/run_summary.json`
- `output/agent-team-extended/dependencies.json`
- `output/interview-bundle/index.html`

## Security

Do not commit `.env` or any secret keys.
Rotate keys if they were shared in logs/chats.
