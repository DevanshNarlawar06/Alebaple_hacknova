-- ============================================================
-- Disaster Information Verification System
-- Canonical SQLite Schema — v0.1
--
-- Authoritative definition. All pipeline scripts and the
-- application must conform to these field names and types.
--
-- Changelog: see dataset_changelog.md
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ============================================================
-- TABLE: sources
-- Registry of all data sources used in claims and evidence.
-- credibility_tier: A=highest (official gov/UN), B=established
--   humanitarian org, C=credible news, D=unverified/social
-- ============================================================
CREATE TABLE IF NOT EXISTS sources (
    source_id             TEXT    PRIMARY KEY,
    source_name           TEXT    NOT NULL,
    source_type           TEXT    NOT NULL
                          CHECK(source_type IN (
                              'official_agency','humanitarian_org',
                              'news_media','social_media','research','synthetic'
                          )),
    source_url            TEXT,
    authority_level       INTEGER CHECK(authority_level BETWEEN 1 AND 5),
    officiality           TEXT    CHECK(officiality IN ('official','semi_official','unofficial')),
    timestamp_precision   TEXT    CHECK(timestamp_precision IN ('exact','date_only','approximate','unknown')),
    geographic_precision  TEXT    CHECK(geographic_precision IN ('coordinate','city','region','country','unknown')),
    license               TEXT,
    retrieval_method      TEXT    CHECK(retrieval_method IN ('api','manual_download','rss','scraping','synthetic')),
    credibility_tier      TEXT    CHECK(credibility_tier IN ('A','B','C','D')),
    notes                 TEXT,
    schema_version        TEXT    NOT NULL DEFAULT '0.1',
    created_at            TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- ============================================================
-- TABLE: claims
-- ============================================================
CREATE TABLE IF NOT EXISTS claims (
    claim_id              TEXT    PRIMARY KEY,
    claim_text            TEXT    NOT NULL,
    source_id             TEXT    REFERENCES sources(source_id),
    source_type           TEXT,
    published_at          TEXT,
    retrieved_at          TEXT    NOT NULL,
    event_type            TEXT    CHECK(event_type IN (
                              'flood','earthquake','cyclone','wildfire',
                              'landslide','drought','tsunami','heatwave',
                              'storm','other','unknown'
                          )),
    location_text         TEXT,
    latitude              REAL    CHECK(latitude IS NULL OR latitude BETWEEN -90 AND 90),
    longitude             REAL    CHECK(longitude IS NULL OR longitude BETWEEN -180 AND 180),
    country               TEXT,
    region                TEXT,
    extracted_entities    TEXT,
    is_synthetic          INTEGER NOT NULL DEFAULT 0   CHECK(is_synthetic IN (0,1)),
    derived_from_event_id TEXT,
    generation_method     TEXT,
    human_validated       INTEGER NOT NULL DEFAULT 0   CHECK(human_validated IN (0,1)),
    schema_version        TEXT    NOT NULL DEFAULT '0.1',
    created_at            TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- ============================================================
-- TABLE: evidence
-- ============================================================
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id           TEXT    PRIMARY KEY,
    source_id             TEXT    REFERENCES sources(source_id),
    source_name           TEXT,
    source_url            TEXT,
    evidence_text         TEXT    NOT NULL,
    published_at          TEXT,
    retrieved_at          TEXT    NOT NULL,
    event_type            TEXT    CHECK(event_type IN (
                              'flood','earthquake','cyclone','wildfire',
                              'landslide','drought','tsunami','heatwave',
                              'storm','other','unknown'
                          )),
    location_text         TEXT,
    latitude              REAL    CHECK(latitude IS NULL OR latitude BETWEEN -90 AND 90),
    longitude             REAL    CHECK(longitude IS NULL OR longitude BETWEEN -180 AND 180),
    country               TEXT,
    region                TEXT,
    credibility_tier      TEXT    CHECK(credibility_tier IN ('A','B','C','D')),
    is_synthetic          INTEGER NOT NULL DEFAULT 0   CHECK(is_synthetic IN (0,1)),
    schema_version        TEXT    NOT NULL DEFAULT '0.1',
    created_at            TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- ============================================================
-- TABLE: claim_evidence_links
-- ============================================================
CREATE TABLE IF NOT EXISTS claim_evidence_links (
    link_id               TEXT    PRIMARY KEY,
    claim_id              TEXT    NOT NULL REFERENCES claims(claim_id),
    evidence_id           TEXT    NOT NULL REFERENCES evidence(evidence_id),
    relationship          TEXT    NOT NULL CHECK(relationship IN (
                              'SUPPORTS','CONTRADICTS','IRRELEVANT','INSUFFICIENT'
                          )),
    support_strength      REAL    CHECK(support_strength IS NULL OR support_strength BETWEEN 0.0 AND 1.0),
    contradiction_type    TEXT    CHECK(contradiction_type IN (
                              'LOCATION_CONFLICT','TIME_CONFLICT','EVENT_TYPE_CONFLICT',
                              'STATUS_CONFLICT','SEVERITY_CONFLICT','QUANTITY_CONFLICT',
                              'CASUALTY_CONFLICT','OTHER'
                          )),
    reason                TEXT,
    human_validated       INTEGER NOT NULL DEFAULT 0   CHECK(human_validated IN (0,1)),
    reviewer              TEXT,
    schema_version        TEXT    NOT NULL DEFAULT '0.1',
    created_at            TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE(claim_id, evidence_id)
);

-- ============================================================
-- TABLE: ground_truth
-- ============================================================
CREATE TABLE IF NOT EXISTS ground_truth (
    gt_id                     TEXT    PRIMARY KEY,
    claim_id                  TEXT    NOT NULL REFERENCES claims(claim_id) UNIQUE,
    expected_status           TEXT    NOT NULL CHECK(expected_status IN (
                                  'VERIFIED','CONFLICTING','OUTDATED','UNVERIFIED'
                              )),
    expected_event_type       TEXT,
    expected_location_text    TEXT,
    expected_latitude         REAL,
    expected_longitude        REAL,
    expected_time_range_start TEXT,
    expected_time_range_end   TEXT,
    freshness_status          TEXT    CHECK(freshness_status IN ('FRESH','AGING','OUTDATED','UNKNOWN')),
    freshness_threshold_hours INTEGER,
    difficulty                TEXT    NOT NULL DEFAULT 'MEDIUM'
                              CHECK(difficulty IN ('EASY','MEDIUM','HARD','AMBIGUOUS')),
    reason                    TEXT    NOT NULL,
    human_validated           INTEGER NOT NULL DEFAULT 0 CHECK(human_validated IN (0,1)),
    reviewer                  TEXT,
    review_notes              TEXT,
    schema_version            TEXT    NOT NULL DEFAULT '0.1',
    created_at                TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_claims_event_type     ON claims(event_type);
CREATE INDEX IF NOT EXISTS idx_claims_country        ON claims(country);
CREATE INDEX IF NOT EXISTS idx_claims_published_at   ON claims(published_at);
CREATE INDEX IF NOT EXISTS idx_claims_is_synthetic   ON claims(is_synthetic);
CREATE INDEX IF NOT EXISTS idx_evidence_event_type   ON evidence(event_type);
CREATE INDEX IF NOT EXISTS idx_evidence_country      ON evidence(country);
CREATE INDEX IF NOT EXISTS idx_evidence_credibility  ON evidence(credibility_tier);
CREATE INDEX IF NOT EXISTS idx_links_claim_id        ON claim_evidence_links(claim_id);
CREATE INDEX IF NOT EXISTS idx_links_evidence_id     ON claim_evidence_links(evidence_id);
CREATE INDEX IF NOT EXISTS idx_links_relationship    ON claim_evidence_links(relationship);
CREATE INDEX IF NOT EXISTS idx_gt_status             ON ground_truth(expected_status);
CREATE INDEX IF NOT EXISTS idx_gt_validated          ON ground_truth(human_validated);
CREATE INDEX IF NOT EXISTS idx_gt_difficulty         ON ground_truth(difficulty);
