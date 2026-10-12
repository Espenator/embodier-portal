"""SQLAlchemy models. Postgres in production; sqlite in tests."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, Numeric, String,
                        Text, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _now():
    return dt.datetime.now(dt.timezone.utc)


class Member(Base):
    __tablename__ = "members"

    phone: Mapped[str] = mapped_column(String(32), primary_key=True)
    tier: Mapped[str] = mapped_column(String(32), nullable=False,
                                      default="inner_circle")
    status: Mapped[str] = mapped_column(String(32), nullable=False,
                                        default="active")
    is_broker: Mapped[bool] = mapped_column(Boolean, nullable=False,
                                            default=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False,
                                              default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now,
                                                    onupdate=_now)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    phone: Mapped[str] = mapped_column(String(32),
                                       ForeignKey("members.phone"),
                                       nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False,
                                            unique=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now)


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    phone: Mapped[str] = mapped_column(String(32),
                                       ForeignKey("members.phone"),
                                       nullable=False, index=True)
    asset_name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_kind: Mapped[str] = mapped_column(String(64), nullable=False,
                                            default="embodiment")
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False,
                                          default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False,
                                          default="USD")
    status: Mapped[str] = mapped_column(String(32), nullable=False,
                                        default="active")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now)


class Interest(Base):
    __tablename__ = "interests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    phone: Mapped[str] = mapped_column(String(32),
                                       ForeignKey("members.phone"),
                                       nullable=False, index=True)
    offering_id: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # pre-DASP: every interest lands as "waitlisted" — nothing is a purchase.
    status: Mapped[str] = mapped_column(String(32), nullable=False,
                                        default="waitlisted")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    phone: Mapped[str] = mapped_column(String(32),
                                       ForeignKey("members.phone"),
                                       nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False,
                                          default="general")
    url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now)


class BrokerDeal(Base):
    __tablename__ = "broker_deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    broker_phone: Mapped[str] = mapped_column(String(32),
                                              ForeignKey("members.phone"),
                                              nullable=False, index=True)
    property_name: Mapped[str] = mapped_column(String(200), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False,
                                       default="sourced")
    deal_value: Mapped[float] = mapped_column(Numeric(18, 2), nullable=True)
    commission_pct: Mapped[float] = mapped_column(Numeric(6, 3), nullable=True)
    commission_status: Mapped[str] = mapped_column(String(32),
                                                  nullable=False,
                                                  default="pending")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now,
                                                    onupdate=_now)


class BrokerBuyBox(Base):
    __tablename__ = "broker_buybox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    broker_phone: Mapped[str] = mapped_column(String(32),
                                              ForeignKey("members.phone"),
                                              nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(120), nullable=False,
                                        default="")
    min_keys: Mapped[int] = mapped_column(Integer, nullable=True)
    max_keys: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now,
                                                    onupdate=_now)


class CourseEnrollment(Base):
    """$100 course enrollment. Created by the Brain's Stripe webhook via the
    internal enroll endpoint (keyed by verified phone)."""
    __tablename__ = "course_enrollments"

    phone: Mapped[str] = mapped_column(String(32),
                                       ForeignKey("members.phone"),
                                       primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False,
                                        default="stripe")
    enrolled_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                     default=_now)
    completed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                      nullable=True)


class CourseModuleProgress(Base):
    """Per-member, per-module progress: lessons read + quiz state."""
    __tablename__ = "course_module_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    phone: Mapped[str] = mapped_column(String(32),
                                       ForeignKey("members.phone"),
                                       nullable=False, index=True)
    module_id: Mapped[str] = mapped_column(String(64), nullable=False)
    lessons_done: Mapped[int] = mapped_column(Integer, nullable=False,
                                              default=0)
    quiz_passed: Mapped[bool] = mapped_column(Boolean, nullable=False,
                                              default=False)
    quiz_best: Mapped[int] = mapped_column(Integer, nullable=False,
                                           default=0)
    quiz_attempts: Mapped[int] = mapped_column(Integer, nullable=False,
                                               default=0)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now,
                                                    onupdate=_now)


class CourseQuizAttempt(Base):
    """Immutable record of each quiz submission (audit trail)."""
    __tablename__ = "course_quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    phone: Mapped[str] = mapped_column(String(32),
                                       ForeignKey("members.phone"),
                                       nullable=False, index=True)
    module_id: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False,
                                         default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now)


class CourseCertificate(Base):
    """Issued once all modules are quiz-passed. Deterministic ID per phone."""
    __tablename__ = "course_certificates"

    phone: Mapped[str] = mapped_column(String(32),
                                       ForeignKey("members.phone"),
                                       primary_key=True)
    certificate_id: Mapped[str] = mapped_column(String(64), nullable=False,
                                                unique=True)
    certified_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                      default=_now)


class ReferralEvent(Base):
    """A signup attributed to a member's referral code (recorded by the Brain
    at enrollment time via the internal endpoint)."""
    __tablename__ = "referral_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    referrer_phone: Mapped[str] = mapped_column(String(32),
                                                ForeignKey("members.phone"),
                                                nullable=False, index=True)
    referred_phone: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now)


class ReferralCode(Base):
    """Stable personal referral code per member (issued lazily)."""
    __tablename__ = "referral_codes"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    phone: Mapped[str] = mapped_column(String(32),
                                       ForeignKey("members.phone"),
                                       nullable=False, unique=True,
                                       index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True),
                                                    default=_now)
