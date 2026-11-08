from datetime import datetime
from sqlalchemy import create_engine, String, Float, Integer, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship
from .core import settings, now_utc

connect_args = {'check_same_thread': False} if settings.database_url.startswith('sqlite') else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(30), default='reviewer')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(128))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    user: Mapped['User'] = relationship()

class GoogleCredential(Base):
    __tablename__ = 'google_credentials'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True)
    email: Mapped[str] = mapped_column(String(320), default='')
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

class OAuthState(Base):
    __tablename__ = 'oauth_states'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    expires_at: Mapped[datetime] = mapped_column(DateTime)

class WorkflowRun(Base):
    __tablename__ = 'workflow_runs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default='queued')
    counts: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

class Lead(Base):
    __tablename__ = 'leads'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(160), unique=True)
    first_name: Mapped[str] = mapped_column(String(80))
    company: Mapped[str] = mapped_column(String(160), default='')
    title: Mapped[str] = mapped_column(String(160), default='')
    source: Mapped[str] = mapped_column(String(40))
    post_url: Mapped[str] = mapped_column(String(500))
    excerpt: Mapped[str] = mapped_column(Text)
    fit_score: Mapped[float] = mapped_column(Float)
    intent_score: Mapped[float] = mapped_column(Float)
    total_score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40), default='drafted')
    draft: Mapped[str] = mapped_column(Text, default='')
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    skipped_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class Debrief(Base):
    __tablename__ = 'debriefs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(160), unique=True)
    account: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(40), default='needs_review')
    stage: Mapped[str] = mapped_column(String(40), default='Discovery')
    summary: Mapped[str] = mapped_column(Text)
    next_steps: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    draft: Mapped[str] = mapped_column(Text, default='')
    reminder_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_type: Mapped[str] = mapped_column(String(40), default='pasted_notes')

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

class OperatorSettings(Base):
    __tablename__ = 'operator_settings'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timezone: Mapped[str] = mapped_column(String(80), default='Europe/Paris')
    warm_signal_threshold: Mapped[float] = mapped_column(Float, default=6.0)
    warm_signal_cron: Mapped[str] = mapped_column(String(80), default='0 7 * * 1-5')
    digest_deadline: Mapped[str] = mapped_column(String(20), default='08:30')
    linkedin_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    gmail_send_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    icp: Mapped[dict] = mapped_column(JSON, default=dict)
    offer: Mapped[dict] = mapped_column(JSON, default=dict)

class IntegrationHealth(Base):
    __tablename__ = 'integration_health'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), unique=True)
    status: Mapped[str] = mapped_column(String(30), default='not_configured')
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[list] = mapped_column(JSON, default=list)

class CallEvent(Base):
    __tablename__ = 'call_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(160), unique=True)
    account: Mapped[str] = mapped_column(String(160))
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    source_status: Mapped[str] = mapped_column(String(40), default='pending')
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class ProviderAction(Base):
    __tablename__ = 'provider_actions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    provider: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default='proposed')
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

def init_db():
    Base.metadata.create_all(engine)
