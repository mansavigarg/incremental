"""Interchangeable application stores behind one contract."""

from abc import ABC, abstractmethod

from sqlalchemy import func, select

from loanserve.api.orm_models import Applicant, StoredApplication


STORED_COLUMNS = (
    "application_id", "applicant_name", "pan_number", "mobile_number", "email_address",
    "loan_type", "loan_amount_inr", "tenure_months", "monthly_income_inr", "age_years",
    "credit_score", "collateral_value_inr",
)


class ApplicationRepository(ABC):
    @abstractmethod
    def save_application(self, application_record):
        """Return a new stored record with a minted identifier."""

    @abstractmethod
    def find_application(self, application_id):
        """Return the record, or None when its identifier is unknown."""

    @abstractmethod
    def list_applications(self, loan_type, limit, offset):
        """Return a page of records and the total number matching."""

    @abstractmethod
    def replace_application(self, application_id, application_record):
        """Return the updated record, or None when absent."""

    @abstractmethod
    def delete_application(self, application_id):
        """Return whether a record was removed."""


class InMemoryApplicationRepository(ApplicationRepository):
    def __init__(self):
        self.stored_applications = {}
        self.applications_created = 0

    def save_application(self, application_record):
        self.applications_created += 1
        application_id = f"LA{self.applications_created:06d}"
        stored = dict(application_record, application_id=application_id)
        self.stored_applications[application_id] = stored
        return stored.copy()

    def find_application(self, application_id):
        stored = self.stored_applications.get(application_id)
        return stored.copy() if stored is not None else None

    def list_applications(self, loan_type, limit, offset):
        matches = [row for row in self.stored_applications.values()
                   if loan_type is None or row["loan_type"] == loan_type]
        return [row.copy() for row in matches[offset:offset + limit]], len(matches)

    def replace_application(self, application_id, application_record):
        if application_id not in self.stored_applications:
            return None
        stored = dict(application_record, application_id=application_id)
        self.stored_applications[application_id] = stored
        return stored.copy()

    def delete_application(self, application_id):
        return self.stored_applications.pop(application_id, None) is not None


class SqlApplicationRepository(ApplicationRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def as_record(self, stored):
        return {column: getattr(stored, column) for column in STORED_COLUMNS}

    def save_application(self, application_record):
        with self.session_factory() as session, session.begin():
            latest = session.scalar(select(func.max(StoredApplication.application_id)))
            next_number = int(latest[2:]) + 1 if latest else 1
            application_id = f"LA{next_number:06d}"
            name = application_record["applicant_name"]
            if session.get(Applicant, name) is None:
                session.add(Applicant(applicant_name=name))
            stored = StoredApplication(application_id=application_id, **application_record)
            session.add(stored)
            session.flush()
            return self.as_record(stored)

    def find_application(self, application_id):
        with self.session_factory() as session:
            stored = session.get(StoredApplication, application_id)
            return self.as_record(stored) if stored is not None else None

    def list_applications(self, loan_type, limit, offset):
        with self.session_factory() as session:
            condition = StoredApplication.loan_type == loan_type if loan_type else True
            total = session.scalar(select(func.count()).select_from(StoredApplication).where(condition))
            rows = session.scalars(select(StoredApplication).where(condition).order_by(
                StoredApplication.application_id).offset(offset).limit(limit)).all()
            return [self.as_record(row) for row in rows], total

    def replace_application(self, application_id, application_record):
        with self.session_factory() as session, session.begin():
            stored = session.get(StoredApplication, application_id)
            if stored is None:
                return None
            name = application_record["applicant_name"]
            if session.get(Applicant, name) is None:
                session.add(Applicant(applicant_name=name))
            for column, value in application_record.items():
                setattr(stored, column, value)
            session.flush()
            return self.as_record(stored)

    def delete_application(self, application_id):
        with self.session_factory() as session, session.begin():
            stored = session.get(StoredApplication, application_id)
            if stored is None:
                return False
            session.delete(stored)
            return True
