-- backend/app/db/schema.sql
-- Apply to Supabase project via SQL editor or: supabase db push
-- Requires pgcrypto for gen_random_uuid()

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─── HOTELS ──────────────────────────────────────────────────────────────────
CREATE TABLE hotels (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name                  text NOT NULL,
    address               text,
    stripe_customer_id    text,
    subscription_status   text NOT NULL DEFAULT 'trialing'
                              CHECK (subscription_status IN ('trialing','active','past_due','canceled')),
    plan                  text NOT NULL DEFAULT 'starter',
    image_retention_hours int  NOT NULL DEFAULT 24 CHECK (image_retention_hours BETWEEN 1 AND 720),
    dpa_signed_at         timestamptz,
    dpa_version           text,
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now()
);

-- ─── USERS ───────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id               uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    hotel_id         uuid NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    email            text NOT NULL,
    role             text NOT NULL DEFAULT 'clerk' CHECK (role IN ('owner','clerk')),
    consent_given_at timestamptz,
    created_at       timestamptz NOT NULL DEFAULT now(),
    last_login_at    timestamptz
);

CREATE INDEX users_hotel_id_idx ON users(hotel_id);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_hotel_isolation ON users
    USING (hotel_id = (auth.jwt() ->> 'hotel_id')::uuid);

-- ─── GUESTS ──────────────────────────────────────────────────────────────────
CREATE TABLE guests (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id              uuid NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    first_name            text,
    last_name             text,
    dob                   date,
    doc_number_last4      text,
    doc_number_encrypted  bytea,           -- Fernet-encrypted at application layer
    doc_type              text CHECK (doc_type IN ('passport','drivers_license','national_id','other')),
    doc_country           text,            -- ISO 3166-1 alpha-2
    email                 text,
    phone                 text,
    address               text,
    nationality           text,
    notes                 text,
    search_vector         tsvector,
    deletion_requested_at timestamptz,
    deleted_at            timestamptz,
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX guests_hotel_id_idx ON guests(hotel_id);
CREATE INDEX guests_search_idx   ON guests USING GIN(search_vector);
CREATE INDEX guests_active_idx   ON guests(hotel_id, created_at DESC) WHERE deleted_at IS NULL;

ALTER TABLE guests ENABLE ROW LEVEL SECURITY;
CREATE POLICY guests_hotel_isolation ON guests
    USING (hotel_id = (auth.jwt() ->> 'hotel_id')::uuid);

CREATE OR REPLACE FUNCTION guests_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        to_tsvector('english',
            coalesce(NEW.first_name, '') || ' ' ||
            coalesce(NEW.last_name,  '') || ' ' ||
            coalesce(NEW.doc_number_last4, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER guests_search_vector_trigger
    BEFORE INSERT OR UPDATE ON guests
    FOR EACH ROW EXECUTE FUNCTION guests_search_vector_update();

-- ─── WORKSTATIONS ────────────────────────────────────────────────────────────
CREATE TABLE workstations (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id                uuid NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    name                    text NOT NULL,
    pairing_code            text,
    pairing_code_expires_at timestamptz,
    token_hash              text,          -- bcrypt hash of ws_live_ token; NEVER store raw
    token_prefix            text,          -- first 12 chars of token for display/logs
    revoked_at              timestamptz,
    last_used_at            timestamptz,
    paired_at               timestamptz,
    last_seen_at            timestamptz,
    created_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX workstations_hotel_id_idx     ON workstations(hotel_id);
CREATE INDEX workstations_token_prefix_idx ON workstations(token_prefix) WHERE token_hash IS NOT NULL;

ALTER TABLE workstations ENABLE ROW LEVEL SECURITY;
CREATE POLICY workstations_hotel_isolation ON workstations
    USING (hotel_id = (auth.jwt() ->> 'hotel_id')::uuid);

-- ─── SCANS ───────────────────────────────────────────────────────────────────
CREATE TYPE scan_status AS ENUM ('pending','parsed','typed','failed','expired');

CREATE TABLE scans (
    id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id                    uuid NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    guest_id                    uuid REFERENCES guests(id),
    user_id                     uuid REFERENCES users(id),
    workstation_id              uuid REFERENCES workstations(id),
    image_path                  text,                    -- NULL after retention window expires
    image_deleted_at            timestamptz,
    image_deletion_scheduled_at timestamptz,             -- set on upload; retention job checks this
    status                      scan_status NOT NULL DEFAULT 'pending',
    parsed_data                 jsonb,                   -- text fields only, NO biometric data
    face_region_blacked_out     boolean NOT NULL DEFAULT true,  -- compliance flag; always true
    error_message               text,
    created_at                  timestamptz NOT NULL DEFAULT now(),
    parsed_at                   timestamptz,
    typed_at                    timestamptz
);

CREATE INDEX scans_hotel_status_idx  ON scans(hotel_id, status);
CREATE INDEX scans_hotel_created_idx ON scans(hotel_id, created_at DESC);
CREATE INDEX scans_parsed_idx        ON scans(hotel_id, status) WHERE status = 'parsed';
CREATE INDEX scans_retention_idx     ON scans(image_deletion_scheduled_at) WHERE image_path IS NOT NULL;

ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
CREATE POLICY scans_hotel_isolation ON scans
    USING (hotel_id = (auth.jwt() ->> 'hotel_id')::uuid);

-- ─── AUDIT LOG ───────────────────────────────────────────────────────────────
-- Append-only. After applying, run: REVOKE DELETE ON audit_log FROM PUBLIC;
-- Retained 7 years per compliance requirement.
CREATE TABLE audit_log (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id      uuid,           -- nullable for system-level events
    user_id       uuid,
    action        text NOT NULL,  -- e.g. 'scan.parsed', 'guest.read', 'token.revoked'
    resource_type text,
    resource_id   uuid,
    metadata      jsonb NOT NULL DEFAULT '{}',
    ip_address    inet,
    user_agent    text,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX audit_log_hotel_created_idx ON audit_log(hotel_id, created_at DESC);

-- ─── DATA SUBJECT REQUESTS (GDPR/CCPA) ──────────────────────────────────────
CREATE TABLE data_subject_requests (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id         uuid REFERENCES hotels(id),
    requester_email  text NOT NULL,
    request_type     text NOT NULL CHECK (request_type IN ('access','delete','export')),
    status           text NOT NULL DEFAULT 'pending'
                         CHECK (status IN ('pending','processing','completed','rejected')),
    completed_at     timestamptz,
    created_at       timestamptz NOT NULL DEFAULT now()
);
