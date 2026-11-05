# LoanServe

LoanServe follows the supplied lending assignment from eligibility checks through a
policy-grounded assistant. The project has one server: FastAPI. The ML models load from
saved files, the policy search reads a local Chroma index, and the LLM calls Gemini.

## Install, test, and start

Use Python 3.11 or newer. Open a terminal inside this extracted directory. A virtual
environment is optional; you do not need to activate one:

```bash
python3 -m pip install --user -r requirements.txt
```

The ZIP includes a blank `.env`. Add `GEMINI_API_KEY` and `GEMINI_MODEL` there; keep the
file private. Both are needed for the live Gemini tests and assistant replies.

```bash
python3 -m pytest tests.py tests/ -q
bash run.sh check
bash run.sh check-live
bash run.sh
```

The server listens on `127.0.0.1:8000` by default. Its API applications persist in
`database/api_applications.db`, separate from the supplied batch analysis database.
`run.sh` uses a Python with installed dependencies; set `LOANSERVE_PYTHON` to select a
specific interpreter. `check` tests FastAPI, the saved ML models, and policy retrieval
without calling Gemini. `check-live` also asks Gemini a policy question and verifies
its citations.
Set `LOANSERVE_HOST` and
`LOANSERVE_PORT` before `bash run.sh` if you need another address or port. Stop it with
Ctrl+C.

| What to inspect | Where |
| --- | --- |
| Swagger interface and live endpoint schemas | <http://127.0.0.1:8000/docs> |
| OpenAPI JSON | <http://127.0.0.1:8000/openapi.json> |
| Health check | <http://127.0.0.1:8000/health> |

The Swagger page uses a relative OpenAPI URL, so it also works when the server is
published behind a path-based proxy such as `/proxy/8000`.

In Swagger, use `POST /api/v1/auth/signup`, then `POST /api/v1/auth/login`.
Copy the returned token into **Authorize**. The `loan_officer` role can ask the
assistant; the `administrator` role can resume a request held for approval.

To check RAG directly, send `{"question": "How soon is an application decided"}`
to `POST /api/v1/policy/search`. It returns the retrieved policy passages without
calling Gemini. Send the same body to `POST /api/v1/policy/answer` to see a Gemini
answer with verified chunk citations. Both routes require the bearer token.

## Where each feature lives

| Feature | Code and outputs | How to inspect it |
| --- | --- | --- |
| Lending rules and installment math | [`loanserve/core/`](loanserve/core/), [`config/constants.py`](config/constants.py) | `tests.py` week 1 tests; create an application in Swagger |
| Cleaning and SQLite reports | [`loanserve/data_access/`](loanserve/data_access/), [`processed_data/`](processed_data/), [`database/loanserve.db`](database/loanserve.db) | `tests.py` week 2 tests; read `loanserve/data_access/database_reports.py` |
| FastAPI routes, schemas, auth | [`loanserve/api/`](loanserve/api/) | Swagger `/docs`; `tests.py` week 3 tests |
| Credit risk ML | [`loanserve/risk_models/`](loanserve/risk_models/), [`artifacts/champion.pkl`](artifacts/champion.pkl), [`output/work_queue.csv`](output/work_queue.csv) | `tests.py` week 4 tests; inspect `output/champion_search.json` and `output/threshold_choice.json` |
| Message classification and LLM sentiment | [`loanserve/message_intelligence/`](loanserve/message_intelligence/), [`artifacts/message_classifier.pkl`](artifacts/message_classifier.pkl), [`output/escalation_report.csv`](output/escalation_report.csv) | `tests.py` weeks 5–6; inspect `output/message_pipeline.csv` and `output/injection_report.csv` |
| Policy retrieval (RAG) | [`loanserve/retrieval/`](loanserve/retrieval/), [`database/policy_store/`](database/policy_store/), [`data/policy_documents/`](data/policy_documents/) | `bash run.sh check-live`; `/api/v1/policy/search` and `/api/v1/policy/answer` in Swagger |
| LangGraph assistant | [`loanserve/assistant/`](loanserve/assistant/), [`loanserve/api/routers/assistant.py`](loanserve/api/routers/assistant.py) | `POST /api/v1/assistant/ask` in Swagger; inspect returned `steps` and `narration` |

The seven assistant steps are `triage → plan → tools → draft → approval → critic → respond`.
The planner can call only the four adapters in [`loanserve/assistant/tools.py`](loanserve/assistant/tools.py).
An approval request pauses at the `approval` node and resumes with the same `thread_id`
after an administrator sends `approved: true` or `false`.

## Rebuild generated assets

```bash
python3 -m loanserve.message_intelligence.message_classifier
python3 -m loanserve.retrieval.vector_store
python3 -m loanserve.message_intelligence.escalation
```

The escalation command uses Gemini for sentiment only when it can change a review decision.
The assignment is in [`loanserve_question/`](loanserve_question/); supplied datasets are
in [`data/`](data/). Test cases are in [`tests.py`](tests.py) and [`tests/`](tests/).
