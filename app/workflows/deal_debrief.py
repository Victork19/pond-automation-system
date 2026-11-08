import re

def extract_debrief(notes: str):
    lines = [x.strip() for x in notes.splitlines() if x.strip()]
    evidence = [{'source': 'pasted_notes', 'quote': line} for line in lines[:8]]
    next_steps = []
    for line in lines:
        if re.search(r'\b(i’ll|i will|we’ll|we will|send|share|follow up|schedule|review)\b', line, re.I):
            next_steps.append({'action': line, 'owner_type': 'unknown', 'due_date_text': 'not discussed', 'confidence': 'medium', 'evidence': [{'quote': line}]})
    stage = 'Discovery'
    text = notes.lower()
    if 'proposal' in text or 'pricing' in text: stage = 'Proposal'
    elif 'demo' in text or 'evaluation' in text: stage = 'Evaluation'
    summary = lines[0] if lines else 'No summary available.'
    draft = f"Hi there,\n\nThanks for the conversation. My notes show: {summary}\n\nNext steps:\n" + '\n'.join(f"- {x['action']}" for x in next_steps[:5]) + "\n\nI’ll keep the thread moving from here."
    return {'summary': summary, 'stage': stage, 'next_steps': next_steps, 'evidence': evidence, 'draft': draft}

def retry_offsets_minutes() -> tuple[int, int, int]:
    return (10, 20, 40)
