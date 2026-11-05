"""Loan applications and product specific eligibility rules."""

from config.constants import (
    INTEREST_RATE_PERCENT_BY_LOAN_TYPE, MAXIMUM_APPLICANT_AGE_YEARS,
    MAXIMUM_INSTALLMENT_TO_INCOME_RATIO, MAXIMUM_LOAN_AMOUNTS_INR,
    MAXIMUM_LOAN_TO_VALUE_RATIO, MINIMUM_APPLICANT_AGE_YEARS,
    MINIMUM_CREDIT_SCORE_FOR_UNSECURED, SECURED_LOAN_TYPES,
)
from loanserve.core.loan_calculations import calculate_debt_to_income_ratio, calculate_monthly_installment
from loanserve.core.exceptions import InvalidApplicationError, UnsupportedLoanTypeError


class LoanApplication:
    def __init__(self, application_record):
        self.loan_type = str(application_record["loan_type"]).strip().lower()
        if self.loan_type not in MAXIMUM_LOAN_AMOUNTS_INR:
            raise UnsupportedLoanTypeError(f"Unsupported loan type: {self.loan_type}")
        try:
            self.principal_inr = float(application_record["loan_amount_inr"])
            self.tenure_months = int(float(application_record["tenure_months"]))
            self.monthly_income_inr = float(application_record["monthly_income_inr"])
            self.applicant_age_years = int(float(application_record["age_years"]))
        except (KeyError, ValueError, TypeError) as error:
            raise InvalidApplicationError(f"Invalid application field: {error}") from error

    def interest_rate_percent(self):
        return INTEREST_RATE_PERCENT_BY_LOAN_TYPE[self.loan_type]

    def monthly_installment_inr(self):
        return calculate_monthly_installment(self.principal_inr, self.interest_rate_percent(), self.tenure_months)

    def debt_to_income_ratio(self):
        return calculate_debt_to_income_ratio(self.monthly_installment_inr(), self.monthly_income_inr)

    def rejection_reasons(self):
        reasons = []
        if not MINIMUM_APPLICANT_AGE_YEARS <= self.applicant_age_years <= MAXIMUM_APPLICANT_AGE_YEARS:
            reasons.append(f"Age {self.applicant_age_years} is outside {MINIMUM_APPLICANT_AGE_YEARS} to {MAXIMUM_APPLICANT_AGE_YEARS}")
        ratio = self.debt_to_income_ratio()
        if ratio > MAXIMUM_INSTALLMENT_TO_INCOME_RATIO:
            reasons.append(f"Instalment {self.monthly_installment_inr():.2f} exceeds {MAXIMUM_INSTALLMENT_TO_INCOME_RATIO:.2f} of income {self.monthly_income_inr:.2f} (ratio {ratio:.2f})")
        maximum = MAXIMUM_LOAN_AMOUNTS_INR[self.loan_type]
        if self.principal_inr > maximum:
            reasons.append(f"Loan amount {self.principal_inr:.2f} exceeds {self.loan_type} maximum {maximum:.2f}")
        return reasons

    def is_eligible(self):
        return not self.rejection_reasons()


class SecuredLoanApplication(LoanApplication):
    def __init__(self, application_record):
        super().__init__(application_record)
        self.collateral_value_inr = float(application_record["collateral_value_inr"])

    def loan_to_value_ratio(self):
        if self.collateral_value_inr <= 0:
            raise InvalidApplicationError("Collateral value must be positive")
        return self.principal_inr / self.collateral_value_inr

    def rejection_reasons(self):
        reasons = super().rejection_reasons()
        ratio = self.loan_to_value_ratio()
        if ratio > MAXIMUM_LOAN_TO_VALUE_RATIO:
            reasons.append(f"Loan-to-value ratio {ratio:.2f} exceeds {MAXIMUM_LOAN_TO_VALUE_RATIO:.2f}")
        return reasons


class UnsecuredLoanApplication(LoanApplication):
    def __init__(self, application_record):
        super().__init__(application_record)
        self.credit_score = int(application_record["credit_score"])

    def rejection_reasons(self):
        reasons = super().rejection_reasons()
        if self.credit_score < MINIMUM_CREDIT_SCORE_FOR_UNSECURED:
            reasons.append(f"Credit score {self.credit_score} is below {MINIMUM_CREDIT_SCORE_FOR_UNSECURED}")
        return reasons


def create_loan_application(application_record):
    product = str(application_record["loan_type"]).strip().lower()
    application_class = SecuredLoanApplication if product in SECURED_LOAN_TYPES else UnsecuredLoanApplication
    return application_class(application_record)


if __name__ == "__main__":
    sample = {"loan_type": "personal", "loan_amount_inr": 100000, "tenure_months": 12,
              "monthly_income_inr": 50000, "age_years": 30, "credit_score": 610}
    application = create_loan_application(sample)
    print(type(application).__name__, application.is_eligible(), application.rejection_reasons())
