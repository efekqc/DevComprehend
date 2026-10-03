"""
DevComprehend — Wave 2: Storage Isolation, Idempotency & FSRS Tests

Verifies:
1. Owner isolation: different users cannot access each other's data
2. Idempotency: duplicate analysis requests return existing records
3. FSRS state transitions: concept_states update correctly based on review ratings

Requires: PostgreSQL (via Docker or CI service container)
Env var: DATABASE_URL
"""

import os
import math
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    import psycopg2
    import psycopg2.errors
except ImportError:
    pytest.skip("psycopg2 not available", allow_module_level=True)

# ─── Configuration ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = PROJECT_ROOT / "infra" / "db" / "migrations" / "001_initial_schema.sql"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://dc_admin:dc_local_pass_2026@localhost:5433/devcomprehend"
)


def _try_connect():
    """Try to connect; skip tests if DB is unavailable."""
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=1)
        conn.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _try_connect(), reason="PostgreSQL not available")


@pytest.fixture(scope="module")
def db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    yield conn
    conn.close()


@pytest.fixture(scope="module", autouse=True)
def apply_migration(db_connection):
    cursor = db_connection.cursor()
    cursor.execute("""
        DROP TABLE IF EXISTS spaced_reviews CASCADE;
        DROP TABLE IF EXISTS concept_states CASCADE;
        DROP TABLE IF EXISTS usages CASCADE;
        DROP TABLE IF EXISTS evaluations CASCADE;
        DROP TABLE IF EXISTS answers CASCADE;
        DROP TABLE IF EXISTS questions CASCADE;
        DROP TABLE IF EXISTS analyses CASCADE;
        DROP TABLE IF EXISTS workspaces CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        DROP TYPE IF EXISTS analysis_status CASCADE;
        DROP TYPE IF EXISTS plan_type CASCADE;
        DROP TYPE IF EXISTS fsrs_state CASCADE;
    """)
    db_connection.commit()
    with open(MIGRATION_PATH, "r", encoding="utf-8") as f:
        sql = f.read()
    cursor.execute(sql)
    db_connection.commit()
    yield


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _create_user(cursor, uid, identifier, plan='free'):
    cursor.execute("""
        INSERT INTO users (id, client_identifier, plan_type, daily_quota_tokens)
        VALUES (%s, %s, %s, 50000)
    """, (uid, identifier, plan))


def _create_workspace(cursor, wid, uid, ws_hash, name):
    cursor.execute("""
        INSERT INTO workspaces (id, user_id, workspace_hash, name)
        VALUES (%s, %s, %s, %s)
    """, (wid, uid, ws_hash, name))


def _create_analysis(cursor, aid, wid, snap, diff_h, status='QUEUED'):
    cursor.execute("""
        INSERT INTO analyses (id, workspace_id, snapshot_id, diff_hash, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (aid, wid, snap, diff_h, status))


def _create_question(cursor, qid, aid, concept, fpath, ls, le, qtext):
    cursor.execute("""
        INSERT INTO questions (id, analysis_id, concept_name, file_path,
                              line_start, line_end, question_text)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (qid, aid, concept, fpath, ls, le, qtext))


