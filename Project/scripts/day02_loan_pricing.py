"""Second lending exercise: calculations and an object before packaging."""

INTEREST_RATE_PERCENT_BY_LOAN_TYPE = {"home": 8.5, "vehicle": 9.75, "gold": 11.0, "personal": 14.5}
MAXIMUM_LOAN_AMOUNTS_INR = {"home": 15000000.0, "vehicle": 2500000.0, "gold": 1000000.0, "personal": 1500000.0}
MINIMUM_APPLICANT_AGE_YEARS = 21
MAXIMUM_APPLICANT_AGE_YEARS = 60
MAXIMUM_INSTALLMENT_TO_INCOME_RATIO = 0.5


def calculate_monthly_installment(principal_inr, annual_interest_rate_percent, tenure_months):
    monthly_rate = annual_interest_rate_percent / 1200
    if monthly_rate == 0:
        return principal_inr / tenure_months
    factor = (1 + monthly_rate) ** tenure_months
    return principal_inr * monthly_rate * factor / (factor - 1)


def calculate_debt_to_income_ratio(monthly_installment_inr, monthly_income_inr):
    return monthly_installment_inr / monthly_income_inr


class LoanApplication:
    def __init__(self, application_record):
        self.loan_type = str(application_record["loan_type"]).strip().lower()
        self.principal_inr = float(application_record["loan_amount_inr"])
        self.tenure_months = int(application_record["tenure_months"])
        self.monthly_income_inr = float(application_record["monthly_income_inr"])
        self.applicant_age_years = int(application_record["age_years"])

    def interest_rate_percent(self):
        return INTEREST_RATE_PERCENT_BY_LOAN_TYPE[self.loan_type]

    def monthly_installment_inr(self):
        return calculate_monthly_installment(self.principal_inr, self.interest_rate_percent(), self.tenure_months)

    def debt_to_income_ratio(self):
        return calculate_debt_to_income_ratio(self.monthly_installment_inr(), self.monthly_income_inr)

    def rejection_reasons(self):
        if self.loan_type not in MAXIMUM_LOAN_AMOUNTS_INR:
            return [f"Loan amount {self.principal_inr:.2f} exceeds unsupported {self.loan_type} maximum 0.00"]
        reasons = []
        if not MINIMUM_APPLICANT_AGE_YEARS <= self.applicant_age_years <= MAXIMUM_APPLICANT_AGE_YEARS:
            reasons.append("Age is outside the permitted band")
        if self.debt_to_income_ratio() > MAXIMUM_INSTALLMENT_TO_INCOME_RATIO:
            reasons.append("Instalment exceeds the affordability limit")
        if self.principal_inr > MAXIMUM_LOAN_AMOUNTS_INR.get(self.loan_type, 0):
            reasons.append("Loan amount exceeds the product maximum")
        return reasons

    def is_eligible(self):
        return not self.rejection_reasons()
