-- =============================================================================
-- DevComprehend — Synthetic Seed Data for Local Development & Testing
-- Seed: 001_synthetic_seed.sql
-- =============================================================================

BEGIN;

-- ─── Test User ───────────────────────────────────────────────────────────────
INSERT INTO users (id, client_identifier, plan_type, daily_quota_tokens)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'test-user-efe@devcomprehend.local',
    'pro',
    50000
);

-- ─── Test Workspace ──────────────────────────────────────────────────────────
INSERT INTO workspaces (id, user_id, workspace_hash, name, root_path_alias)
VALUES (
    'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'sha256:abc123def456',
    'devcomprehend-main',
    '/home/dev/projects/devcomprehend'
);

-- ─── Test Analysis ───────────────────────────────────────────────────────────
INSERT INTO analyses (id, workspace_id, snapshot_id, diff_hash, status, model_version, prompt_version)
VALUES (
    'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33',
    'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    'snap-a1b2c3d4',
    'sha256:diff789',
    'READY',
    'gpt-4o-2025-08-06',
    'v1.2.0'
);

-- ─── Test Questions ──────────────────────────────────────────────────────────
INSERT INTO questions (id, analysis_id, concept_name, file_path, line_start, line_end, question_text, question_type, rubric_spec, max_score)
VALUES
(
    'd3eebc99-9c0b-4ef8-bb6d-6bb9bd380a44',
    'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33',
    'async-error-handling',
    'src/auth/login.ts',
    12, 19,
    'The refreshToken() call is now awaited and its failure throws an AuthError. What would happen if this function is called from a non-async context?',
    'situational',
    '{"criteria": [{"name": "identifies_promise_rejection", "weight": 30}, {"name": "proposes_error_boundary", "weight": 40}, {"name": "mentions_global_handler", "weight": 30}]}',
    100.00
),
(
    'e4eebc99-9c0b-4ef8-bb6d-6bb9bd380a55',
    'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33',
    'session-management',
    'src/auth/session.ts',
    1, 28,
    'Explain the SRP trade-offs of having SessionManager handle both session creation and validation.',
    'open-ended',
    '{"criteria": [{"name": "defines_srp", "weight": 25}, {"name": "identifies_dual_responsibility", "weight": 35}, {"name": "argues_tradeoff", "weight": 40}]}',
    100.00
);

-- ─── Test Answer ─────────────────────────────────────────────────────────────
INSERT INTO answers (id, question_id, user_id, user_answer_text, time_spent_seconds)
VALUES (
    'f5eebc99-9c0b-4ef8-bb6d-6bb9bd380a66',
    'd3eebc99-9c0b-4ef8-bb6d-6bb9bd380a44',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'If refreshToken is called without await from a non-async context, it returns a Promise object that may reject silently.',
    65
);

-- ─── Test Evaluation ─────────────────────────────────────────────────────────
INSERT INTO evaluations (id, answer_id, score, passed, feedback, rubric_breakdown)
VALUES (
    '06eebc99-9c0b-4ef8-bb6d-6bb9bd380a77',
    'f5eebc99-9c0b-4ef8-bb6d-6bb9bd380a66',
    55.00,
    false,
    'You identified the core issue but missed proposing specific error handling strategies.',
    '{"correct": ["Identified unhandled promise rejection"], "missing": ["No try-catch or .catch() suggestion", "No global handler mention"], "incorrect": []}'
);

-- ─── FSRS Concept States ─────────────────────────────────────────────────────
INSERT INTO concept_states (id, workspace_id, user_id, concept_name, stability, difficulty, retrievability, state, last_reviewed_at)
VALUES
(
    '17eebc99-9c0b-4ef8-bb6d-6bb9bd380a88',
    'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'async-error-handling',
    2.5, 5.2, 0.85, 'Learning',
    '2026-10-03T00:32:50Z'
),
(
    '28eebc99-9c0b-4ef8-bb6d-6bb9bd380a99',
    'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'session-management',
    0.0, 5.0, 1.0, 'New',
    NULL
);

-- ─── Spaced Review Schedule ──────────────────────────────────────────────────
INSERT INTO spaced_reviews (id, concept_state_id, answer_id, scheduled_for, rating)
VALUES (
    '39eebc99-9c0b-4ef8-bb6d-6bb9bd380aaa',
    '17eebc99-9c0b-4ef8-bb6d-6bb9bd380a88',
    'f5eebc99-9c0b-4ef8-bb6d-6bb9bd380a66',
    '2026-10-05T12:00:00Z',
    2  -- Hard
);

-- ─── Usage Log ───────────────────────────────────────────────────────────────
INSERT INTO usages (id, user_id, analysis_id, tokens_in, tokens_out, cost_usd)
VALUES (
    '4aeebc99-9c0b-4ef8-bb6d-6bb9bd380abb',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33',
    1250,
    890,
    0.003210
);

COMMIT;