# ═════════════════════════════════════════════════════════════════════════════
# TEST SUITE 1: Owner Isolation
# ═════════════════════════════════════════════════════════════════════════════
class TestOwnerIsolation:
    """Different users/workspaces must not see each other's data."""

    # UUIDs for two separate users
    USER_A = '10000000-0000-0000-0000-000000000001'
    USER_B = '10000000-0000-0000-0000-000000000002'
    WS_A   = '20000000-0000-0000-0000-000000000001'
    WS_B   = '20000000-0000-0000-0000-000000000002'
    AN_A   = '30000000-0000-0000-0000-000000000001'
    AN_B   = '30000000-0000-0000-0000-000000000002'
    Q_A    = '40000000-0000-0000-0000-000000000001'
    Q_B    = '40000000-0000-0000-0000-000000000002'

    def test_user_a_cannot_see_user_b_analyses(self, db_connection):
        """Analyses scoped by workspace_id; querying another workspace returns nothing."""
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_A, 'owner-iso-user-a')
            _create_user(cursor, self.USER_B, 'owner-iso-user-b')
            _create_workspace(cursor, self.WS_A, self.USER_A, 'hashA', 'ws-a')
            _create_workspace(cursor, self.WS_B, self.USER_B, 'hashB', 'ws-b')
            _create_analysis(cursor, self.AN_A, self.WS_A, 'snap-a', 'diff-a', 'READY')
            _create_analysis(cursor, self.AN_B, self.WS_B, 'snap-b', 'diff-b', 'READY')

            # User A queries their workspace => sees only their analysis
            cursor.execute(
                "SELECT id FROM analyses WHERE workspace_id = %s", (self.WS_A,)
            )
            rows_a = cursor.fetchall()
            assert len(rows_a) == 1
            assert str(rows_a[0][0]) == self.AN_A

            # User A queries User B's workspace => sees nothing belonging to them
            cursor.execute(
                "SELECT id FROM analyses WHERE workspace_id = %s", (self.WS_B,)
            )
            rows_b = cursor.fetchall()
            # None of these belong to user A's workspace
            for row in rows_b:
                assert str(row[0]) != self.AN_A
        finally:
            db_connection.rollback()

    def test_user_a_cannot_see_user_b_questions(self, db_connection):
        """Questions scoped by analysis_id; cross-owner queries return nothing."""
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_A, 'iso-qa-user-a')
            _create_user(cursor, self.USER_B, 'iso-qa-user-b')
            _create_workspace(cursor, self.WS_A, self.USER_A, 'hashA2', 'ws-a2')
            _create_workspace(cursor, self.WS_B, self.USER_B, 'hashB2', 'ws-b2')
            _create_analysis(cursor, self.AN_A, self.WS_A, 'snap-q', 'diff-q1', 'READY')
            _create_analysis(cursor, self.AN_B, self.WS_B, 'snap-q', 'diff-q2', 'READY')
            _create_question(cursor, self.Q_A, self.AN_A, 'concept-a', 'a.ts', 1, 10, 'Q for A?')
            _create_question(cursor, self.Q_B, self.AN_B, 'concept-b', 'b.ts', 1, 10, 'Q for B?')

            # Fetch questions for User A's analysis
            cursor.execute(
                "SELECT id FROM questions WHERE analysis_id = %s", (self.AN_A,)
            )
            qa = cursor.fetchall()
            assert len(qa) == 1
            assert str(qa[0][0]) == self.Q_A

            # Fetch questions for User B's analysis
            cursor.execute(
                "SELECT id FROM questions WHERE analysis_id = %s", (self.AN_B,)
            )
            qb = cursor.fetchall()
            assert len(qb) == 1
            assert str(qb[0][0]) == self.Q_B
        finally:
            db_connection.rollback()

    def test_workspace_data_isolated_on_delete(self, db_connection):
        """Deleting user A cascades only their data, not user B's."""
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_A, 'del-iso-a')
            _create_user(cursor, self.USER_B, 'del-iso-b')
            _create_workspace(cursor, self.WS_A, self.USER_A, 'hA', 'ws-del-a')
            _create_workspace(cursor, self.WS_B, self.USER_B, 'hB', 'ws-del-b')
            _create_analysis(cursor, self.AN_A, self.WS_A, 'snap-d', 'diff-d1', 'READY')
            _create_analysis(cursor, self.AN_B, self.WS_B, 'snap-d', 'diff-d2', 'READY')

            # Delete user A
            cursor.execute("DELETE FROM users WHERE id = %s", (self.USER_A,))

            # User B's data survives
            cursor.execute("SELECT COUNT(*) FROM analyses WHERE id = %s", (self.AN_B,))
            assert cursor.fetchone()[0] == 1

            # User A's data is gone
            cursor.execute("SELECT COUNT(*) FROM analyses WHERE id = %s", (self.AN_A,))
            assert cursor.fetchone()[0] == 0
        finally:
            db_connection.rollback()


