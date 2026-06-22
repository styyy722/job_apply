"""ORM models: CVs, Jobs, and Applications (the tracker)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CV(Base):
    __tablename__ = "cvs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text)
    # Structured CV extracted by the model (skills, experience, education, ...).
    structured: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    applications: Mapped[list["Application"]] = relationship(
        back_populates="cv", cascade="all, delete-orphan"
    )


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_job_source_external"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(50))  # greenhouse | lever | manual
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    apply_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    # Model's analysis of the JD (requirements, keywords, tone, ...).
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    applications: Mapped[list["Application"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class Applicant(Base):
    """The candidate's contact details, used when submitting via an API.

    Single-row table (id is always 1); the UI saves it once.
    """

    __tablename__ = "applicant"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    links: Mapped[str | None] = mapped_column(Text, nullable=True)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("cv_id", "job_id", name="uq_application_cv_job"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_id: Mapped[int] = mapped_column(ForeignKey("cvs.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))

    # draft -> ready -> submitted -> interviewing -> offer / rejected
    status: Mapped[str] = mapped_column(String(32), default="draft")
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    # How the application was/will be sent and the result of any submission.
    submitted_via: Mapped[str | None] = mapped_column(String(32), nullable=True)
    submit_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    cv: Mapped[CV] = relationship(back_populates="applications")
    job: Mapped[Job] = relationship(back_populates="applications")
