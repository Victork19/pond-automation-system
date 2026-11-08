from app.workflows.warm_signal import score_candidate, validate_draft
from app.workflows.deal_debrief import extract_debrief

def test_score_uses_fit_and_intent():
    result = score_candidate('Head of Growth', 'We need a tool for outbound pipeline.')
    assert result.total >= 6
    assert result.fit > 0 and result.intent > 0

def test_debrief_captures_next_step_and_evidence():
    result = extract_debrief('Acme is evaluating a pilot.\nI will send the one-pager by Thursday.')
    assert result['next_steps']
    assert result['evidence'][0]['source'] == 'pasted_notes'
