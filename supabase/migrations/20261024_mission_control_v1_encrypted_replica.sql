-- Mission Control encrypted replica (production target: saczglesalubroyaucqe)
-- Original production migration: mission_control_v1_encrypted_replica
-- Follow-up security hardening: mission_control_v1_security_invoker
-- Idempotent source representation; never grant anon/authenticated access.
create table if not exists public.mission_control_v1_backups (
 vault_id text primary key constraint mc_v1_single_owner check (vault_id = 'owner'),
 version bigint not null constraint mc_v1_version_nonnegative check (version >= 0),
 iv text not null constraint mc_v1_iv_length check (char_length(iv) between 16 and 64),
 ciphertext text not null,
 item_count integer not null constraint mc_v1_count_bounds check (item_count between 0 and 5000),
 updated_at timestamptz not null default now()
);
alter table public.mission_control_v1_backups enable row level security;
revoke all on table public.mission_control_v1_backups from public, anon, authenticated;
grant select,insert,update on public.mission_control_v1_backups to service_role;
create or replace function public.mission_control_v1_save_backup(
 p_version bigint,p_iv text,p_ciphertext text,p_count integer
) returns table(saved boolean,current_version bigint)
language plpgsql security invoker set search_path=pg_catalog,public
as $$
declare affected integer;
begin
 if p_version < 0 or p_count < 0 or p_count > 5000
   or char_length(p_iv) < 16 or char_length(p_iv) > 64
   or char_length(p_ciphertext) < 20 or char_length(p_ciphertext) > 2000000
 then raise exception 'invalid backup payload'; end if;
 insert into public.mission_control_v1_backups(vault_id,version,iv,ciphertext,item_count)
 values('owner',p_version,p_iv,p_ciphertext,p_count)
 on conflict(vault_id) do update set
   version=excluded.version,iv=excluded.iv,
   ciphertext=excluded.ciphertext,item_count=excluded.item_count,updated_at=now()
 where public.mission_control_v1_backups.version < excluded.version;
 get diagnostics affected = row_count;
 saved := affected > 0;
 select b.version into current_version
 from public.mission_control_v1_backups b where b.vault_id='owner';
 return next;
end;
$$;
revoke all on function public.mission_control_v1_save_backup(bigint,text,text,integer) from public, anon, authenticated;
grant execute on function public.mission_control_v1_save_backup(bigint,text,text,integer) to service_role;
