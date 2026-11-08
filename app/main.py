from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request as URLRequest, urlopen
from urllib.parse import parse_qs
import json, secrets, time
from fastapi import FastAPI, Depends, HTTPException, Request, Header, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from fastapi.responses import StreamingResponse
import csv
from io import StringIO
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import select
from .db import init_db, SessionLocal, WorkflowRun, Lead, Debrief, AuditEvent, OperatorSettings, IntegrationHealth, CallEvent, ProviderAction, User, AuthSession, GoogleCredential, OAuthState
from .schemas import WarmSignalRequest, DebriefRequest, ApprovalRequest, SettingsRequest, CallEventRequest, StageRequest, IntegrationConnectRequest
from .core import settings
from .integrations import ApprovalOnlyGoogle
from .jobs import schedule_transcript_retries
from .workflows.warm_signal import score_candidate, draft_message, validate_draft, normalize_identity
from .workflows.deal_debrief import extract_debrief, retry_offsets_minutes
from .policies import is_suppressed, skipped_until, can_move_stage
from .security import ensure_bootstrap_admin, password_matches, create_session, authenticated_user, require_csrf, encrypt_secret, production_guard, require_role

app = FastAPI(title='Pond Automation System', version='0.1.0')
ROOT = Path(__file__).resolve().parent.parent
app.mount('/static', StaticFiles(directory=str(ROOT / 'frontend')), name='static')
_login_attempts: dict[str, list[float]] = {}

if settings.allowed_origins:
    app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.allowed_origins.split(',') if x.strip()], allow_credentials=True, allow_methods=['GET','POST','PUT','PATCH','DELETE'], allow_headers=['Content-Type','X-CSRF-Token'])
if settings.trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[x.strip() for x in settings.trusted_hosts.split(',') if x.strip()])

@app.middleware('http')
async def security_middleware(request: Request, call_next):
    if settings.app_env.lower() == 'production':
        try:
            if int(request.headers.get('content-length', '0')) > 1_000_000:
                raise HTTPException(413, 'Request body too large')
        except ValueError:
            raise HTTPException(400, 'Invalid content length')
    public = request.url.path in {'/api/health','/api/auth/login','/api/auth/logout','/api/auth/me','/api/integrations/google/callback'} or request.url.path.startswith('/static') or request.url.path == '/'
    if request.url.path.startswith('/api') and not public and settings.app_env.lower() == 'production':
        with SessionLocal() as s:
            authenticated_user(request, s, request.cookies.get('pond_session'))
            require_csrf(request, request.headers.get('X-CSRF-Token'), request.cookies.get('pond_session'), s)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    if settings.app_env.lower() == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

@app.on_event('startup')
def startup():
    production_guard()
    init_db()
    with SessionLocal() as s:
        ensure_bootstrap_admin(s)

def db():
    s = SessionLocal()
    try: yield s
    finally: s.close()

def audit(s, action, entity_type, entity_id, detail=None):
    s.add(AuditEvent(action=action, entity_type=entity_type, entity_id=str(entity_id), detail=detail or {}))

def user_from_request(request: Request, s: Session) -> User:
    return authenticated_user(request, s, request.cookies.get('pond_session'))

@app.post('/api/auth/login')
def login(payload: dict, response: Response, s: Session = Depends(db)):
    email = str(payload.get('email','')).strip().lower()
    password = str(payload.get('password',''))
    now=time.monotonic(); attempts=[x for x in _login_attempts.get(email,[]) if now-x < 900]
    if len(attempts) >= 10: raise HTTPException(429, 'Too many login attempts; try again later')
    user = s.query(User).filter_by(email=email, active=True).one_or_none()
    if not user or not password_matches(password, user.password_hash):
        attempts.append(now); _login_attempts[email]=attempts
        raise HTTPException(401, 'Invalid email or password')
    _login_attempts.pop(email, None)
    token, csrf = create_session(s, user)
    response.set_cookie('pond_session', token, httponly=True, secure=settings.cookie_secure, samesite='lax', max_age=settings.session_ttl_hours*3600)
    response.set_cookie('pond_csrf', csrf, httponly=False, secure=settings.cookie_secure, samesite='lax', max_age=settings.session_ttl_hours*3600)
    return {'email':user.email, 'role':user.role, 'csrf_token':csrf}

