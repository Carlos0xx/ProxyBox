-- ProxyBox SQLite schema.
--
-- Applied on every app startup via app.db.init.init_schema(). All statements
-- must be idempotent (IF NOT EXISTS). Use additive migrations only — never
-- drop or rename columns in place once shipped.

CREATE TABLE IF NOT EXISTS device (
    name          TEXT     PRIMARY KEY,
    label         TEXT     NOT NULL DEFAULT '',
    kind          TEXT     NOT NULL DEFAULT 'generic',
    vless_uuid    TEXT     NOT NULL,
    hy2_password  TEXT     NOT NULL,
    vless_port    INTEGER  NOT NULL,
    hy2_port      INTEGER  NOT NULL,
    sni           TEXT     NOT NULL,
    created_at    INTEGER  NOT NULL,
    last_seen     INTEGER,
    last_ip       TEXT,
    revoked       INTEGER  NOT NULL DEFAULT 0,
    notes         TEXT     NOT NULL DEFAULT '',
    sub_token     TEXT     NOT NULL UNIQUE,
    paused_until  INTEGER  NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS device_revoked_idx   ON device (revoked);
CREATE INDEX IF NOT EXISTS device_last_seen_idx ON device (last_seen);
