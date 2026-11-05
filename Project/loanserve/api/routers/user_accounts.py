"""Sign up and exchange a password for a signed token."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from loanserve.api import schemas


router = APIRouter(prefix="/auth", tags=["accounts"])


@router.post("/signup", response_model=schemas.AccountResponse, status_code=status.HTTP_201_CREATED)
def sign_up(submitted: schemas.AccountRequest, request: Request):
    accounts = request.app.state.user_accounts
    if submitted.user_name in accounts:
        raise HTTPException(status_code=409, detail=f"User {submitted.user_name} already exists")
    accounts[submitted.user_name] = {
        "password_hash": request.app.state.password_vault.hash_password(submitted.password),
        "role": submitted.role,
    }
    return schemas.AccountResponse(user_name=submitted.user_name, role=submitted.role)


@router.post("/login", response_model=schemas.TokenResponse)
def log_in(submitted: schemas.AccountRequest, request: Request, background_tasks: BackgroundTasks):
    account = request.app.state.user_accounts.get(submitted.user_name)
    vault = request.app.state.password_vault
    if account is None or not vault.matches_stored_hash(submitted.password, account["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid user name or password")
    guard = request.app.state.access_control
    background_tasks.add_task(guard.record_audit_entry, submitted.user_name, "login")
    return schemas.TokenResponse(access_token=guard.issue_token(submitted.user_name, account["role"]))
