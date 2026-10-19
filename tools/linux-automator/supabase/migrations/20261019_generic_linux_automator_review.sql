-- Review-only SQL: never apply without verified owner/project and backup.
-- Dedicated tables; no access to or reuse of Pine/Andaz/customer credentials.
create table if not exists public.generic_auto_members (
 user_id uuid primary key references auth.users(id) on delete cascade,
 role text not null check (role='owner'),
 enabled boolean not null default false
);
create table if not exists public.generic_auto_hosts (
 host_id text primary key check (host_id in ('dell-linux','mac-linux')),
 owner_id uuid not null references public.generic_auto_members(user_id),
 worker_hash text unique check (worker_hash is null or worker_hash ~ '^[0-9a-f]{64}$'),
 paired_at timestamptz, last_seen_at timestamptz, worker_version text,
 enabled boolean not null default false,
 allow_shell boolean not null default false
);
create table if not exists public.generic_auto_pairings (
 id uuid primary key default gen_random_uuid(),
 host_id text not null references public.generic_auto_hosts(host_id),
 owner_id uuid not null references public.generic_auto_members(user_id),
 code_hash text not null unique check (code_hash ~ '^[0-9a-f]{64}$'),
 expires_at timestamptz not null,
 consumed_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists public.generic_auto_jobs (
 id uuid primary key default gen_random_uuid(),
 host_id text not null references public.generic_auto_hosts(host_id),
 owner_id uuid not null references public.generic_auto_members(user_id),
 kind text not null check (kind in ('probe','shell')),
 command text not null default '',
 status text not null default 'queued'
   check (status in ('queued','running','completed','failed')),
 claim uuid unique,
 timeout_seconds integer not null default 20 check (timeout_seconds between 5 and 120),
 created_at timestamptz not null default now(),
 expires_at timestamptz not null default (now() + interval '2 minutes'),
 started_at timestamptz, finished_at timestamptz,
 stdout text, stderr text, exit_code integer
);
create index if not exists generic_auto_jobs_queue_idx
 on public.generic_auto_jobs(host_id,created_at) where status='queued';
create index if not exists generic_auto_pairings_expiry_idx
 on public.generic_auto_pairings(expires_at) where consumed_at is null;
alter table public.generic_auto_members enable row level security;
alter table public.generic_auto_hosts enable row level security;
alter table public.generic_auto_pairings enable row level security;
alter table public.generic_auto_jobs enable row level security;
revoke all on public.generic_auto_members from public,anon,authenticated;
revoke all on public.generic_auto_hosts from public,anon,authenticated;
revoke all on public.generic_auto_pairings from public,anon,authenticated;
revoke all on public.generic_auto_jobs from public,anon,authenticated;
grant all on public.generic_auto_members to service_role;
grant all on public.generic_auto_hosts to service_role;
grant all on public.generic_auto_pairings to service_role;
grant all on public.generic_auto_jobs to service_role;
-- Private bootstrap after verifying exact Supabase Auth user ID:
-- insert into public.generic_auto_members(user_id,role,enabled)
-- values ('<verified-owner-uuid>','owner',true);
-- insert into public.generic_auto_hosts(host_id,owner_id,enabled)
-- values ('dell-linux','<verified-owner-uuid>',true),
--        ('mac-linux','<verified-owner-uuid>',true);
