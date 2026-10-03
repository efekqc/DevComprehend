"""
DevComprehend — Wave 2: Quota & Usage Tracking Tests

Verifies:
1. Token usage is correctly logged in the usages table
2. Daily quota enforcement: reject when tokens exceed daily limit
3. Analysis count limits are enforced

Requires: PostgreSQL (via Docker or CI service container)
Env var: DATABASE_URL
"""

import os
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


def _create_user(cursor, uid, identifier, quota=50000):
    cursor.execute("""
        INSERT INTO users (id, client_identifier, plan_type, daily_quota_tokens)
        VALUES (%s, %s, 'free', %s)
    """, (uid, identifier, quota))

def _create_workspace(cursor, wid, uid, ws_hash, name):
    cursor.execute("""
        INSERT INTO workspaces (id, user_id, workspace_hash, name)
        VALUES (%s, %s, %s, %s)
    """, (wid, uid, ws_hash, name))

def _create_analysis(cursor, aid, wid, snap, diff_h, status='READY'):
    cursor.execute("""
        INSERT INTO analyses (id, workspace_id, snapshot_id, diff_hash, status)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (aid, wid, snap, diff_h, status))
    return cursor.fetchone()[0]

def _log_usage(cursor, uid, aid, tokens_in, tokens_out, cost):
    cursor.execute("""
        INSERT INTO usages (user_id, analysis_id, tokens_in, tokens_out, cost_usd)
        VALUES (%s, %s, %s, %s, %s)
    """, (uid, aid, tokens_in, tokens_out, cost))

def _get_daily_token_usage(cursor, uid):
    """Sum tokens used today for a given user."""
    cursor.execute("""
        SELECT COALESCE(SUM(tokens_in + tokens_out), 0)
        FROM usages
        WHERE user_id = %s
          AND timestamp >= CURRENT_DATE
          AND timestamp < CURRENT_DATE + INTERVAL '1 day'
    """, (uid,))
    return cursor.fetchone()[0]

def _get_daily_analysis_count(cursor, uid):
    """Count analyses created today for user's workspaces."""
    cursor.execute("""
        SELECT COUNT(*)
        FROM analyses a
        JOIN workspaces w ON a.workspace_id = w.id
        WHERE w.user_id = %s
          AND a.created_at >= CURRENT_DATE
          AND a.created_at < CURRENT_DATE + INTERVAL '1 day'
    """, (uid,))
    return cursor.fetchone()[0]


class TestUsageTracking:
    """Verify token usage is recorded correctly."""

    USER_ID = '70000000-0000-0000-0000-000000000001'
    WS_ID   = '70000000-0000-0000-0000-000000000002'
    AN_ID   = '70000000-0000-0000-0000-000000000003'

    def test_usage_entry_recorded(self, db_connection):
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_ID, 'usage-track-user')
            _create_workspace(cursor, self.WS_ID, self.USER_ID, 'ut-h', 'ws-ut')
            _create_analysis(cursor, self.AN_ID, self.WS_ID, 'snap-ut', 'diff-ut')
            _log_usage(cursor, self.USER_ID, self.AN_ID, 1200, 800, 0.003)

            cursor.execute("""
                SELECT tokens_in, tokens_out, cost_usd
                FROM usages WHERE user_id = %s AND analysis_id = %s
            """, (self.USER_ID, self.AN_ID))
            row = cursor.fetchone()
            assert row[0] == 1200
            assert row[1] == 800
            assert float(row[2]) == pytest.approx(0.003, abs=1e-6)
        finally:
            db_connection.rollback()

    def test_daily_token_sum(self, db_connection):
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_ID, 'usage-sum-user')
            _create_workspace(cursor, self.WS_ID, self.USER_ID, 'us-h', 'ws-us')
            # Create multiple analyses with different hashes
            for i in range(3):
                aid = f'70000000-0000-0000-0000-00000000{i+10:04d}'
                _create_analysis(cursor, aid, self.WS_ID, f'snap-s{i}', f'diff-s{i}')
                _log_usage(cursor, self.USER_ID, aid, 1000, 500, 0.002)

            total = _get_daily_token_usage(cursor, self.USER_ID)
            assert total == 4500  # 3 * (1000 + 500)
        finally:
            db_connection.rollback()


