-- Tighten Mission Control staging before use: all human-readable task fields
-- must be AES-GCM ciphertext generated in the trusted Edge Function.
-- The table was verified empty before this additive migration.
ALTER TABLE public.mission_control_mcp_inbox_v1
  ADD COLUMN payload_iv text NOT NULL,
  ADD COLUMN payload_ciphertext text NOT NULL,
  ADD COLUMN payload_version smallint NOT NULL DEFAULT 1
    CHECK (payload_version = 1);
ALTER TABLE public.mission_control_mcp_inbox_v1
  ADD CONSTRAINT mcmcp_encrypted_only CHECK (
    project = 'Encrypted' AND chat_title = '' AND chat_url = '' AND
    title = 'Encrypted' AND summary = '' AND next_step = '' AND
    blocker = '' AND status = 'Working' AND
    char_length(payload_iv) = 16 AND
    char_length(payload_ciphertext) BETWEEN 24 AND 30000
  );
COMMENT ON COLUMN public.mission_control_mcp_inbox_v1.payload_ciphertext IS
  'AES-256-GCM encrypted task payload; bound to owner UUID and task UUID as additional authenticated data. No plaintext task content stored.';
COMMENT ON COLUMN public.mission_control_mcp_inbox_v1.payload_iv IS
  'Fresh random 96-bit AES-GCM nonce (base64) for the encrypted task payload.';
