"""
DevComprehend — Database Migration Integration Tests

Verifies that the DDL migration runs cleanly on PostgreSQL and that
constraints (unique, FK, check) behave as expected.

Requires: PostgreSQL (via Docker or CI service container)
Env var: DATABASE_URL (defaults to local docker-compose setup)
"""

import os
import pytest
from pathlib import Path

try:
    import psycopg2
    import psycopg2.errors
except ImportError:
    pytest.skip("psycopg2 not available", allow_module_level=True)

# ─── Configuration ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = PROJECT_ROOT / "infra" / "db" / "migrations" / "001_initial_schema.sql"
SEED_PATH = PROJECT_ROOT / "infra" / "db" / "seeds" / "001_synthetic_seed.sql"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://dc_admin:dc_local_pass_2026@localhost:5433/devcomprehend"
)

def _try_connect():
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=1)
        conn.close()
        return True
    except Exception:
        return False

pytestmark = pytest.mark.skipif(not _try_connect(), reason="PostgreSQL not available")



@pytest.fixture(scope="module")
def db_connection():
    """Create a database connection for the test module."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    yield conn
    conn.close()


@pytest.fixture(scope="module", autouse=True)
def apply_migration(db_connection):
    """Apply the migration SQL before tests run."""
    cursor = db_connection.cursor()
    # Drop all tables to start fresh (reverse dependency order)
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

    # Apply migration
    with open(MIGRATION_PATH, "r", encoding="utf-8") as f:
        sql = f.read()
    cursor.execute(sql)
    db_connection.commit()
    yield


class TestMigrationApplied:
    """Verify that migration creates all expected tables."""

    EXPECTED_TABLES = [
        "users", "workspaces", "analyses", "questions",
        "answers", "evaluations", "concept_states",
        "spaced_reviews", "usages"
    ]

    @pytest.mark.parametrize("table_name", EXPECTED_TABLES)
    def test_table_exists(self, db_connection, table_name):
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (table_name,))
        exists = cursor.fetchone()[0]
        assert exists, f"Table '{table_name}' was not created"


class TestUniqueConstraints:
    """Verify idempotency and uniqueness constraints."""

    def test_analyses_idempotency_constraint(self, db_connection):
        """Inserting duplicate (workspace_id, snapshot_id, diff_hash) should fail."""
        cursor = db_connection.cursor()
        try:
            # Insert first
            cursor.execute("""
                INSERT INTO users (id, client_identifier) VALUES
                ('00000000-0000-0000-0000-000000000001', 'unique-test-user-1')
            """)
            cursor.execute("""
                INSERT INTO workspaces (id, user_id, workspace_hash, name) VALUES
                ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'hash1', 'test-ws')
            """)
            cursor.execute("""
                INSERT INTO analyses (workspace_id, snapshot_id, diff_hash, status) VALUES
                ('00000000-0000-0000-0000-000000000002', 'snap-1', 'diff-1', 'QUEUED')
            """)
            # Insert duplicate — should raise
            with pytest.raises(psycopg2.errors.UniqueViolation):
                cursor.execute("""
                    INSERT INTO analyses (workspace_id, snapshot_id, diff_hash, status) VALUES
                    ('00000000-0000-0000-0000-000000000002', 'snap-1', 'diff-1', 'QUEUED')
                """)
        finally:
            db_connection.rollback()

    def test_user_client_identifier_unique(self, db_connection):
        """Duplicate client_identifier should fail."""
        cursor = db_connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (id, client_identifier) VALUES
                ('00000000-0000-0000-0000-000000000010', 'dup-user@test')
            """)
            with pytest.raises(psycopg2.errors.UniqueViolation):
                cursor.execute("""
                    INSERT INTO users (id, client_identifier) VALUES
                    ('00000000-0000-0000-0000-000000000011', 'dup-user@test')
                """)
        finally:
            db_connection.rollback()


