"""Provider boundaries. Customer-facing writes require an authenticated operator."""
from dataclasses import dataclass
from datetime import datetime, timezone
from base64 import urlsafe_b64encode
from email.message import EmailMessage
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import json
from sqlalchemy.orm import Session
from .core import settings
from .db import GoogleCredential, User
from .security import decrypt_secret, encrypt_secret

@dataclass
class ProviderResult:
    status: str
    external_id: str | None = None
    detail: str | None = None

class ReadOnlySource:
    name = 'manual'
    def search(self, query: str, lookback_hours: int) -> list[dict]:
        return []

class XSource(ReadOnlySource):
    name = 'x'
    def search(self, query: str, lookback_hours: int) -> list[dict]:
        if not settings.x_provider:
            raise RuntimeError('X provider is not configured')
        raise NotImplementedError('Configure an approved X adapter before enabling live search')

class ApprovalOnlyGoogle:
    """Executes only explicit operator actions; Gmail send is never exposed."""
    def __init__(self, s: Session | None = None, user: User | None = None):
        self.s, self.user = s, user

    def _request(self, method: str, url: str, payload: dict | None = None) -> tuple[dict, str | None]:
        if not self.s or not self.user or not self.user.id:
            return {}, 'Google account authorization required'
        credential = self.s.query(GoogleCredential).filter_by(user_id=self.user.id).one_or_none()
        if not credential:
            return {}, 'Connect Google before preparing provider actions'
        token = decrypt_secret(credential.access_token)
        if credential.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            refresh = decrypt_secret(credential.refresh_token) if credential.refresh_token else ''
            if not refresh:
                return {}, 'Google authorization expired; reconnect the account'
            body = urlencode({'client_id':settings.google_client_id,'client_secret':settings.google_client_secret,'refresh_token':refresh,'grant_type':'refresh_token'}).encode()
            try:
                with urlopen(Request('https://oauth2.googleapis.com/token', data=body, headers={'Content-Type':'application/x-www-form-urlencoded'}), timeout=15) as response:
                    tokens=json.loads(response.read())
                token=tokens['access_token']; credential.access_token=encrypt_secret(token); credential.expires_at=datetime.now(timezone.utc).replace(microsecond=0)+__import__('datetime').timedelta(seconds=int(tokens.get('expires_in',3600))); self.s.commit()
            except Exception as exc:
                return {}, f'Google token refresh failed: {exc}'
        headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'}
        try:
            with urlopen(Request(url, method=method, data=json.dumps(payload).encode() if payload is not None else None, headers=headers), timeout=20) as response:
                return json.loads(response.read()), None
        except Exception as exc:
            return {}, f'Google API request failed: {exc}'

    def create_private_reminder(self, *, idempotency_key: str, title: str, start_at: str) -> ProviderResult:
        try:
            start=datetime.fromisoformat(start_at.replace('Z','+00:00'))
            end=start + __import__('datetime').timedelta(minutes=30)
        except Exception:
            return ProviderResult('failed', detail='Reminder requires an ISO-8601 start time')
        payload={'summary':title,'start':{'dateTime':start.isoformat()},'end':{'dateTime':end.isoformat()},'visibility':'private','description':'Created by Pond after operator review.'}
        data,error=self._request('POST','https://www.googleapis.com/calendar/v3/calendars/primary/events',payload)
        return ProviderResult('failed' if error else 'completed', data.get('id') if data else None, error or 'Calendar reminder created')

    def create_gmail_draft(self, *, idempotency_key: str, to: str | None, subject: str, body: str) -> ProviderResult:
        message=EmailMessage();
        if to: message['To']=to
        message['Subject']=subject; message.set_content(body)
        raw=urlsafe_b64encode(message.as_bytes()).decode().rstrip('=')
        data,error=self._request('POST','https://gmail.googleapis.com/gmail/v1/users/me/drafts',{'message':{'raw':raw}})
        return ProviderResult('failed' if error else 'completed', data.get('id') if data else None, error or 'Gmail draft created; no email was sent')

    def sync_sheet_row(self, *, idempotency_key: str, tab: str, row: dict) -> ProviderResult:
        return ProviderResult('failed', detail='Sheets projection requires an approved sheet mapping')
