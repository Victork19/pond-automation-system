from pydantic import BaseModel, Field, HttpUrl

class CandidateIn(BaseModel):
    external_id: str
    source: str = 'manual'
    post_url: HttpUrl | str
    posted_at: str | None = None
    author_first_name: str
    title: str = ''
    company: str = ''
    post_excerpt: str = Field(min_length=20)

class WarmSignalRequest(BaseModel):
    candidates: list[CandidateIn] = []
    threshold: float = Field(default=6.0, ge=0, le=10)

class DebriefRequest(BaseModel):
    event_id: str
    account: str
    notes: str = Field(min_length=20)
    call_ended_at: str | None = None

class ApprovalRequest(BaseModel):
    status: str = Field(pattern='^(approved|edited|skipped|do_not_contact)$')

class SettingsRequest(BaseModel):
    timezone: str = 'Europe/Paris'
    warm_signal_threshold: float = Field(default=6.0, ge=0, le=10)
    warm_signal_cron: str = '0 7 * * 1-5'
    digest_deadline: str = '08:30'
    linkedin_enabled: bool = False
    gmail_send_enabled: bool = False
    icp: dict = {}
    offer: dict = {}

class CallEventRequest(BaseModel):
    event_id: str
    account: str
    ends_at: str

class StageRequest(BaseModel):
    stage: str
    evidence: list[dict] = []

class IntegrationConnectRequest(BaseModel):
    account_label: str = ''