class TestForeignKeyBehavior:
    """Verify CASCADE delete behavior."""

    def test_deleting_user_cascades_to_workspaces(self, db_connection):
        cursor = db_connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (id, client_identifier) VALUES
                ('00000000-0000-0000-0000-000000000020', 'cascade-test-user')
            """)
            cursor.execute("""
                INSERT INTO workspaces (id, user_id, workspace_hash, name) VALUES
                ('00000000-0000-0000-0000-000000000021', '00000000-0000-0000-0000-000000000020', 'hash2', 'ws-cascade')
            """)
            # Delete user
            cursor.execute("DELETE FROM users WHERE id = '00000000-0000-0000-0000-000000000020'")
            # Workspace should be gone
            cursor.execute("SELECT COUNT(*) FROM workspaces WHERE id = '00000000-0000-0000-0000-000000000021'")
            count = cursor.fetchone()[0]
            assert count == 0, "Workspace should have been cascade-deleted"
        finally:
            db_connection.rollback()


class TestCheckConstraints:
    """Verify CHECK constraints."""

    def test_score_must_be_between_0_and_100(self, db_connection):
        cursor = db_connection.cursor()
        try:
            # Setup required records
            cursor.execute("""
                INSERT INTO users (id, client_identifier) VALUES
                ('00000000-0000-0000-0000-000000000030', 'check-test-user')
            """)
            cursor.execute("""
                INSERT INTO workspaces (id, user_id, workspace_hash, name) VALUES
                ('00000000-0000-0000-0000-000000000031', '00000000-0000-0000-0000-000000000030', 'hash3', 'ws-check')
            """)
            cursor.execute("""
                INSERT INTO analyses (id, workspace_id, snapshot_id, diff_hash, status) VALUES
                ('00000000-0000-0000-0000-000000000032', '00000000-0000-0000-0000-000000000031', 'snap-c', 'diff-c', 'READY')
            """)
            cursor.execute("""
                INSERT INTO questions (id, analysis_id, concept_name, file_path, line_start, line_end, question_text) VALUES
                ('00000000-0000-0000-0000-000000000033', '00000000-0000-0000-0000-000000000032', 'test', 'test.ts', 1, 10, 'Test?')
            """)
            cursor.execute("""
                INSERT INTO answers (id, question_id, user_id, user_answer_text) VALUES
                ('00000000-0000-0000-0000-000000000034', '00000000-0000-0000-0000-000000000033', '00000000-0000-0000-0000-000000000030', 'Test answer')
            """)
            with pytest.raises(psycopg2.errors.CheckViolation):
                cursor.execute("""
                    INSERT INTO evaluations (answer_id, score, passed) VALUES
                    ('00000000-0000-0000-0000-000000000034', 150.00, true)
                """)
        finally:
            db_connection.rollback()

    def test_rating_must_be_1_to_4(self, db_connection):
        cursor = db_connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (id, client_identifier) VALUES
                ('00000000-0000-0000-0000-000000000040', 'rating-test-user')
            """)
            cursor.execute("""
                INSERT INTO workspaces (id, user_id, workspace_hash, name) VALUES
                ('00000000-0000-0000-0000-000000000041', '00000000-0000-0000-0000-000000000040', 'hash4', 'ws-rating')
            """)
            cursor.execute("""
                INSERT INTO concept_states (id, workspace_id, user_id, concept_name) VALUES
                ('00000000-0000-0000-0000-000000000042', '00000000-0000-0000-0000-000000000041', '00000000-0000-0000-0000-000000000040', 'test-concept')
            """)
            with pytest.raises(psycopg2.errors.CheckViolation):
                cursor.execute("""
                    INSERT INTO spaced_reviews (concept_state_id, scheduled_for, rating) VALUES
                    ('00000000-0000-0000-0000-000000000042', NOW(), 5)
                """)
        finally:
            db_connection.rollback()


class TestSeedData:
    """Verify synthetic seed data loads correctly."""

    def test_seed_loads_without_error(self, db_connection):
        cursor = db_connection.cursor()
        try:
            with open(SEED_PATH, "r", encoding="utf-8") as f:
                sql = f.read()
            cursor.execute(sql)
            db_connection.commit()

            # Verify counts
            for table, expected in [("users", 1), ("workspaces", 1), ("analyses", 1), ("questions", 2), ("concept_states", 2)]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                assert count >= expected, f"Expected at least {expected} rows in {table}, got {count}"
        finally:
            db_connection.rollback()