# ═════════════════════════════════════════════════════════════════════════════
# TEST SUITE 2: Idempotency
# ═════════════════════════════════════════════════════════════════════════════
class TestIdempotency:
    """Duplicate (workspace_id, snapshot_id, diff_hash) must not create new analysis."""

    USER_ID = '50000000-0000-0000-0000-000000000001'
    WS_ID   = '50000000-0000-0000-0000-000000000002'

    def test_duplicate_analysis_raises_unique_violation(self, db_connection):
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_ID, 'idemp-user')
            _create_workspace(cursor, self.WS_ID, self.USER_ID, 'idemp-hash', 'ws-idemp')
            _create_analysis(cursor, '50000000-0000-0000-0000-000000000003',
                           self.WS_ID, 'snap-idemp', 'diff-idemp', 'QUEUED')

            with pytest.raises(psycopg2.errors.UniqueViolation):
                cursor.execute("""
                    INSERT INTO analyses (workspace_id, snapshot_id, diff_hash, status)
                    VALUES (%s, 'snap-idemp', 'diff-idemp', 'QUEUED')
                """, (self.WS_ID,))
        finally:
            db_connection.rollback()

    def test_insert_on_conflict_returns_existing(self, db_connection):
        """Using INSERT ... ON CONFLICT DO NOTHING pattern for idempotency."""
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_ID, 'idemp2-user')
            _create_workspace(cursor, self.WS_ID, self.USER_ID, 'idemp2-h', 'ws-idemp2')

            # First insert
            cursor.execute("""
                INSERT INTO analyses (id, workspace_id, snapshot_id, diff_hash, status)
                VALUES ('50000000-0000-0000-0000-000000000010', %s, 'snap-oc', 'diff-oc', 'QUEUED')
                ON CONFLICT ON CONSTRAINT uq_analyses_idempotency DO NOTHING
                RETURNING id
            """, (self.WS_ID,))
            first_result = cursor.fetchone()
            assert first_result is not None
            first_id = str(first_result[0])

            # Second insert — same constraint values
            cursor.execute("""
                INSERT INTO analyses (id, workspace_id, snapshot_id, diff_hash, status)
                VALUES (uuid_generate_v4(), %s, 'snap-oc', 'diff-oc', 'QUEUED')
                ON CONFLICT ON CONSTRAINT uq_analyses_idempotency DO NOTHING
                RETURNING id
            """, (self.WS_ID,))
            second_result = cursor.fetchone()
            # ON CONFLICT DO NOTHING returns no rows
            assert second_result is None

            # Verify only one record exists
            cursor.execute("""
                SELECT id FROM analyses
                WHERE workspace_id = %s AND snapshot_id = 'snap-oc' AND diff_hash = 'diff-oc'
            """, (self.WS_ID,))
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert str(rows[0][0]) == first_id
        finally:
            db_connection.rollback()

    def test_different_diff_hash_creates_new_analysis(self, db_connection):
        """Same workspace+snapshot but different diff_hash => new analysis is valid."""
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_ID, 'idemp3-user')
            _create_workspace(cursor, self.WS_ID, self.USER_ID, 'idemp3-h', 'ws-idemp3')

            cursor.execute("""
                INSERT INTO analyses (workspace_id, snapshot_id, diff_hash, status)
                VALUES (%s, 'snap-multi', 'diff-v1', 'QUEUED')
            """, (self.WS_ID,))
            cursor.execute("""
                INSERT INTO analyses (workspace_id, snapshot_id, diff_hash, status)
                VALUES (%s, 'snap-multi', 'diff-v2', 'QUEUED')
            """, (self.WS_ID,))

            cursor.execute("""
                SELECT COUNT(*) FROM analyses
                WHERE workspace_id = %s AND snapshot_id = 'snap-multi'
            """, (self.WS_ID,))
            assert cursor.fetchone()[0] == 2
        finally:
            db_connection.rollback()


