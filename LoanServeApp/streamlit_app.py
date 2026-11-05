"""LoanServe officer workspace. All operations use the public FastAPI endpoints."""

import os

import httpx
import pandas as pd
import streamlit as st


API = os.getenv("LOANSERVE_API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="LoanServe", page_icon="▣", layout="wide")
st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&display=swap');
    html, body, [data-testid="stApp"] {font-family: Geist, system-ui, sans-serif;}
    .block-container {max-width: 1160px; padding-top: 2rem;}
    h1 {font-size: 1.6rem !important; letter-spacing: -.035em; font-weight: 600 !important;}
    h2, h3 {letter-spacing: -.025em;}
    div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"]
      {background: #141414; border-color: #141414; color: white;}
    div.stButton > button, div.stFormSubmitButton > button {border-radius: 6px; box-shadow: none;}
    [data-testid="stForm"], [data-testid="stExpander"] {background: #ffffff; border: 1px solid #dfe3e8; border-radius: 8px;}
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
    [data-testid="stTextArea"] textarea, [data-baseweb="select"] > div
      {background: #ffffff !important; color: #0a0a0a !important; border: 1px solid #141414 !important;}
    [data-testid="stTextInput"] input::placeholder, [data-testid="stTextArea"] textarea::placeholder
      {color: #6b7280 !important; opacity: 1;}
    [data-testid="stTextInput"] label, [data-testid="stNumberInput"] label,
    [data-testid="stTextArea"] label {color: #1f2937 !important;}
    [data-testid="stMetricValue"] {font-variant-numeric: tabular-nums; letter-spacing: -.03em;}
    [data-testid="stTabs"] button {font-size: .92rem;}
    </style>""",
    unsafe_allow_html=True,
)


def call(method, path, *, json=None, params=None):
    headers = {}
    if st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        with httpx.Client(base_url=API, timeout=300) as client:
            response = client.request(method, path, json=json, params=params, headers=headers)
        if response.status_code == 204:
            return True
        data = response.json()
        if response.is_error:
            detail = data.get("detail", data) if isinstance(data, dict) else data
            st.error(f"API {response.status_code}: {detail}")
            return None
        return data
    except (httpx.ConnectError, httpx.TimeoutException) as error:
        st.error(f"API unavailable at {API}: {error}")
        return None


def money(value):
    return f"₹{value:,.2f}"


def application_form(initial=None, key="new"):
    data = initial or {}
    with st.form(key):
        left, right = st.columns(2)
        with left:
            name = st.text_input("Applicant name", data.get("applicant_name", ""))
            product = st.selectbox("Loan type", ["personal", "home", "vehicle", "gold"],
                                   index=["personal", "home", "vehicle", "gold"].index(data.get("loan_type", "personal")))
            amount = st.number_input("Loan amount (₹)", min_value=1.0, value=float(data.get("loan_amount_inr", 100000.0)), step=1000.0)
            tenure = st.number_input("Tenure (months)", min_value=1, max_value=360, value=int(data.get("tenure_months", 12)))
            income = st.number_input("Monthly income (₹)", min_value=1.0, value=float(data.get("monthly_income_inr", 50000.0)), step=1000.0)
            collateral = st.number_input("Collateral value (₹)", min_value=0.0,
                                         value=float(data.get("collateral_value_inr", 0.0)), step=1000.0,
                                         help="Required for home, vehicle and gold loans.")
        with right:
            age = st.number_input("Age (years)", min_value=18, max_value=100, value=int(data.get("age_years", 30)))
            score = st.number_input("Credit score", min_value=300, max_value=900, value=int(data.get("credit_score", 750)))
            pan = st.text_input("PAN", data.get("pan_number", ""), placeholder="ABCDE1234F")
            mobile = st.text_input("Mobile number", data.get("mobile_number", ""), placeholder="9876543210")
            email = st.text_input("Email", data.get("email_address", ""), placeholder="name@example.com")
        submitted = st.form_submit_button("Save application", type="primary")
    if not submitted:
        return None
    return {"applicant_name": name, "loan_type": product, "loan_amount_inr": amount,
            "tenure_months": tenure, "monthly_income_inr": income, "age_years": age,
            "credit_score": score, "collateral_value_inr": collateral,
            "pan_number": pan, "mobile_number": mobile, "email_address": email}


def account_screen():
    st.title("LoanServe")
    st.caption("Loan servicing workspace · Sign in to continue")
    login, signup = st.tabs(["Sign in", "Create account"])
    with login:
        with st.form("login"):
            user = st.text_input("User name")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary")
        if submitted:
            result = call("POST", "/api/v1/auth/login", json={"user_name": user, "password": password})
            if result:
                st.session_state.token = result["access_token"]
                st.session_state.user = user
                account = call("GET", "/api/v1/auth/me")
                st.session_state.role = account["role"] if account else "loan_officer"
                st.rerun()
    with signup:
        with st.form("signup"):
            new_user = st.text_input("New user name")
            new_password = st.text_input("New password", type="password")
            created = st.form_submit_button("Create account")
        if created:
            result = call("POST", "/api/v1/auth/signup",
                          json={"user_name": new_user, "password": new_password})
            if result:
                st.success(f"{result['role'].replace('_', ' ').title()} account created. Sign in using the first tab.")


def applications_screen():
    st.subheader("Applications")
    create_tab, review_tab = st.tabs(["New application", "Review applications"])
    with create_tab:
        payload = application_form()
        if payload:
            result = call("POST", "/api/v1/applications", json=payload)
            if result:
                st.success(f"Created {result['application_id']}")
                st.json(result)
    with review_tab:
        filter_col, limit_col = st.columns([3, 1])
        product = filter_col.selectbox("Filter loan type", ["All", "personal", "home", "vehicle", "gold"])
        limit = limit_col.number_input("Rows", min_value=1, max_value=100, value=20)
        params = {"limit": limit, "offset": 0}
        if product != "All":
            params["loan_type"] = product
        page = call("GET", "/api/v1/applications", params=params)
        if page is None:
            return
        st.caption(f"{page['total']} applications")
        if not page["applications"]:
            st.info("No applications yet. Create one in the first tab.")
            return
        rows = page["applications"]
        st.dataframe(pd.DataFrame([{
            "ID": row["application_id"], "Applicant": row["applicant_name"],
            "Loan": row["loan_type"], "Amount (₹)": row["loan_amount_inr"],
            "Monthly (₹)": row["monthly_installment_inr"],
            "Eligible": row["is_eligible"],
        } for row in rows]), hide_index=True, use_container_width=True)
        selected = st.selectbox("Open application", [row["application_id"] for row in rows])
        detail = call("GET", f"/api/v1/applications/{selected}")
        if detail is None:
            return
        a, b, c = st.columns(3)
        a.metric("Loan amount", money(detail["loan_amount_inr"]))
        b.metric("Monthly installment", money(detail["monthly_installment_inr"]))
        c.metric("Eligibility", "Eligible" if detail["is_eligible"] else "Review")
        if detail["rejection_reasons"]:
            st.warning("; ".join(detail["rejection_reasons"]))
        with st.expander("Repayment schedule"):
            schedule = call("GET", f"/api/v1/applications/{selected}/schedule")
            if schedule:
                values = schedule["outstanding_after_each_month"]
                st.line_chart(pd.DataFrame({"Outstanding (₹)": values}, index=range(1, len(values) + 1)), color="#1d5fbf")
                st.dataframe(pd.DataFrame({"Month": range(1, len(values) + 1), "Outstanding (₹)": values}), hide_index=True)
        with st.expander("Edit application"):
            original = call("GET", f"/api/v1/applications/{selected}/details")
            if original:
                edited = application_form(original, key=f"edit-{selected}")
                if edited and call("PUT", f"/api/v1/applications/{selected}", json=edited):
                    st.success("Application updated")
                    st.rerun()
        with st.expander("Delete application"):
            st.caption("Administrator account required. This cannot be undone.")
            if st.button("Delete this application"):
                if call("DELETE", f"/api/v1/applications/{selected}"):
                    st.success("Application deleted")
                    st.rerun()


def policy_screen():
    st.subheader("Policy evidence")
    st.caption("Search retrieves local passages. Answer asks Gemini to respond using those passages.")
    with st.form("policy"):
        question = st.text_input("Policy question", "How soon is an application decided?")
        count = st.slider("Passages", min_value=1, max_value=10, value=4)
        search = st.form_submit_button("Search policy", type="primary")
    if search:
        result = call("POST", "/api/v1/policy/search", json={"question": question, "how_many": count})
        if result:
            st.session_state.policy_question = question
            st.session_state.policy_count = count
            st.session_state.policy_result = result
            st.session_state.pop("policy_answer", None)
    result = st.session_state.get("policy_result")
    if result:
        st.caption(f"Product: {result['product_type']} · {len(result['passages'])} retrieved passages")
        for passage in result["passages"]:
            with st.expander(f"{passage['chunk_id']} · {passage['heading']}"):
                st.caption(passage["document_id"])
                st.write(passage["text"])
        if st.button("Generate grounded answer", type="primary"):
            answer = call("POST", "/api/v1/policy/answer",
                          json={"question": st.session_state.policy_question,
                                "how_many": st.session_state.policy_count})
            if answer:
                st.session_state.policy_answer = answer
        if st.session_state.get("policy_answer"):
            answer = st.session_state.policy_answer
            st.markdown(answer["answer"])
            st.caption(f"Verified citations: {answer['citations'] or 'none'}")


def assistant_screen():
    st.subheader("Assistant")
    st.caption("The assistant classifies, selects a tool, checks evidence, and may pause for approval.")
    with st.form("assistant"):
        question = st.text_area("Customer question", placeholder="Ask about policy, a loan calculation, or an application")
        ask = st.form_submit_button("Ask assistant", type="primary")
    if ask:
        result = call("POST", "/api/v1/assistant/ask", json={"question": question})
        if result:
            st.session_state.assistant_result = result
            st.session_state.assistant_question = question
    result = st.session_state.get("assistant_result")
    if result:
        if result["needs_approval"]:
            st.warning("This answer is waiting for administrator approval.")
        elif result["refused"]:
            st.warning(result["answer"])
        else:
            st.write(result["answer"])
        st.caption(f"Category: {result['category']} · Confidence: {result['confidence']} · Thread: {result['thread_id']}")
        with st.expander("Workflow trace"):
            st.write(" → ".join(result["steps"]))
            for note in result["narration"]:
                st.write(note)
        if result["needs_approval"]:
            approve, deny = st.columns(2)
            decision = True if approve.button("Approve") else False if deny.button("Deny") else None
            if decision is not None:
                resumed = call("POST", "/api/v1/assistant/ask", json={
                    "question": st.session_state.assistant_question,
                    "thread_id": result["thread_id"], "approved": decision,
                })
                if resumed:
                    st.session_state.assistant_result = resumed
                    st.rerun()


def main():
    if not st.session_state.get("token"):
        account_screen()
        return
    top_left, top_right = st.columns([4, 1])
    top_left.title("LoanServe")
    top_left.caption("Applications · policy evidence · assisted answers")
    if top_right.button(f"Sign out · {st.session_state.get('user', '')}"):
        st.session_state.clear()
        st.rerun()
    overview, applications, policy, assistant = st.tabs(["Overview", "Applications", "Policy", "Assistant"])
    with overview:
        health = call("GET", "/health")
        if health:
            a, b = st.columns(2)
            a.metric("Applications", health["applications"])
            b.metric("API", "Connected" if health["status"] == "ok" else "Unavailable")
            st.write("Create a loan application, review repayment, search policy passages, or ask the assistant.")
            st.link_button("Open Swagger API", f"{API}/docs")
        if st.session_state.get("role") == "administrator":
            with st.expander("Create another administrator"):
                with st.form("create_admin"):
                    admin_name = st.text_input("User name")
                    admin_password = st.text_input("Password", type="password")
                    create_admin = st.form_submit_button("Create administrator")
                if create_admin:
                    result = call("POST", "/api/v1/auth/signup", json={
                        "user_name": admin_name, "password": admin_password, "role": "administrator"
                    })
                    if result:
                        st.success("Administrator created")
    with applications:
        applications_screen()
    with policy:
        policy_screen()
    with assistant:
        assistant_screen()


if __name__ == "__main__":
    main()
