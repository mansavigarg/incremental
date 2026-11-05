"""Public request and response contracts for the web service."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from config.constants import SECURED_LOAN_TYPES
from loanserve.core.validators import validate_email_address, validate_mobile_number, validate_pan_number


class LoanApplicationRequest(BaseModel):
    applicant_name: str = Field(min_length=2, max_length=80)
    loan_type: Literal["home", "vehicle", "gold", "personal"]
    loan_amount_inr: float = Field(gt=0)
    tenure_months: int = Field(gt=0, le=360)
    monthly_income_inr: float = Field(gt=0)
    age_years: int = Field(ge=18, le=100)
    credit_score: int = Field(ge=300, le=900)
    collateral_value_inr: float = Field(default=0.0, ge=0)
    pan_number: str
    mobile_number: str
    email_address: str

    @field_validator("pan_number")
    @classmethod
    def settle_pan_number(cls, given_pan_number):
        return validate_pan_number(given_pan_number)

    @field_validator("mobile_number")
    @classmethod
    def settle_mobile_number(cls, given_mobile_number):
        return validate_mobile_number(given_mobile_number)

    @field_validator("email_address")
    @classmethod
    def settle_email_address(cls, given_email_address):
        return validate_email_address(given_email_address)

    @model_validator(mode="after")
    def require_collateral_for_secured_loans(self):
        if self.loan_type in SECURED_LOAN_TYPES and self.collateral_value_inr <= 0:
            raise ValueError(f"{self.loan_type} loan needs a collateral value")
        return self


class LoanApplicationResponse(BaseModel):
    application_id: str
    applicant_name: str
    loan_type: str
    loan_amount_inr: float
    tenure_months: int
    interest_rate_percent: float
    monthly_installment_inr: float
    is_eligible: bool
    rejection_reasons: list[str]


class RepaymentSchedule(BaseModel):
    application_id: str
    outstanding_after_each_month: list[float]


class ApplicationFilters(BaseModel):
    loan_type: Literal["home", "vehicle", "gold", "personal"] | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ApplicationPage(BaseModel):
    total: int
    limit: int
    offset: int
    applications: list[LoanApplicationResponse]


class AccountRequest(BaseModel):
    user_name: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["loan_officer", "administrator"] = "loan_officer"


class AccountResponse(BaseModel):
    user_name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AssistantQuestion(BaseModel):
    question: str = Field(min_length=3)
    thread_id: str | None = None
    approved: bool | None = None
    thread_owner: str | None = None

    @field_validator('question')
    @classmethod
    def require_words(cls, value):
        if len(value.strip()) < 3:
            raise ValueError('Question must contain at least three characters')
        return value.strip()


class AssistantResponse(BaseModel):
    thread_id: str
    answer: str
    category: str
    confidence: float
    refused: str
    steps: list[str]
    narration: list[str]
    needs_approval: bool
