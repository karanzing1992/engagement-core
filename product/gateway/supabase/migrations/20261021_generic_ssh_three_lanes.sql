-- Three independent SSH execution lanes per existing host; additive / backward-compatible.
-- Legacy worker polls and MCP calls continue to use operations by default.
alter table public.generic_auto_jobs
  add column if not exists lane text not null default 'operations';
alter table public.generic_auto_jobs
  add constraint generic_auto_jobs_lane_allowed
  check (lane in ('control','operations','development'));
create index if not exists generic_auto_jobs_lane_claim_idx
  on public.generic_auto_jobs (owner_id,host_id,lane,created_at)
  where status = 'queued';
alter table public.generic_auto_hosts
  add column if not exists control_seen_at timestamptz,
  add column if not exists operations_seen_at timestamptz,
  add column if not exists development_seen_at timestamptz;
-- Existing owner, worker hash, shell gates, RLS policies and ACLs remain unchanged.
