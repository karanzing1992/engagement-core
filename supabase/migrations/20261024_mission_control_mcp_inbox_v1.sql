-- Mission Control ChatGPT MCP staging inbox.
-- Deliberately separate from the encrypted canonical WordPress index and backup.
CREATE TABLE IF NOT EXISTS public.mission_control_mcp_inbox_v1 (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  project text NOT NULL DEFAULT 'Unfiled Chats' CHECK (char_length(project) BETWEEN 1 AND 100),
  chat_title text NOT NULL DEFAULT '' CHECK (char_length(chat_title) <= 180),
  chat_url text NOT NULL DEFAULT '' CHECK (char_length(chat_url) <= 400),
  title text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 180),
  summary text NOT NULL DEFAULT '' CHECK (char_length(summary) <= 1500),
  next_step text NOT NULL DEFAULT '' CHECK (char_length(next_step) <= 700),
  blocker text NOT NULL DEFAULT '' CHECK (char_length(blocker) <= 700),
  status text NOT NULL DEFAULT 'Working' CHECK (status IN ('Working','Done','On Ice','Deprecated')),
  sync_state text NOT NULL DEFAULT 'staged' CHECK (sync_state IN ('staged','imported')),
  source text NOT NULL DEFAULT 'chatgpt-mcp' CHECK (source='chatgpt-mcp'),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.mission_control_mcp_inbox_v1 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.mission_control_mcp_inbox_v1 FROM PUBLIC, anon;
GRANT SELECT, INSERT, UPDATE ON public.mission_control_mcp_inbox_v1 TO authenticated;
CREATE POLICY mcmcp_owner_select ON public.mission_control_mcp_inbox_v1 FOR SELECT TO authenticated
  USING (owner_id = (SELECT auth.uid()));
CREATE POLICY mcmcp_owner_insert ON public.mission_control_mcp_inbox_v1 FOR INSERT TO authenticated
  WITH CHECK (owner_id = (SELECT auth.uid()));
CREATE POLICY mcmcp_owner_update ON public.mission_control_mcp_inbox_v1 FOR UPDATE TO authenticated
  USING (owner_id = (SELECT auth.uid())) WITH CHECK (owner_id = (SELECT auth.uid()));
CREATE INDEX mcmcp_inbox_owner_recent_idx ON public.mission_control_mcp_inbox_v1
  (owner_id, updated_at DESC);
CREATE INDEX mcmcp_inbox_owner_status_idx ON public.mission_control_mcp_inbox_v1
  (owner_id, status, updated_at DESC);
COMMENT ON TABLE public.mission_control_mcp_inbox_v1 IS
  'Owner-isolated ChatGPT MCP task staging; WordPress owner vault remains canonical. No full chat transcripts or secrets.';