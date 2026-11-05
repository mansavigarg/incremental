"""Validated adapters over existing pricing, lookup, model and policy code."""

from typing import Any

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

from config.constants import MODELLING_COLUMNS
from loanserve.core.loan_calculations import calculate_monthly_installment
from loanserve.data_access.database_loader import ApplicationDatabase
from loanserve.retrieval.filtered_search import filtered_search
from loanserve.retrieval.vector_store import load_embedder, open_policy_store
from loanserve.risk_models.baseline_model import load_model, predict_default_probability


class ToolError(Exception):
    """A requested tool cannot provide a trustworthy result."""


class InstallmentRequest(BaseModel):
    principal_inr: float = Field(gt=0, allow_inf_nan=False)
    annual_interest_rate_percent: float = Field(ge=0, allow_inf_nan=False)
    tenure_months: int = Field(gt=0)


class ApplicationRequest(BaseModel):
    application_id: str = Field(pattern=r"(?i)^(?:LA|LP)\d{6}$")


class RiskRequest(BaseModel):
    application: dict[str, Any]


class PolicyRequest(BaseModel):
    question: str = Field(min_length=3)
    how_many: int = Field(default=4, ge=1, le=10)


def calculate_installment(arguments):
    try:
        request = InstallmentRequest.model_validate(arguments)
        amount = calculate_monthly_installment(**request.model_dump())
        return {"monthly_installment_inr": round(amount, 2)}
    except (ValidationError, ValueError, TypeError) as error:
        raise ToolError(str(error)) from error


def lookup_application(arguments, database_path):
    try:
        request = ApplicationRequest.model_validate(arguments)
        database = ApplicationDatabase(database_path)
        found = database.find_application(request.application_id.upper())
        database.connection.close()
        if found is None:
            raise ToolError(f"Application {request.application_id.upper()} not found")
        return found
    except Exception as error:
        raise ToolError(str(error)) from error


def predict_default_risk(arguments, champion_path):
    try:
        application = RiskRequest.model_validate(arguments).application
        missing = set(MODELLING_COLUMNS) - set(application)
        if missing:
            raise ToolError(f"Missing model columns: {sorted(missing)}")
        model = load_model(champion_path)
        probability = predict_default_probability(model, pd.DataFrame([application]))[0]
        return {"default_probability": round(float(probability), 6)}
    except (ValidationError, ValueError, TypeError, KeyError) as error:
        raise ToolError(str(error)) from error


def search_policy_documents(arguments, store_path):
    try:
        request = PolicyRequest.model_validate(arguments)
        collection = open_policy_store(store_path)
        passages = filtered_search(collection, request.question, load_embedder(), request.how_many)
        if not passages:
            raise ToolError(f"No policy passages found for {request.question}")
        return {"passages": [
            {key: passage[key] for key in ("chunk_id", "text", "heading", "document_id")}
            for passage in passages
        ]}
    except ValidationError as error:
        raise ToolError(str(error)) from error
