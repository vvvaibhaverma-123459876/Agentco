-- Store bounded source text for real specialist extraction.
-- Existing rows remain valid; extraction fails closed when no text exists.
ALTER TABLE autonomy_evidence
  ADD COLUMN IF NOT EXISTS content_text TEXT;
