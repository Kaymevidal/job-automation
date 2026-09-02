from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.core.constants import ApplicationStatus, ExperienceLevel, ScraperSource, WorkMode


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    experience_level: Mapped[ExperienceLevel | None] = mapped_column(nullable=True)
    resume_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    profile_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    applications: Mapped[list["Application"]] = relationship(back_populates="user")


class Vacancy(Base):
    __tablename__ = "vacancies"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_vacancy_source_external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_mode: Mapped[WorkMode | None] = mapped_column(nullable=True)
    url: Mapped[str] = mapped_column(String(1000))
    source: Mapped[ScraperSource] = mapped_column()
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    experience_level: Mapped[ExperienceLevel | None] = mapped_column(nullable=True)
    salary_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    compatibility_score: Mapped[float | None] = mapped_column(nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(default=utcnow)

    applications: Mapped[list["Application"]] = relationship(back_populates="vacancy")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "vacancy_id", name="uq_application_user_vacancy"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id"))
    status: Mapped[ApplicationStatus] = mapped_column(default=ApplicationStatus.PENDING)
    cover_letter_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_letter_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_used_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="applications")
    vacancy: Mapped["Vacancy"] = relationship(back_populates="applications")


class SchedulerJob(Base):
    __tablename__ = "scheduler_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(String(255), unique=True)
    job_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    next_run_time: Mapped[datetime | None] = mapped_column(nullable=True)
    last_run_time: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
