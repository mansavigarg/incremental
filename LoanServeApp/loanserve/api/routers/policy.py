"""Direct policy retrieval and citation-checked RAG endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from loanserve.retrieval.filtered_search import filtered_search, product_in_question
from loanserve.retrieval.grounded_answer import UngroundedAnswer, answer_from_passages
from loanserve.retrieval.vector_store import load_embedder, open_policy_store
from loanserve.core.exceptions import LanguageModelError
from config.constants import POLICY_STORE_PATH


router = APIRouter(prefix='/policy', tags=['policy and RAG'])


class PolicyQuestion(BaseModel):
    question: str = Field(min_length=3)
    how_many: int = Field(default=4, ge=1, le=10)

    @field_validator('question')
    @classmethod
    def require_words(cls, value):
        if len(value.strip()) < 3:
            raise ValueError('Question must contain at least three characters')
        return value.strip()


class PolicyPassage(BaseModel):
    chunk_id: str
    text: str
    heading: str
    document_id: str
    distance: float


class PolicySearchResponse(BaseModel):
    question: str
    product_type: str
    passages: list[PolicyPassage]


class PolicyAnswerResponse(PolicySearchResponse):
    answer: str
    citations: str
    retrieved: str


def retrieve(submitted: PolicyQuestion):
    try:
        collection = open_policy_store(POLICY_STORE_PATH)
        passages = filtered_search(collection, submitted.question, load_embedder(), submitted.how_many)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f'Policy search unavailable: {error}') from error
    if not passages:
        raise HTTPException(status_code=404, detail='No policy passage found')
    return passages


@router.post('/search', response_model=PolicySearchResponse)
def search(submitted: PolicyQuestion):
    passages = retrieve(submitted)
    return {'question': submitted.question, 'product_type': product_in_question(submitted.question),
            'passages': passages}


@router.post('/answer', response_model=PolicyAnswerResponse)
def answer(submitted: PolicyQuestion):
    passages = retrieve(submitted)
    try:
        grounded = answer_from_passages(submitted.question, passages)
    except UngroundedAnswer as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except LanguageModelError as error:
        raise HTTPException(status_code=503, detail=f'Language model unavailable: {error}') from error
    return {**grounded, 'product_type': product_in_question(submitted.question),
            'passages': passages}
