BEGIN;
SELECT pg_advisory_xact_lock(727001);
CREATE TABLE IF NOT EXISTS schema_version (version integer PRIMARY KEY);
INSERT INTO schema_version VALUES (1) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS installations (
 id text PRIMARY KEY, token_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 epoch bigint NOT NULL DEFAULT 0, enabled boolean NOT NULL DEFAULT false,
 prompts boolean NOT NULL DEFAULT false, raw_otlp boolean NOT NULL DEFAULT false,
 revoked boolean NOT NULL DEFAULT false, bytes bigint NOT NULL DEFAULT 0,
 rate_minute bigint NOT NULL DEFAULT 0, rate_count integer NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS events (
 installation text NOT NULL REFERENCES installations(id), id text NOT NULL,
 epoch bigint NOT NULL, kind text NOT NULL CHECK(kind IN ('metrics','prompts','raw_otlp')),
 data jsonb NOT NULL, size integer NOT NULL, received_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(installation,id));
CREATE INDEX IF NOT EXISTS events_kind ON events(kind);
CREATE INDEX IF NOT EXISTS events_received ON events(received_at);
CREATE TABLE IF NOT EXISTS deletions (
 installation text PRIMARY KEY, epoch bigint NOT NULL, deleted_at timestamptz NOT NULL DEFAULT now());
COMMIT;
