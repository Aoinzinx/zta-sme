"""Initial schema: users, roles, policies, audit_log, revoked_tokens"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, INET


def upgrade():
    op.execute("CREATE TYPE effect_enum AS ENUM ('permit', 'deny')")
    op.execute("CREATE TYPE decision_enum AS ENUM ('permit', 'deny')")

    op.create_table("roles",
        sa.Column("role_id", UUID(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.Text()),
        sa.PrimaryKeyConstraint("role_id"),
        sa.UniqueConstraint("name")
    )

    op.create_table("users",
        sa.Column("user_id", UUID(), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role_id", UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(255)),
        sa.Column("session_created_at", sa.TIMESTAMP()),
        sa.ForeignKeyConstraint(["role_id"], ["roles.role_id"]),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("username")
    )

    op.create_table("policies",
        sa.Column("policy_id", UUID(), nullable=False),
        sa.Column("role_binding", sa.String(64), nullable=False),
        sa.Column("resource_pattern", sa.String(255), nullable=False),
        sa.Column("http_method", sa.String(10), nullable=False),
        sa.Column("effect", sa.Enum("permit", "deny", name="effect_enum"), nullable=False),
        sa.Column("priority", sa.Integer(), default=100, nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.PrimaryKeyConstraint("policy_id")
    )

    op.create_table("audit_log",
        sa.Column("log_id", UUID(), nullable=False),
        sa.Column("timestamp", sa.TIMESTAMP(), nullable=False),
        sa.Column("subject_id", UUID()),
        sa.Column("resource", sa.String(255), nullable=False),
        sa.Column("http_method", sa.String(10), nullable=False),
        sa.Column("policy_decision", sa.Enum("permit", "deny", name="decision_enum"), nullable=False),
        sa.Column("response_latency_ms", sa.Integer(), nullable=False),
        sa.Column("client_ip", INET(), nullable=False),
        sa.Column("rule_id", UUID()),
        sa.PrimaryKeyConstraint("log_id")
    )
    op.create_index("idx_audit_timestamp", "audit_log", ["timestamp"])

    op.create_table("revoked_tokens",
        sa.Column("jti", sa.String(255), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint("jti")
    )

    # NOTE: After migration, run as superuser:
    # REVOKE UPDATE, DELETE ON audit_log FROM ztapp_user;

    # Seed default roles
    op.execute("""
        INSERT INTO roles (role_id, name, description) VALUES
        (gen_random_uuid(), 'Administrator', 'Full access to all resources and management functions'),
        (gen_random_uuid(), 'Operator', 'Read and write access to business resources'),
        (gen_random_uuid(), 'Viewer', 'Read-only access to business resources');
    """)

    # Seed default policy rules
    op.execute("""
        INSERT INTO policies (policy_id, role_binding, resource_pattern, http_method, effect, priority)
        VALUES
        (gen_random_uuid(), 'Administrator', '/*',      '*',   'permit', 1000),
        (gen_random_uuid(), 'Operator',      '/aws/*',  '*',   'permit',  500),
        (gen_random_uuid(), 'Operator',      '/azure/*','*',   'permit',  500),
        (gen_random_uuid(), 'Viewer',        '/aws/*',  'GET', 'permit',  300),
        (gen_random_uuid(), 'Viewer',        '/azure/*','GET', 'permit',  300),
        (gen_random_uuid(), '*',             '/admin/*','*',   'deny',   2000);
    """)


def downgrade():
    op.drop_table("revoked_tokens")
    op.drop_table("audit_log")
    op.drop_table("policies")
    op.drop_table("users")
    op.drop_table("roles")
    op.execute("DROP TYPE IF EXISTS effect_enum")
    op.execute("DROP TYPE IF EXISTS decision_enum")
