"""Course API: enrollment status, module content, quiz grading, certificates,
and referral tools for the $100 Investment Real Estate Course.

Auth: member endpoints require a Brain-issued session token (same as the rest
of the member API). Quiz grading is server-side — answer keys never leave the
server. The Brain enrolls buyers via the internal endpoint after its Stripe
webhook confirms purchase (keyed by verified phone).

Compliance: all copy is education-framed. No yield/return promises anywhere,
no live token-sale claims (pre-DASP).
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from .. import content as course_content
from ..deps import get_current_member, require_brain_secret
from ..db import get_db
from ..models import (CourseCertificate, CourseEnrollment,
                      CourseModuleProgress, CourseQuizAttempt, Member,
                      ReferralCode, ReferralEvent)

router = APIRouter(prefix="/api")


# --- helpers ---------------------------------------------------------------

def _b32(data: bytes, length: int) -> str:
    return base64.b32encode(data).decode().rstrip("=")[:length]


def referral_code_for(phone: str) -> str:
    """Deterministic personal referral code for a phone number."""
    digest = hashlib.sha256(f"referral:{phone}".encode()).digest()
    return "EMB-" + _b32(digest, 6)


def certificate_id_for(phone: str) -> str:
    digest = hashlib.sha256(f"certificate:{phone}".encode()).digest()
    return "EMB-CRS-" + _b32(digest, 8)


def _get_or_create_code(db: DBSession, phone: str) -> ReferralCode:
    row = db.query(ReferralCode).filter_by(phone=phone).one_or_none()
    if row is None:
        # Extremely unlikely collision: deterministic code per phone, but a
        # different phone could theoretically collide — suffix and retry.
        base = referral_code_for(phone)
        code, n = base, 2
        while db.get(ReferralCode, code) is not None:
            code = f"{base}-{n}"
            n += 1
        row = ReferralCode(code=code, phone=phone)
        db.add(row)
        db.commit()
    return row


def _progress_map(db: DBSession, phone: str) -> dict[str, CourseModuleProgress]:
    rows = db.query(CourseModuleProgress).filter_by(phone=phone).all()
    return {r.module_id: r for r in rows}


def _module_states(db: DBSession, phone: str) -> list[dict]:
    catalog = course_content.list_modules()
    pmap = _progress_map(db, phone)
    states = []
    for meta in catalog:
        p = pmap.get(meta["id"])
        lessons_done = p.lessons_done if p else 0
        quiz_passed = bool(p and p.quiz_passed)
        if quiz_passed:
            state = "complete"
        elif lessons_done > 0 or (p and p.quiz_attempts > 0):
            state = "in-progress"
        else:
            state = "not-started"
        states.append({
            "id": meta["id"],
            "order": meta["order"],
            "title": meta["title"],
            "summary": meta["summary"],
            "lesson_count": meta["lesson_count"],
            "lessons_done": min(lessons_done, meta["lesson_count"]),
            "quiz_count": meta["quiz_count"],
            "quiz_passed": quiz_passed,
            "quiz_best": p.quiz_best if p else 0,
            "state": state,
        })
    return states


def _maybe_issue_certificate(db: DBSession, member: Member) -> None:
    """Issue the certificate once every module is quiz-passed (idempotent)."""
    if db.get(CourseCertificate, member.phone) is not None:
        return
    catalog = course_content.list_modules()
    pmap = _progress_map(db, member.phone)
    if not catalog:
        return
    if all(pmap.get(m["id"]) and pmap[m["id"]].quiz_passed
           for m in catalog):
        db.add(CourseCertificate(
            phone=member.phone,
            certificate_id=certificate_id_for(member.phone)))
        enrollment = db.get(CourseEnrollment, member.phone)
        if enrollment and enrollment.completed_at is None:
            enrollment.completed_at = dt.datetime.now(dt.timezone.utc)
        db.commit()


# --- member endpoints --------------------------------------------------------

@router.get("/course/status")
def course_status(member: Member = Depends(get_current_member),
                  db: DBSession = Depends(get_db)):
    """Enrollment + per-module progress + completion state for the panel."""
    enrollment = db.get(CourseEnrollment, member.phone)
    states = _module_states(db, member.phone)
    total = len(states)
    complete = sum(1 for s in states if s["state"] == "complete")
    cert = db.get(CourseCertificate, member.phone)
    return {
        "enrolled": enrollment is not None,
        "enrolled_at": (enrollment.enrolled_at.isoformat()
                        if enrollment else None),
        "modules": states,
        "modules_complete": complete,
        "modules_total": total,
        "progress_pct": round(100 * complete / total) if total else 0,
        "certified": cert is not None,
        "certificate_id": cert.certificate_id if cert else None,
    }


@router.get("/course/modules")
def course_modules(member: Member = Depends(get_current_member),
                   db: DBSession = Depends(get_db)):
    """Course manifest + module catalog (sanitized: no answer keys)."""
    manifest = course_content.load_manifest()
    return {
        "course": {
            "id": manifest["id"],
            "title": manifest["title"],
            "tagline": manifest["tagline"],
            "description": manifest["description"],
            "price_usd": manifest["price_usd"],
            "pass_score": manifest["pass_score"],
        },
        "modules": _module_states(db, member.phone),
    }


@router.get("/course/modules/{module_id}")
def course_module(module_id: str,
                  member: Member = Depends(get_current_member),
                  db: DBSession = Depends(get_db)):
    """Single module: lessons + quiz questions/options (no answer keys)."""
    try:
        return course_content.sanitized_module(module_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="unknown module")


class LessonsIn(BaseModel):
    module_id: str
    lessons_done: int = Field(ge=0, le=50)


@router.post("/course/lessons")
def course_lessons(body: LessonsIn,
                   member: Member = Depends(get_current_member),
                   db: DBSession = Depends(get_db)):
    """Record reading progress. Enrollment required."""
    if db.get(CourseEnrollment, member.phone) is None:
        raise HTTPException(status_code=403, detail="course not purchased")
    try:
        meta = next(m for m in course_content.list_modules()
                    if m["id"] == body.module_id)
    except StopIteration:
        raise HTTPException(status_code=404, detail="unknown module")
    done = min(body.lessons_done, meta["lesson_count"])
    row = db.query(CourseModuleProgress).filter_by(
        phone=member.phone, module_id=body.module_id).one_or_none()
    if row is None:
        row = CourseModuleProgress(phone=member.phone,
                                   module_id=body.module_id,
                                   lessons_done=0, quiz_passed=False,
                                   quiz_best=0, quiz_attempts=0)
        db.add(row)
    row.lessons_done = max(row.lessons_done or 0, done)
    db.commit()
    return {"ok": True, "module_id": body.module_id,
            "lessons_done": row.lessons_done,
            "lesson_count": meta["lesson_count"]}


class QuizIn(BaseModel):
    module_id: str
    answers: list[int] = Field(min_length=1, max_length=10)


@router.post("/course/quiz")
def course_quiz(body: QuizIn,
                member: Member = Depends(get_current_member),
                db: DBSession = Depends(get_db)):
    """Grade a quiz submission server-side. Pass = pass_score correct."""
    if db.get(CourseEnrollment, member.phone) is None:
        raise HTTPException(status_code=403, detail="course not purchased")
    try:
        key = course_content.answer_key(body.module_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="unknown module")
    if len(body.answers) != len(key):
        raise HTTPException(
            status_code=400,
            detail=f"expected {len(key)} answers, got {len(body.answers)}")
    if any(not isinstance(a, int) or a < 0 or a > 3 for a in body.answers):
        raise HTTPException(status_code=400,
                            detail="answers must be option indices 0-3")
    correct = [a == k for a, k in zip(body.answers, key)]
    score = sum(correct)
    # Pass threshold: manifest pass_score, but never more than the quiz
    # length (a 1-question quiz passes at 1/1, not 4/1).
    needed = min(course_content.pass_score(), len(key))
    passed = score >= needed

    db.add(CourseQuizAttempt(phone=member.phone, module_id=body.module_id,
                             score=score, total=len(key), passed=passed))
    row = db.query(CourseModuleProgress).filter_by(
        phone=member.phone, module_id=body.module_id).one_or_none()
    if row is None:
        row = CourseModuleProgress(phone=member.phone,
                                   module_id=body.module_id,
                                   lessons_done=0, quiz_passed=False,
                                   quiz_best=0, quiz_attempts=0)
        db.add(row)
    row.quiz_attempts = (row.quiz_attempts or 0) + 1
    row.quiz_best = max(row.quiz_best or 0, score)
    if passed:
        row.quiz_passed = True
    db.commit()

    _maybe_issue_certificate(db, member)

    return {
        "ok": True,
        "module_id": body.module_id,
        "score": score,
        "total": len(key),
        "passed": passed,
        "pass_score": course_content.pass_score(),
        "correct": correct,  # per-question right/wrong — not the answer key
        "module_complete": passed,
        "certified": db.get(CourseCertificate, member.phone) is not None,
    }


@router.get("/course/certificate")
def course_certificate(member: Member = Depends(get_current_member),
                       db: DBSession = Depends(get_db)):
    """Completion certificate. 404 until all modules are quiz-passed."""
    cert = db.get(CourseCertificate, member.phone)
    if cert is None:
        raise HTTPException(status_code=404,
                            detail="certificate not earned yet — "
                                   "complete all modules first")
    manifest = course_content.load_manifest()
    return {
        "certificate_id": cert.certificate_id,
        "certified_at": cert.certified_at.isoformat(),
        "course_title": manifest["title"],
        "name": member.display_name or member.phone,
    }


def _mask_phone(phone: str) -> str:
    p = str(phone)
    if len(p) <= 4:
        return "••••"
    return "••••" + p[-4:]


@router.get("/course/referrals")
def course_referrals(member: Member = Depends(get_current_member),
                      db: DBSession = Depends(get_db)):
    """Personal referral code + attribution stats (who signed up via it)."""
    code = _get_or_create_code(db, member.phone)
    events = (db.query(ReferralEvent)
              .filter_by(referrer_phone=member.phone)
              .order_by(ReferralEvent.created_at.desc()).all())
    return {
        "referral_code": code.code,
        "signups": len(events),
        "referred": [{
            "phone_masked": _mask_phone(e.referred_phone),
            "at": e.created_at.isoformat(),
        } for e in events],
        # Program terms, stated factually. Education framing only; pre-DASP
        # no token sale is live, so rewards accrue against future offerings.
        "program": {
            "reward": "5% of referred buyers' token purchases, forever",
            "note": ("Applies to future token offerings once they open. "
                     "No token sale is live right now."),
        },
    }


# --- brain-internal endpoints --------------------------------------------------

class EnrollIn(BaseModel):
    phone: str = Field(min_length=4, max_length=32)
    source: str = Field(default="stripe", max_length=64)


@router.post("/internal/course/enroll")
def internal_enroll(body: EnrollIn, _s=Depends(require_brain_secret),
                    db: DBSession = Depends(get_db)):
    """Brain-only: enroll a member after its Stripe webhook confirms the
    $100 course purchase (keyed by verified phone). Idempotent."""
    member = db.get(Member, body.phone)
    if member is None or member.status != "active":
        raise HTTPException(status_code=404,
                            detail="member not found or inactive")
    enrollment = db.get(CourseEnrollment, body.phone)
    if enrollment is None:
        enrollment = CourseEnrollment(phone=body.phone,
                                      source=body.source[:64])
        db.add(enrollment)
        db.commit()
    return {"ok": True, "phone": body.phone,
            "enrolled_at": enrollment.enrolled_at.isoformat()}


class ReferralIn(BaseModel):
    referrer_code: str = Field(min_length=4, max_length=32)
    referred_phone: str = Field(min_length=4, max_length=64)


@router.post("/internal/course/referral")
def internal_referral(body: ReferralIn, _s=Depends(require_brain_secret),
                      db: DBSession = Depends(get_db)):
    """Brain-only: attribute a signup to a referrer's code (called at the
    referred member's enrollment). Idempotent per referred phone."""
    code_row = db.get(ReferralCode, body.referrer_code.strip().upper())
    if code_row is None:
        # The referrer may never have opened the referrals tab; resolve the
        # deterministic code directly against members.
        code_row = None
        for m in db.query(Member).all():
            if referral_code_for(m.phone) == body.referrer_code.strip().upper():
                code_row = _get_or_create_code(db, m.phone)
                break
    if code_row is None:
        raise HTTPException(status_code=404, detail="unknown referral code")
    if code_row.phone == body.referred_phone:
        raise HTTPException(status_code=400, detail="self-referral not allowed")
    existing = (db.query(ReferralEvent)
                .filter_by(referred_phone=body.referred_phone).one_or_none())
    if existing is None:
        db.add(ReferralEvent(referrer_phone=code_row.phone,
                             referred_phone=body.referred_phone))
        db.commit()
    return {"ok": True, "referrer_phone": code_row.phone}
