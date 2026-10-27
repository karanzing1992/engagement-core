-- Production emergency owner-approved route guard, applied 2026-10-27 via Supabase migration.
-- Resource-bound; never sends OAuth code or returns owner/customer records.
CREATE OR REPLACE FUNCTION public.generic_ssh_is_current_oauth_authorization(p_authorization_id text)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT COALESCE(
    length(p_authorization_id) BETWEEN 12 AND 160
    AND p_authorization_id ~ '^[a-zA-Z0-9_-]+$'
    AND EXISTS (
      SELECT 1 FROM auth.oauth_authorizations AS a
      WHERE a.authorization_id = p_authorization_id
        AND a.resource = 'https://saczglesalubroyaucqe.supabase.co/functions/v1/generic-linux-automator/mcp'
        AND a.status::text = 'pending'
        AND a.expires_at > now()
        AND a.created_at > now() - interval '30 minutes'
    ), false
  );
$$;
REVOKE ALL ON FUNCTION public.generic_ssh_is_current_oauth_authorization(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.generic_ssh_is_current_oauth_authorization(text) TO service_role;
COMMENT ON FUNCTION public.generic_ssh_is_current_oauth_authorization(text) IS
'Owner-authorized emergency OAuth routing predicate. Only service_role can evaluate; no data returned beyond exact SSH pending resource match. P0 Generic SSH freeze exception 2026-10-27.';
