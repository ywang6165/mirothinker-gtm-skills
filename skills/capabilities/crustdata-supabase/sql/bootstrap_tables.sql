-- Minimal bootstrap for Goose GTM lead pipeline
-- Run in Supabase SQL Editor (project: hyzmkyakdqlxyskhgcjt)

create extension if not exists "uuid-ossp";

create table if not exists public.leads (
  id uuid primary key default uuid_generate_v4(),
  linkedin_url text unique not null,
  email text,
  email_verified boolean default false,
  name text,
  first_name text,
  last_name text,
  title text,
  company text,
  company_domain text,
  company_linkedin_url text,
  company_headcount text,
  industry text,
  location text,
  seniority_level text,
  headline text,
  years_of_experience integer,
  connections integer,
  skills text[],
  source text default 'crustdata',
  client_name text,
  search_config_name text,
  icp_segment text,
  date_found timestamptz default now(),
  enrichment_status text default 'complete',
  qualification_score numeric,
  last_contacted timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.outreach_log (
  id uuid primary key default uuid_generate_v4(),
  lead_id uuid references public.leads(id) on delete cascade,
  campaign_name text,
  channel text default 'email',
  sent_date timestamptz,
  status text default 'sent',
  notes text,
  created_at timestamptz default now()
);

create table if not exists public.companies (
  id uuid primary key default uuid_generate_v4(),
  domain text unique,
  name text,
  linkedin_url text,
  headcount integer,
  headcount_range text,
  industry text,
  company_type text,
  tech_stack jsonb default '[]'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_leads_linkedin_url on public.leads(linkedin_url);
create index if not exists idx_leads_client_name on public.leads(client_name);
create index if not exists idx_leads_last_contacted on public.leads(last_contacted);
create index if not exists idx_outreach_lead_id on public.outreach_log(lead_id);
create index if not exists idx_companies_domain on public.companies(domain);