@app.post('/api/auth/logout')
def logout(response: Response, request: Request, s: Session = Depends(db)):
    token = request.cookies.get('pond_session')
    if token and settings.session_secret:
        import hashlib, hmac
        digest = hmac.new(settings.session_secret.encode(), token.encode(), hashlib.sha256).hexdigest()
        s.query(AuthSession).filter_by(token_hash=digest).delete(); s.commit()
    response.delete_cookie('pond_session'); response.delete_cookie('pond_csrf')
    return {'status':'logged_out'}

@app.get('/api/auth/me')
def me(request: Request, s: Session = Depends(db)):
    user = user_from_request(request, s)
    return {'email':user.email, 'role':user.role}

@app.get('/', response_class=HTMLResponse)
def home():
    return (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')

@app.get('/api/health')
def health(): return {'status':'ok','provider_writes':'approval_required','gmail_send_enabled':False,'database':settings.database_url.split(':',1)[0]}

@app.get('/api/settings')
def get_settings(s: Session = Depends(db)):
    item = s.query(OperatorSettings).first()
    if not item:
        item = OperatorSettings(icp={'titles':['founder','head of growth'], 'company_stage':'early-stage'}, offer={'name':'Pond','proof_points':[]}); s.add(item); s.commit()
    return {'id': item.id, 'timezone': item.timezone, 'warm_signal_threshold': item.warm_signal_threshold,
            'warm_signal_cron': item.warm_signal_cron, 'digest_deadline': item.digest_deadline,
            'linkedin_enabled': item.linkedin_enabled, 'gmail_send_enabled': item.gmail_send_enabled,
            'icp': item.icp, 'offer': item.offer}

@app.put('/api/settings')
def put_settings(req: SettingsRequest, request: Request, s: Session = Depends(db)):
    # Owner-only configuration; reviewers can still operate the queues.
    if settings.app_env.lower() == 'production': require_role(user_from_request(request, s), 'owner')
    from zoneinfo import ZoneInfo
    try: ZoneInfo(req.timezone)
    except Exception: raise HTTPException(422, 'timezone must be a valid IANA timezone')
    item = s.query(OperatorSettings).first() or OperatorSettings()
    for key, value in req.model_dump().items(): setattr(item, key, value)
    s.add(item); audit(s,'settings_updated','settings',item.id or 'new',{'fields':list(req.model_dump())}); s.commit()
    return {'status':'saved'}

@app.get('/api/integrations')
def integrations(s: Session = Depends(db)):
    configured = {'openai': bool(settings.openai_api_key), 'x': bool(settings.x_provider), 'linkedin': settings.linkedin_read_enabled, 'google': bool(s.query(IntegrationHealth).filter_by(provider='google', status='connected').one_or_none()), 'redis': settings.celery_enabled}
    catalog = {
        'google': {'label':'Google workspace','description':'Calendar, Drive transcripts, Gmail drafts, and Sheets projection.','scopes':['Calendar events','Drive transcript reads','Gmail draft creation','Sheets read/write'],'setup':'Create an OAuth web client, add the configured callback URL, then set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.'},
        'openai': {'label':'OpenAI','description':'Bounded scoring, drafting, extraction, and next-step review.','scopes':['Server-side model execution','Agent traces'],'setup':'Set OPENAI_API_KEY and an allowlisted OPENAI_MODEL on the server.'},
        'x': {'label':'X read-only','description':'Public buying-intent search only.','scopes':['Public search reads','No posting or engagement'],'setup':'Choose an approved X provider and set X_PROVIDER plus its secret reference.'},
        'linkedin': {'label':'LinkedIn read-only','description':'Optional research path, disabled until policy and account review.','scopes':['Read-only research'],'setup':'Complete permission and Terms of Service review, then enable LINKEDIN_READ_ENABLED.'},
        'redis': {'label':'Redis / workers','description':'Queue, locks, retries, and scheduled jobs.','scopes':['Job broker','Short-lived locks'],'setup':'Set REDIS_URL and CELERY_ENABLED=true, then start worker and beat containers.'},
    }
    return [{**catalog[k], 'provider':k, 'status':'connected' if v else 'needs_setup', 'writes':'approval_required' if k=='google' else 'read_only'} for k,v in configured.items()]

@app.post('/api/integrations/{provider}/connect')
def connect_integration(provider: str, req: IntegrationConnectRequest, request: Request, s: Session = Depends(db)):
    if settings.app_env.lower() == 'production': require_role(user_from_request(request, s), 'owner')
    allowed = {'google','openai','x','linkedin','redis'}
    if provider not in allowed: raise HTTPException(404, 'Unknown integration')
    item = s.query(IntegrationHealth).filter_by(provider=provider).one_or_none()
    if not item:
        item = IntegrationHealth(provider=provider, status='needs_setup'); s.add(item)
    item.last_error = 'Connection handoff requires deployment credentials or OAuth configuration.'
    audit(s,'integration_setup_started','integration',provider,{'account_label':req.account_label})
    s.commit()
    return {'provider':provider,'status':'needs_setup','next_step':'Configure the provider credentials, then reconnect.','oauth_available': provider=='google' and bool(getattr(settings,'google_client_id',None))}

@app.get('/api/integrations/google/start')
def google_start(request: Request, s: Session = Depends(db)):
    if not settings.google_client_id:
        raise HTTPException(409, 'GOOGLE_CLIENT_ID is not configured on the server')
    scopes = ' '.join(['openid','email','https://www.googleapis.com/auth/calendar','https://www.googleapis.com/auth/drive.readonly','https://www.googleapis.com/auth/gmail.compose','https://www.googleapis.com/auth/spreadsheets'])
    user = user_from_request(request, s)
    state = secrets.token_urlsafe(32)
    s.add(OAuthState(value=state, user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(minutes=10))); s.commit()
    query = urlencode({'client_id':settings.google_client_id,'redirect_uri':settings.google_redirect_uri,'response_type':'code','access_type':'offline','prompt':'consent','state':state,'scope':scopes})
    return {'authorization_url':f'https://accounts.google.com/o/oauth2/v2/auth?{query}'}

@app.get('/api/integrations/google/callback')
def google_callback(code: str | None = None, error: str | None = None, state: str | None = None, s: Session = Depends(db)):
    if error: raise HTTPException(400, f'Google authorization failed: {error}')
    if not code or not state: raise HTTPException(400, 'Missing authorization code or state')
    oauth = s.query(OAuthState).filter_by(value=state).one_or_none()
    oauth_expiry = oauth.expires_at.replace(tzinfo=timezone.utc) if oauth else None
    if not oauth or oauth_expiry < datetime.now(timezone.utc): raise HTTPException(400, 'Invalid or expired OAuth state')
    body = urlencode({'code':code,'client_id':settings.google_client_id,'client_secret':settings.google_client_secret,'redirect_uri':settings.google_redirect_uri,'grant_type':'authorization_code'}).encode()
    try:
        with urlopen(URLRequest('https://oauth2.googleapis.com/token', data=body, headers={'Content-Type':'application/x-www-form-urlencoded'}), timeout=15) as result:
            tokens=json.loads(result.read())
    except Exception as exc:
        raise HTTPException(502, f'Google token exchange failed: {exc}')
    if 'access_token' not in tokens: raise HTTPException(502, 'Google did not return an access token')
    userinfo={}
    try:
        with urlopen(URLRequest('https://openidconnect.googleapis.com/v1/userinfo', headers={'Authorization':f"Bearer {tokens['access_token']}"}), timeout=15) as result:
            userinfo=json.loads(result.read())
    except Exception:
        pass
    existing=s.query(GoogleCredential).filter_by(user_id=oauth.user_id).one_or_none()
    if not existing: existing=GoogleCredential(user_id=oauth.user_id, refresh_token='')
    existing.email=userinfo.get('email',''); existing.access_token=encrypt_secret(tokens['access_token']); existing.refresh_token=encrypt_secret(tokens.get('refresh_token','')) if tokens.get('refresh_token') else existing.refresh_token; existing.expires_at=datetime.now(timezone.utc)+timedelta(seconds=int(tokens.get('expires_in',3600))); existing.scopes=scopes.split(); existing.updated_at=datetime.now(timezone.utc); s.add(existing)
    s.delete(oauth)
    item=s.query(IntegrationHealth).filter_by(provider='google').one_or_none() or IntegrationHealth(provider='google'); item.status='connected'; item.last_error=None; item.scopes=scopes.split(); item.last_success_at=datetime.now(timezone.utc); s.add(item); s.commit()
    return HTMLResponse('<h1>Google connected</h1><p>You can close this window and return to Pond.</p>')

@app.get('/api/runs')
def runs(s: Session = Depends(db)):
    return [{'id':x.id,'workflow':x.workflow,'status':x.status,'counts':x.counts,'created_at':x.created_at.isoformat()} for x in s.query(WorkflowRun).order_by(WorkflowRun.id.desc()).limit(30)]

@app.get('/api/dashboard')
def dashboard(search: str | None = None, status: str | None = None, s: Session = Depends(db)):
    leads = s.scalars(select(Lead).order_by(Lead.total_score.desc())).all()
    if search:
        needle=search.lower(); leads=[x for x in leads if needle in f'{x.first_name} {x.company} {x.title} {x.excerpt}'.lower()]
    if status: leads=[x for x in leads if x.status == status]
    debriefs = s.scalars(select(Debrief).order_by(Debrief.id.desc())).all()
    return {'leads':[{'id':x.id,'name':x.first_name,'company':x.company,'title':x.title,'score':x.total_score,'fit':x.fit_score,'intent':x.intent_score,'status':x.status,'draft':x.draft,'url':x.post_url,'evidence':x.evidence,'skipped_until':x.skipped_until.isoformat() if x.skipped_until else None} for x in leads], 'debriefs':[{'id':x.id,'account':x.account,'stage':x.stage,'status':x.status,'summary':x.summary,'next_steps':x.next_steps,'draft':x.draft,'reminder_date':x.reminder_date,'source_type':x.source_type} for x in debriefs], 'runs':s.query(WorkflowRun).count(), 'audit':s.query(AuditEvent).count()}

@app.get('/api/export/leads.csv')
def export_leads(s: Session = Depends(db)):
    out=StringIO(); writer=csv.writer(out); writer.writerow(['id','first_name','company','title','source','score','status','post_url','draft'])
    for x in s.query(Lead).order_by(Lead.total_score.desc()): writer.writerow([x.id,x.first_name,x.company,x.title,x.source,x.total_score,x.status,x.post_url,x.draft])
    return StreamingResponse(iter([out.getvalue()]), media_type='text/csv', headers={'Content-Disposition':'attachment; filename=pond-leads.csv'})

@app.post('/api/warm-signal/run')
def warm_signal(req: WarmSignalRequest, s: Session = Depends(db)):
    run = WorkflowRun(workflow='warm_signal', status='running', counts={}); s.add(run); s.flush(); shortlisted=0; drafted=0
    seen = set()
    for c in req.candidates:
        key = normalize_identity(c.source, c.external_id, c.author_first_name, c.company)
        existing = s.scalar(select(Lead).where(Lead.external_id==key))
        if key in seen or existing:
            continue
        seen.add(key); result = score_candidate(c.title, c.post_excerpt)
        if result.total < req.threshold: continue
        shortlisted += 1; msg = draft_message(c.author_first_name, c.post_excerpt)
        errors = validate_draft(msg, c.author_first_name)
        lead = Lead(external_id=key, first_name=c.author_first_name, company=c.company, title=c.title, source=c.source, post_url=str(c.post_url), excerpt=c.post_excerpt, fit_score=result.fit, intent_score=result.intent, total_score=result.total, status='needs_review' if errors else 'drafted', draft=msg, evidence={'rationale':result.rationale,'validation_errors':errors,'source_url':str(c.post_url),'quote':c.post_excerpt})
        s.add(lead); s.flush(); audit(s,'lead_created','lead',lead.id,{'run_id':run.id}); drafted += 1
    run.status='completed_with_warnings' if drafted < shortlisted else 'completed'; run.counts={'shortlisted':shortlisted,'drafted':drafted}; s.commit()
    return {'run_id':run.id,'status':run.status,'counts':run.counts}

@app.post('/api/debriefs')
def create_debrief(req: DebriefRequest, s: Session = Depends(db)):
    existing = s.scalar(select(Debrief).where(Debrief.event_id==req.event_id))
    if existing: return {'id':existing.id,'idempotent':True}
    data=extract_debrief(req.notes); d=Debrief(event_id=req.event_id, account=req.account, status='needs_review', stage=data['stage'], summary=data['summary'], next_steps=data['next_steps'], evidence=data['evidence'], draft=data['draft']); s.add(d); s.flush(); audit(s,'debrief_created','debrief',d.id,{'event_id':req.event_id}); s.commit(); return {'id':d.id,'status':d.status,'stage':d.stage}

@app.patch('/api/leads/{lead_id}/approval')
def approve_lead(lead_id:int, req:ApprovalRequest, s:Session=Depends(db)):
    lead=s.get(Lead,lead_id)
    if not lead: raise HTTPException(404,'Lead not found')
    lead.status=req.status
    lead.skipped_until = skipped_until() if req.status == 'skipped' else None
    audit(s,'lead_status_changed','lead',lead.id,{'status':req.status,'skipped_until':lead.skipped_until.isoformat() if lead.skipped_until else None}); s.commit(); return {'id':lead.id,'status':lead.status,'skipped_until':lead.skipped_until}

@app.patch('/api/debriefs/{debrief_id}/approval')
def approve_debrief(debrief_id: int, req: ApprovalRequest, s: Session = Depends(db)):
    debrief = s.get(Debrief, debrief_id)
    if not debrief: raise HTTPException(404, 'Debrief not found')
    debrief.status = req.status; audit(s,'debrief_status_changed','debrief',debrief.id,{'status':req.status}); s.commit()
    return {'id':debrief.id,'status':debrief.status}

@app.patch('/api/debriefs/{debrief_id}/stage')
def update_stage(debrief_id: int, req: StageRequest, s: Session = Depends(db)):
    debrief = s.get(Debrief, debrief_id)
    if not debrief: raise HTTPException(404, 'Debrief not found')
    if not can_move_stage(debrief.stage, req.stage, req.evidence):
        raise HTTPException(422, 'Stage transition requires supporting evidence and cannot move backward without explicit evidence')
    before = debrief.stage; debrief.stage = req.stage
    audit(s,'deal_stage_changed','debrief',debrief.id,{'before':before,'after':req.stage,'evidence':req.evidence}); s.commit()
    return {'id':debrief.id,'stage':debrief.stage}

@app.post('/api/debriefs/{debrief_id}/actions')
def propose_debrief_actions(debrief_id: int, request: Request, s: Session = Depends(db)):
    debrief = s.get(Debrief, debrief_id)
    if not debrief: raise HTTPException(404, 'Debrief not found')
    google = ApprovalOnlyGoogle(s, user_from_request(request, s)); actions=[]
    for kind, result in [('calendar_reminder', google.create_private_reminder(idempotency_key=f'debrief:{debrief.id}:reminder', title=f'Follow up {debrief.account}', start_at=debrief.reminder_date or 'unscheduled')), ('gmail_draft', google.create_gmail_draft(idempotency_key=f'debrief:{debrief.id}:draft', to=None, subject=f'Next steps — {debrief.account}', body=debrief.draft))]:
        existing=s.query(ProviderAction).filter_by(idempotency_key=f'debrief:{debrief.id}:{"reminder" if kind=="calendar_reminder" else "draft"}').one_or_none()
        if not existing:
            existing=ProviderAction(idempotency_key=f'debrief:{debrief.id}:{"reminder" if kind=="calendar_reminder" else "draft"}', provider='google', action=kind, payload={'detail':result.detail}, status=result.status); s.add(existing)
        actions.append({'action':kind,'status':existing.status,'detail':result.detail})
    audit(s,'debrief_actions_proposed','debrief',debrief.id,{'actions':actions}); s.commit(); return {'actions':actions,'note':'No email was sent.'}

@app.post('/api/call-events')
def register_call_event(req: CallEventRequest, s: Session = Depends(db)):
    existing=s.query(CallEvent).filter_by(event_id=req.event_id).one_or_none()
    if existing: return {'id':existing.id,'idempotent':True}
    ends=datetime.fromisoformat(req.ends_at.replace('Z','+00:00'))
    item=CallEvent(event_id=req.event_id,account=req.account,ends_at=ends,source_status='pending'); s.add(item); s.commit(); schedule_transcript_retries(req.event_id, ends); audit(s,'call_event_registered','call_event',item.id,{'retry_offsets':[10,20,40]}); s.commit()
    return {'id':item.id,'status':item.source_status,'retry_offsets_minutes':list(retry_offsets_minutes())}

