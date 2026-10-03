-- =============================================================================
-- DevComprehend — Initial Database Schema (v1)
-- Migration: 001_initial_schema.sql
-- Created:  2026-10-03
-- Author:   Efe (Contracts & Infrastructure)
-- =============================================================================

BEGIN;

-- ─── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── ENUM Types ──────────────────────────────────────────────────────────────
CREATE TYPE analysis_status AS ENUM ('QUEUED', 'PROCESSING', 'READY', 'FAILED', 'EXPIRED');
CREATE TYPE plan_type AS ENUM ('free', 'pro', 'team', 'enterprise');
CREATE TYPE fsrs_state AS ENUM ('New', 'Learning', 'Review', 'Relearning');

-- ─── users ───────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_identifier VARCHAR(255) NOT NULL UNIQUE,
    plan_type       plan_type NOT NULL DEFAULT 'free',
    daily_quota_tokens INTEGER NOT NULL DEFAULT 50000,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── workspaces ──────────────────────────────────────────────────────────────
CREATE TABLE workspaces (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_hash  VARCHAR(64) NOT NULL,
    name            VARCHAR(255) NOT NULL,
    root_path_alias VARCHAR(512),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_workspaces_user ON workspaces(user_id);

-- ─── analyses ────────────────────────────────────────────────────────────────
CREATE TABLE analyses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    snapshot_id     VARCHAR(64) NOT NULL,
    diff_hash       VARCHAR(64) NOT NULL,
    status          analysis_status NOT NULL DEFAULT 'QUEUED',
    model_version   VARCHAR(64),
    prompt_version  VARCHAR(32),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    
    -- Idempotency constraint: same workspace + snapshot + diff = same analysis
    CONSTRAINT uq_analyses_idempotency UNIQUE (workspace_id, snapshot_id, diff_hash)
);

CREATE INDEX idx_analyses_workspace ON analyses(workspace_id);
CREATE INDEX idx_analyses_status ON analyses(status);

-- ─── questions ───────────────────────────────────────────────────────────────
CREATE TABLE questions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id     UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    concept_name    VARCHAR(255) NOT NULL,
    file_path       VARCHAR(1024) NOT NULL,
    line_start      INTEGER NOT NULL CHECK (line_start > 0),
    line_end        INTEGER NOT NULL CHECK (line_end >= line_start),
    question_text   TEXT NOT NULL,
    question_type   VARCHAR(64) NOT NULL DEFAULT 'situational',
    rubric_spec     JSONB NOT NULL DEFAULT '{}',
    max_score       NUMERIC(5,2) NOT NULL DEFAULT 100.00,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_questions_analysis ON questions(analysis_id);
CREATE INDEX idx_questions_concept ON questions(concept_name);

-- ─── answers ─────────────────────────────────────────────────────────────────
CREATE TABLE answers (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id         UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_answer_text    TEXT NOT NULL,
    time_spent_seconds  INTEGER NOT NULL DEFAULT 0 CHECK (time_spent_seconds >= 0),
    submitted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_answers_question ON answers(question_id);
CREATE INDEX idx_answers_user ON answers(user_id);

-- ─── evaluations ─────────────────────────────────────────────────────────────
CREATE TABLE evaluations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    answer_id           UUID NOT NULL UNIQUE REFERENCES answers(id) ON DELETE CASCADE,
    score               NUMERIC(5,2) NOT NULL CHECK (score >= 0 AND score <= 100),
    passed              BOOLEAN NOT NULL DEFAULT false,
    feedback            TEXT,
    rubric_breakdown    JSONB NOT NULL DEFAULT '{"correct": [], "missing": [], "incorrect": []}',
    evaluated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── concept_states (FSRS-based spaced repetition) ───────────────────────────
CREATE TABLE concept_states (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    concept_name    VARCHAR(255) NOT NULL,
    stability       FLOAT NOT NULL DEFAULT 0.0,
    difficulty      FLOAT NOT NULL DEFAULT 5.0 CHECK (difficulty >= 1.0 AND difficulty <= 10.0),
    retrievability  FLOAT NOT NULL DEFAULT 1.0 CHECK (retrievability >= 0.0 AND retrievability <= 1.0),
    state           fsrs_state NOT NULL DEFAULT 'New',
    last_reviewed_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_concept_per_workspace_user UNIQUE (workspace_id, user_id, concept_name)
);

CREATE INDEX idx_concepts_workspace ON concept_states(workspace_id);
CREATE INDEX idx_concepts_user ON concept_states(user_id);
CREATE INDEX idx_concepts_state ON concept_states(state);

-- ─── spaced_reviews ──────────────────────────────────────────────────────────
CREATE TABLE spaced_reviews (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_state_id    UUID NOT NULL REFERENCES concept_states(id) ON DELETE CASCADE,
    answer_id           UUID REFERENCES answers(id) ON DELETE SET NULL,
    scheduled_for       TIMESTAMPTZ NOT NULL,
    rating              INTEGER CHECK (rating >= 1 AND rating <= 4),
    -- 1=Again, 2=Hard, 3=Good, 4=Easy
    actual_review_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reviews_scheduled ON spaced_reviews(scheduled_for);
CREATE INDEX idx_reviews_concept_state ON spaced_reviews(concept_state_id);

-- ─── usages (token & cost tracking) ──────────────────────────────────────────
CREATE TABLE usages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    analysis_id     UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    tokens_in       INTEGER NOT NULL DEFAULT 0 CHECK (tokens_in >= 0),
    tokens_out      INTEGER NOT NULL DEFAULT 0 CHECK (tokens_out >= 0),
    cost_usd        NUMERIC(10,6) NOT NULL DEFAULT 0.000000,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usages_user ON usages(user_id);
CREATE INDEX idx_usages_timestamp ON usages(timestamp);

COMMIT;
