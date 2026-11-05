"""Pure lending arithmetic shared by scripts, entities and later APIs."""

import math

import numpy as np

from loanserve.core.decorators import reject_negative_arguments
from loanserve.core.exceptions import InvalidApplicationError


@reject_negative_arguments
def calculate_monthly_installment(principal_inr, annual_interest_rate_percent, tenure_months):
    """Fixed payment for a reducing balance loan, without rounding intermediate values."""
    values = (principal_inr, annual_interest_rate_percent, tenure_months)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
        raise InvalidApplicationError("Loan terms must be finite numbers")
    if tenure_months <= 0 or int(tenure_months) != tenure_months:
        raise InvalidApplicationError("Tenure must be a positive whole number of months")
    monthly_rate = annual_interest_rate_percent / 1200
    if monthly_rate == 0:
        return principal_inr / tenure_months
    # expm1 retains precision for interest rates very close to zero.
    growth_minus_one = math.expm1(tenure_months * math.log1p(monthly_rate))
    return principal_inr * monthly_rate * (1 + growth_minus_one) / growth_minus_one


def calculate_debt_to_income_ratio(monthly_installment_inr, monthly_income_inr):
    if not math.isfinite(monthly_income_inr) or monthly_income_inr <= 0:
        raise InvalidApplicationError("Monthly income must be positive and finite")
    return monthly_installment_inr / monthly_income_inr


def build_outstanding_balances(principal_inr, annual_interest_rate_percent, tenure_months):
    payment = calculate_monthly_installment(principal_inr, annual_interest_rate_percent, tenure_months)
    months = np.arange(1, int(tenure_months) + 1, dtype=float)
    monthly_rate = annual_interest_rate_percent / 1200
    if monthly_rate == 0:
        balances = principal_inr - payment * months
    else:
        growth_minus_one = np.expm1(months * np.log1p(monthly_rate))
        balances = principal_inr * (1 + growth_minus_one) - payment * growth_minus_one / monthly_rate
    balances[np.isclose(balances, 0, atol=0.005)] = 0
    return balances


if __name__ == "__main__":
    print(f"instalment: {calculate_monthly_installment(500000, 14, 36):.2f}")
