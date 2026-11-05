"""First lending exercise: a complete top-level terminal program."""

loan_type = input().strip().lower()
principal_inr = float(input())
annual_interest_rate_percent = float(input())
tenure_months = int(input())
monthly_income_inr = float(input())
applicant_age_years = int(input())

maximums = {"home": 15000000.0, "vehicle": 2500000.0, "gold": 1000000.0, "personal": 1500000.0}
monthly_rate = annual_interest_rate_percent / 1200
if monthly_rate == 0:
    monthly_installment_inr = principal_inr / tenure_months
else:
    factor = (1 + monthly_rate) ** tenure_months
    monthly_installment_inr = principal_inr * monthly_rate * factor / (factor - 1)
total_interest_inr = monthly_installment_inr * tenure_months - principal_inr
debt_to_income_ratio = monthly_installment_inr / monthly_income_inr

print("LoanServe Eligibility Check")
print(f"Loan Type: {loan_type}")
print(f"Principal (INR): {principal_inr:.2f}")
print(f"Annual Interest Rate (%): {annual_interest_rate_percent:.2f}")
print(f"Tenure (months): {tenure_months}")
print(f"Monthly Income (INR): {monthly_income_inr:.2f}")
print(f"Applicant Age (years): {applicant_age_years}")
print(f"Monthly Instalment (INR): {monthly_installment_inr:.2f}")
print(f"Total Interest (INR): {total_interest_inr:.2f}")
print(f"Debt-to-Income Ratio: {debt_to_income_ratio:.2f}")
print("Repayment Schedule (first 3 months):")
balance = principal_inr
for month in range(1, 4):
    interest = balance * monthly_rate
    principal_paid = monthly_installment_inr - interest
    balance -= principal_paid
    if abs(balance) < 0.005:
        balance = 0.0
    print(f"Month {month} | Interest: {interest:.2f} | Principal: {principal_paid:.2f} | Outstanding: {balance:.2f}")

reasons = []
if loan_type not in maximums:
    reasons.append(f"Loan amount {principal_inr:.2f} exceeds unsupported {loan_type} maximum 0.00")
else:
    if not 21 <= applicant_age_years <= 60:
        reasons.append(f"Age {applicant_age_years} is outside 21 to 60 years")
    if debt_to_income_ratio > 0.5:
        reasons.append(f"Instalment {monthly_installment_inr:.2f} exceeds 0.50 of income {monthly_income_inr:.2f} (ratio {debt_to_income_ratio:.2f})")
    if principal_inr > maximums[loan_type]:
        reasons.append(f"Loan amount {principal_inr:.2f} exceeds {loan_type} maximum {maximums[loan_type]:.2f}")
print("Decision: REJECTED" if reasons else "Decision: APPROVED")
for reason in reasons:
    print(f"Reason: {reason}")
