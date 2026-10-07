-- WP Control multi-tenant gateway.
create table if not exists public.wpcontrol_sites (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references auth.users(id) on delete set null,
  name text not null,
  base_url text not null unique,
  status text not null default 'pending' check (status in ('pending','active','suspended','revoked')),
  plan text not null default 'free',
  capabilities jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.wpcontrol_pairings (
  id uuid primary key default gen_random_uuid(),
  site_id uuid not null references public.wpcontrol_sites(id) on delete cascade,
  code_hash text not null unique,
  expires_at timestamptz not null,
  claimed_by uuid references auth.users(id) on delete set null,
  claimed_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.wpcontrol_audit (
  id bigint generated always as identity primary key,
  request_id uuid not null default gen_random_uuid(),
  site_id uuid references public.wpcontrol_sites(id) on delete set null,
  actor_user_id uuid references auth.users(id) on delete set null,
  tool_name text not null,
  success boolean not null default true,
  duration_ms integer not null default 0,
  error_code text not null default '',
  created_at timestamptz not null default now()
);

alter table public.wpcontrol_sites enable row level security;
alter table public.wpcontrol_pairings enable row level security;
alter table public.wpcontrol_audit enable row level security;

revoke all on public.wpcontrol_sites from anon, authenticated;
revoke all on public.wpcontrol_pairings from anon, authenticated;
revoke all on public.wpcontrol_audit from anon, authenticated;

create index if not exists wpcontrol_sites_owner_idx on public.wpcontrol_sites(owner_id);
create index if not exists wpcontrol_pairings_site_idx on public.wpcontrol_pairings(site_id);
create index if not exists wpcontrol_audit_site_created_idx on public.wpcontrol_audit(site_id, created_at desc);
