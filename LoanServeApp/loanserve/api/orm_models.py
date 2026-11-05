"""SQLAlchemy tables for applicants and their applications."""

from sqlalchemy import Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class Applicant(Base):
    __tablename__ = "applicants"

    applicant_name: Mapped[str] = mapped_column(String(80), primary_key=True)
    applications: Mapped[list["StoredApplication"]] = relationship(
        back_populates="applicant", cascade="all, delete-orphan"
    )


class StoredApplication(Base):
    __tablename__ = "applications"

    application_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    applicant_name: Mapped[str] = mapped_column(ForeignKey("applicants.applicant_name"))
    pan_number: Mapped[str] = mapped_column(String(10))
    mobile_number: Mapped[str] = mapped_column(String(10))
    email_address: Mapped[str] = mapped_column(String(254))
    loan_type: Mapped[str] = mapped_column(String(20))
    loan_amount_inr: Mapped[float] = mapped_column(Float)
    tenure_months: Mapped[int] = mapped_column(Integer)
    monthly_income_inr: Mapped[float] = mapped_column(Float)
    age_years: Mapped[int] = mapped_column(Integer)
    credit_score: Mapped[int] = mapped_column(Integer)
    collateral_value_inr: Mapped[float] = mapped_column(Float)
    applicant: Mapped[Applicant] = relationship(back_populates="applications")


def create_session_factory(database_url):
    options = {"connect_args": {"check_same_thread": False}}
    if database_url in ("sqlite://", "sqlite:///:memory:"):
        options["poolclass"] = StaticPool
    engine = create_engine(database_url, **options)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


if __name__ == "__main__":
    factory = create_session_factory("sqlite://")
    with factory() as session:
        person = Applicant(applicant_name="Aarav Nair")
        person.applications.append(StoredApplication(
            application_id="LA000001", pan_number="ABCDE1234F", mobile_number="9876543210",
            email_address="aarav@example.com", loan_type="personal", loan_amount_inr=500000,
            tenure_months=36, monthly_income_inr=60000, age_years=32, credit_score=760,
            collateral_value_inr=0,
        ))
        session.add(person)
        session.commit()
        print(f"{len(session.get(Applicant, 'Aarav Nair').applications)} application(s)")
