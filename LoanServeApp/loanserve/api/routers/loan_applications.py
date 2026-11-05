"""HTTP routes for application creation, reading, replacement and removal."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status

from loanserve.api import schemas
from loanserve.core.entities import create_loan_application
from loanserve.core.loan_calculations import build_outstanding_balances


router = APIRouter(prefix="/applications", tags=["applications"])


def price_application(stored_application):
    loan = create_loan_application(stored_application)
    return schemas.LoanApplicationResponse(
        application_id=stored_application["application_id"],
        applicant_name=stored_application["applicant_name"],
        loan_type=loan.loan_type,
        loan_amount_inr=loan.principal_inr,
        tenure_months=loan.tenure_months,
        interest_rate_percent=loan.interest_rate_percent(),
        monthly_installment_inr=round(loan.monthly_installment_inr(), 2),
        is_eligible=loan.is_eligible(),
        rejection_reasons=loan.rejection_reasons(),
    )


@router.post("", response_model=schemas.LoanApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(submitted: schemas.LoanApplicationRequest, request: Request):
    stored = request.app.state.application_repository.save_application(submitted.model_dump())
    return price_application(stored)


@router.get("", response_model=schemas.ApplicationPage)
def list_applications(filters: Annotated[schemas.ApplicationFilters, Query()], request: Request):
    rows, total = request.app.state.application_repository.list_applications(
        filters.loan_type, filters.limit, filters.offset
    )
    return schemas.ApplicationPage(
        total=total, limit=filters.limit, offset=filters.offset,
        applications=[price_application(row) for row in rows],
    )


@router.get("/{application_id}/schedule", response_model=schemas.RepaymentSchedule)
def read_schedule(application_id: str, request: Request):
    stored = request.app.state.application_repository.find_application(application_id)
    if stored is None:
        raise HTTPException(status_code=404, detail=f"Application {application_id} not found")
    loan = create_loan_application(stored)
    balances = build_outstanding_balances(loan.principal_inr, loan.interest_rate_percent(), loan.tenure_months)
    return schemas.RepaymentSchedule(
        application_id=application_id,
        outstanding_after_each_month=[round(float(balance), 2) for balance in balances],
    )


@router.get("/{application_id}/details", response_model=schemas.LoanApplicationRequest)
def read_application_details(application_id: str, request: Request):
    stored = request.app.state.application_repository.find_application(application_id)
    if stored is None:
        raise HTTPException(status_code=404, detail=f"Application {application_id} not found")
    return stored


@router.get("/{application_id}", response_model=schemas.LoanApplicationResponse)
def read_application(application_id: str, request: Request):
    stored = request.app.state.application_repository.find_application(application_id)
    if stored is None:
        raise HTTPException(status_code=404, detail=f"Application {application_id} not found")
    return price_application(stored)


@router.put("/{application_id}", response_model=schemas.LoanApplicationResponse)
def replace_application(application_id: str, request: Request, submitted: schemas.LoanApplicationRequest):
    stored = request.app.state.application_repository.replace_application(application_id, submitted.model_dump())
    if stored is None:
        raise HTTPException(status_code=404, detail=f"Application {application_id} not found")
    return price_application(stored)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(application_id: str, request: Request):
    if not request.app.state.application_repository.delete_application(application_id):
        raise HTTPException(status_code=404, detail=f"Application {application_id} not found")
