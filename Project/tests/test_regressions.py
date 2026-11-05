import pytest
from fastapi.testclient import TestClient
from loanserve.api.application_factory import create_application
from loanserve.assistant.nodes import critic
from loanserve.assistant.tools import ToolError, calculate_installment
from loanserve.core.exceptions import InvalidApplicationError
from loanserve.core.loan_calculations import calculate_monthly_installment


@pytest.mark.parametrize('terms', [(100, 10, 0), (100, 10, 2.5), (float('inf'), 10, 12), (100, -1, 12)])
def test_invalid_terms_have_domain_errors(terms):
    with pytest.raises(InvalidApplicationError):
        calculate_monthly_installment(*terms)


def test_tiny_interest_remains_accurate():
    assert calculate_monthly_installment(120000, 1e-12, 12) == pytest.approx(10000)


@pytest.mark.parametrize('result', [{'tool_error': 'unavailable'}, {'passages': []}])
def test_unavailable_evidence_is_refused(result):
    assert critic({'draft': 'Your request has been recorded.', 'tool_results': [result]})['refused']


def test_whitespace_questions_are_rejected(monkeypatch):
    monkeypatch.setenv('LOANSERVE_OPEN_MODE', '1')
    with TestClient(create_application()) as client:
        assert client.post('/api/v1/assistant/ask', json={'question': '       '}).status_code == 422


def test_swagger_uses_relative_openapi_url():
    with TestClient(create_application()) as client:
        docs = client.get('/docs')

    assert docs.status_code == 200
    assert "url: 'openapi.json'" in docs.text


@pytest.mark.parametrize('terms', [dict(principal_inr=100, annual_interest_rate_percent=1, tenure_months=1.5),
                                   dict(principal_inr=float('nan'), annual_interest_rate_percent=1, tenure_months=12)])
def test_tool_rejects_nonfinite_or_fractional_terms(terms):
    with pytest.raises(ToolError):
        calculate_installment(terms)