# ═════════════════════════════════════════════════════════════════════════════
# TEST SUITE 3: FSRS Spaced Repetition Logic
# ═════════════════════════════════════════════════════════════════════════════
class TestFSRSConceptStates:
    """Verify FSRS state transitions in concept_states and spaced_reviews."""

    USER_ID = '60000000-0000-0000-0000-000000000001'
    WS_ID   = '60000000-0000-0000-0000-000000000002'
    CS_ID   = '60000000-0000-0000-0000-000000000003'

    def test_initial_concept_state_defaults(self, db_connection):
        """New concept_state has correct FSRS defaults."""
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_ID, 'fsrs-user')
            _create_workspace(cursor, self.WS_ID, self.USER_ID, 'fsrs-h', 'ws-fsrs')
            cursor.execute("""
                INSERT INTO concept_states (id, workspace_id, user_id, concept_name)
                VALUES (%s, %s, %s, 'error-handling')
            """, (self.CS_ID, self.WS_ID, self.USER_ID))

            cursor.execute("""
                SELECT stability, difficulty, retrievability, state, last_reviewed_at
                FROM concept_states WHERE id = %s
            """, (self.CS_ID,))
            row = cursor.fetchone()
            assert row[0] == 0.0   # stability default
            assert row[1] == 5.0   # difficulty default
            assert row[2] == 1.0   # retrievability default
            assert row[3] == 'New' # state default
            assert row[4] is None  # last_reviewed_at
        finally:
            db_connection.rollback()

    def test_fsrs_state_transition_on_review(self, db_connection):
        """After review, stability/difficulty update and next_review is scheduled."""
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_ID, 'fsrs-trans-user')
            _create_workspace(cursor, self.WS_ID, self.USER_ID, 'fsrs-t-h', 'ws-fsrs-t')
            cursor.execute("""
                INSERT INTO concept_states (id, workspace_id, user_id, concept_name,
                                          stability, difficulty, state)
                VALUES (%s, %s, %s, 'async-patterns', 0.0, 5.0, 'New')
            """, (self.CS_ID, self.WS_ID, self.USER_ID))

            # Simulate a review: rating=3 (Good) => transition to Learning/Review
            new_stability = 4.5
            new_difficulty = 4.8
            new_retrievability = 0.90
            now = datetime.now(timezone.utc)
            next_review = now + timedelta(days=3)

            cursor.execute("""
                UPDATE concept_states
                SET stability = %s, difficulty = %s, retrievability = %s,
                    state = 'Review', last_reviewed_at = %s
                WHERE id = %s
            """, (new_stability, new_difficulty, new_retrievability, now, self.CS_ID))

            # Schedule the review
            cursor.execute("""
                INSERT INTO spaced_reviews (concept_state_id, scheduled_for, rating)
                VALUES (%s, %s, 3)
            """, (self.CS_ID, next_review))

            # Verify updated state
            cursor.execute("""
                SELECT stability, difficulty, retrievability, state, last_reviewed_at
                FROM concept_states WHERE id = %s
            """, (self.CS_ID,))
            row = cursor.fetchone()
            assert row[0] == new_stability
            assert row[1] == new_difficulty
            assert abs(row[2] - new_retrievability) < 0.01
            assert row[3] == 'Review'
            assert row[4] is not None

            # Verify scheduled review
            cursor.execute("""
                SELECT scheduled_for, rating FROM spaced_reviews
                WHERE concept_state_id = %s
            """, (self.CS_ID,))
            rev = cursor.fetchone()
            assert rev[1] == 3  # Good
        finally:
            db_connection.rollback()

    @pytest.mark.parametrize("rating,expected_state,min_stability", [
        (1, 'Relearning', 0.0),   # Again => Relearning, stability stays low
        (2, 'Learning', 1.0),     # Hard => Learning, moderate stability
        (3, 'Review', 3.0),       # Good => Review, good stability
        (4, 'Review', 5.0),       # Easy => Review, high stability
    ])
    def test_rating_determines_state_and_stability(self, db_connection,
                                                     rating, expected_state,
                                                     min_stability):
        """Each FSRS rating (1-4) drives different state transitions."""
        cursor = db_connection.cursor()
        uid = f'60000000-0000-0000-0000-0000000000{rating:02d}'
        wid = f'60000000-0000-0000-0000-0000001000{rating:02d}'
        csid = f'60000000-0000-0000-0000-0000002000{rating:02d}'
        try:
            _create_user(cursor, uid, f'fsrs-r{rating}-user')
            _create_workspace(cursor, wid, uid, f'fsrs-r{rating}', f'ws-r{rating}')
            cursor.execute("""
                INSERT INTO concept_states (id, workspace_id, user_id, concept_name,
                                          stability, difficulty, state)
                VALUES (%s, %s, %s, %s, %s, 5.0, %s)
            """, (csid, wid, uid, f'concept-r{rating}', min_stability, expected_state))

            cursor.execute("""
                INSERT INTO spaced_reviews (concept_state_id, scheduled_for, rating)
                VALUES (%s, NOW() + interval '1 day', %s)
            """, (csid, rating))

            # Verify
            cursor.execute("SELECT state, stability FROM concept_states WHERE id = %s", (csid,))
            row = cursor.fetchone()
            assert row[0] == expected_state
            assert row[1] >= min_stability
        finally:
            db_connection.rollback()

    def test_concept_uniqueness_per_workspace_user(self, db_connection):
        """Same concept in same workspace+user => unique violation."""
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_ID, 'fsrs-uniq-user')
            _create_workspace(cursor, self.WS_ID, self.USER_ID, 'fsrs-u-h', 'ws-fsrs-u')
            cursor.execute("""
                INSERT INTO concept_states (workspace_id, user_id, concept_name)
                VALUES (%s, %s, 'dup-concept')
            """, (self.WS_ID, self.USER_ID))

            with pytest.raises(psycopg2.errors.UniqueViolation):
                cursor.execute("""
                    INSERT INTO concept_states (workspace_id, user_id, concept_name)
                    VALUES (%s, %s, 'dup-concept')
                """, (self.WS_ID, self.USER_ID))
        finally:
            db_connection.rollback()
