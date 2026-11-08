import re
from dataclasses import dataclass

INTENT_TERMS = ('looking for', 'need', 'struggling', 'trying to', 'recommend', 'tool', 'outbound', 'pipeline')
FIT_TERMS = ('founder', 'growth', 'sales', 'marketing', 'revenue', 'gtm', 'head of')

@dataclass
class ScoredCandidate:
    fit: float
    intent: float
    total: float
    rationale: list[str]

def score_candidate(title: str, excerpt: str) -> ScoredCandidate:
    text = f'{title} {excerpt}'.lower()
    fit_hits = [t for t in FIT_TERMS if t in text]
    intent_hits = [t for t in INTENT_TERMS if t in text]
    fit = min(5.0, 2.0 + len(fit_hits) * 0.75)
    intent = min(5.0, 1.5 + len(intent_hits) * 0.7)
    rationale = [f'Fit signals: {", ".join(fit_hits) or "none"}', f'Intent signals: {", ".join(intent_hits) or "none"}']
    return ScoredCandidate(fit, intent, round(fit + intent, 1), rationale)

def draft_message(first_name: str, excerpt: str, product: str = 'Pond') -> str:
    problem = re.sub(r'\s+', ' ', excerpt).strip().rstrip('.!?')
    return f"Hi {first_name} — saw you mention {problem}. That kind of friction can quietly slow a team’s pipeline. We built {product} to help teams turn warm buying signals into focused next steps, without adding another noisy outbound sequence. Worth comparing notes?"

def validate_draft(message: str, first_name: str, min_chars=300, max_chars=400) -> list[str]:
    errors = []
    if not 300 <= len(message) <= 400: errors.append(f'character_count={len(message)}; expected 300-400')
    if not message.startswith(f'Hi {first_name}'): errors.append('must use first name only')
    if '?' not in message[-3:]: errors.append('must end with a low-pressure question')
    return errors

def normalize_identity(source: str, external_id: str, author_first_name: str, company: str = '') -> str:
    """Stable identity key used across repeated source runs."""
    return f'{source}:{external_id}'.lower().strip()

def within_lookback(posted_at, now, monday: bool = False) -> bool:
    from datetime import timedelta
    return posted_at >= now - timedelta(hours=72 if monday else 36)