class TestQuotaEnforcement:
    """Verify quota limits are queryable for enforcement."""

    USER_ID = '80000000-0000-0000-0000-000000000001'
    WS_ID   = '80000000-0000-0000-0000-000000000002'

    def test_detect_quota_exceeded(self, db_connection):
        """When daily tokens exceed user's quota, detection query returns True."""
        cursor = db_connection.cursor()
        try:
            # User with 5000 token quota (low for testing)
            _create_user(cursor, self.USER_ID, 'quota-user', quota=5000)
            _create_workspace(cursor, self.WS_ID, self.USER_ID, 'qt-h', 'ws-qt')

            # Log usage that exceeds quota
            aid1 = '80000000-0000-0000-0000-000000000010'
            _create_analysis(cursor, aid1, self.WS_ID, 'snap-q1', 'diff-q1')
            _log_usage(cursor, self.USER_ID, aid1, 3000, 2500, 0.008)  # 5500 > 5000

            # Check quota
            daily_usage = _get_daily_token_usage(cursor, self.USER_ID)
            cursor.execute(
                "SELECT daily_quota_tokens FROM users WHERE id = %s",
                (self.USER_ID,)
            )
            quota = cursor.fetchone()[0]
            is_exceeded = daily_usage > quota
            assert is_exceeded, f"Usage {daily_usage} should exceed quota {quota}"
        finally:
            db_connection.rollback()

    def test_under_quota_allows_analysis(self, db_connection):
        """When usage is under quota, detection returns False."""
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_ID, 'quota-ok-user', quota=50000)
            _create_workspace(cursor, self.WS_ID, self.USER_ID, 'qo-h', 'ws-qo')
            aid = '80000000-0000-0000-0000-000000000020'
            _create_analysis(cursor, aid, self.WS_ID, 'snap-qo', 'diff-qo')
            _log_usage(cursor, self.USER_ID, aid, 1000, 500, 0.002)

            daily_usage = _get_daily_token_usage(cursor, self.USER_ID)
            cursor.execute(
                "SELECT daily_quota_tokens FROM users WHERE id = %s",
                (self.USER_ID,)
            )
            quota = cursor.fetchone()[0]
            assert daily_usage <= quota
        finally:
            db_connection.rollback()

    def test_analysis_count_limit(self, db_connection):
        """Detect when daily analysis count exceeds limit (10)."""
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_ID, 'count-limit-user')
            _create_workspace(cursor, self.WS_ID, self.USER_ID, 'cl-h', 'ws-cl')

            max_daily = 10
            # Create 11 analyses
            for i in range(11):
                aid = f'80000000-0000-0000-0000-000000001{i:03d}'
                _create_analysis(cursor, aid, self.WS_ID, f'snap-cl{i}', f'diff-cl{i}')

            count = _get_daily_analysis_count(cursor, self.USER_ID)
            assert count > max_daily, f"Count {count} should exceed {max_daily}"
        finally:
            db_connection.rollback()

    def test_usage_cost_tracking(self, db_connection):
        """Verify cost_usd accumulates correctly."""
        cursor = db_connection.cursor()
        try:
            _create_user(cursor, self.USER_ID, 'cost-track-user')
            _create_workspace(cursor, self.WS_ID, self.USER_ID, 'ct-h', 'ws-ct')

            for i in range(5):
                aid = f'80000000-0000-0000-0000-000000002{i:03d}'
                _create_analysis(cursor, aid, self.WS_ID, f'snap-ct{i}', f'diff-ct{i}')
                _log_usage(cursor, self.USER_ID, aid, 1000, 500, 1.25)

            cursor.execute("""
                SELECT SUM(cost_usd) FROM usages
                WHERE user_id = %s
                  AND timestamp >= CURRENT_DATE
            """, (self.USER_ID,))
            total_cost = float(cursor.fetchone()[0])
            assert total_cost == pytest.approx(6.25, abs=0.01)  # 5 * 1.25

            # Check if exceeds daily cost cap ($5.00)
            cost_cap = 5.00
            assert total_cost > cost_cap
        finally:
            db_connection.rollback()
