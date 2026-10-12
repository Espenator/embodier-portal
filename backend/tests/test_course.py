"""Tests for the $100 Investment Real Estate Course API.

Covers: enrollment (brain-internal), status/progress, lesson tracking, quiz
grading (server-side, pass/fail/validation), certificate gating, referral
code + attribution, sanitized content (no answer keys leak), and the
compliance scan over all bundled course content (no yield promises, no live
token-sale claims).
"""
from __future__ import annotations

import json
import re

import pytest

from app import content as course_content
from app.models import (CourseCertificate, CourseEnrollment,
                        CourseModuleProgress, ReferralEvent)
from app.routers.course import certificate_id_for, referral_code_for
from tests.conftest import TEST_SECRET, bearer, seed_member

BRAIN = {"X-Brain-Secret": TEST_SECRET}


def enroll(client, phone="+15550001111", source="stripe"):
    return client.post("/api/internal/course/enroll",
                       json={"phone": phone, "source": source}, headers=BRAIN)


def module_ids():
    return [m["id"] for m in course_content.list_modules()]


def correct_answers(module_id):
    return course_content.answer_key(module_id)


def wrong_answers(module_id):
    return [(a + 1) % 4 for a in correct_answers(module_id)]


# --- enrollment ------------------------------------------------------------

def test_internal_enroll_requires_brain_secret(client, member):
    r = client.post("/api/internal/course/enroll",
                    json={"phone": member.phone})
    assert r.status_code == 403


def test_internal_enroll_unknown_member(client):
    r = client.post("/api/internal/course/enroll",
                    json={"phone": "+19999999999"}, headers=BRAIN)
    assert r.status_code == 404


def test_internal_enroll_ok_and_idempotent(client, member, db):
    r = enroll(client, member.phone)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert db.get(CourseEnrollment, member.phone) is not None
    r2 = enroll(client, member.phone)
    assert r2.status_code == 200
    assert db.query(CourseEnrollment).filter_by(
        phone=member.phone).count() == 1


# --- status ----------------------------------------------------------------

def test_status_requires_auth(client):
    assert client.get("/api/course/status").status_code == 401


def test_status_not_enrolled(client, member):
    r = client.get("/api/course/status", headers=bearer(member.phone))
    assert r.status_code == 200
    body = r.json()
    assert body["enrolled"] is False
    assert body["modules_total"] == 6
    assert body["modules_complete"] == 0
    assert body["progress_pct"] == 0
    assert body["certified"] is False
    assert all(m["state"] == "not-started" for m in body["modules"])


def test_status_enrolled(client, member):
    enroll(client, member.phone)
    r = client.get("/api/course/status", headers=bearer(member.phone))
    body = r.json()
    assert body["enrolled"] is True
    assert body["enrolled_at"]
    assert [m["id"] for m in body["modules"]] == module_ids()


# --- lessons -----------------------------------------------------------------

def test_lessons_requires_enrollment(client, member):
    r = client.post("/api/course/lessons",
                    json={"module_id": module_ids()[0], "lessons_done": 2},
                    headers=bearer(member.phone))
    assert r.status_code == 403


def test_lessons_unknown_module(client, member):
    enroll(client, member.phone)
    r = client.post("/api/course/lessons",
                    json={"module_id": "nope", "lessons_done": 1},
                    headers=bearer(member.phone))
    assert r.status_code == 404


def test_lessons_records_progress(client, member, db):
    enroll(client, member.phone)
    mid = module_ids()[0]
    r = client.post("/api/course/lessons",
                    json={"module_id": mid, "lessons_done": 2},
                    headers=bearer(member.phone))
    assert r.status_code == 200
    assert r.json()["lessons_done"] == 2
    # monotonic: a lower re-report never rewinds
    r = client.post("/api/course/lessons",
                    json={"module_id": mid, "lessons_done": 1},
                    headers=bearer(member.phone))
    assert r.json()["lessons_done"] == 2
    status = client.get("/api/course/status",
                        headers=bearer(member.phone)).json()
    m = next(x for x in status["modules"] if x["id"] == mid)
    assert m["state"] == "in-progress"


# --- quiz --------------------------------------------------------------------

def test_quiz_requires_enrollment(client, member):
    r = client.post("/api/course/quiz",
                    json={"module_id": module_ids()[0],
                          "answers": correct_answers(module_ids()[0])},
                    headers=bearer(member.phone))
    assert r.status_code == 403


def test_quiz_validates_answer_count(client, member):
    enroll(client, member.phone)
    mid = module_ids()[0]
    r = client.post("/api/course/quiz",
                    json={"module_id": mid, "answers": [0, 1]},
                    headers=bearer(member.phone))
    assert r.status_code == 400


def test_quiz_validates_indices(client, member):
    enroll(client, member.phone)
    mid = module_ids()[0]
    r = client.post("/api/course/quiz",
                    json={"module_id": mid, "answers": [0, 1, 2, 3, 9]},
                    headers=bearer(member.phone))
    assert r.status_code == 400


def test_quiz_unknown_module(client, member):
    enroll(client, member.phone)
    r = client.post("/api/course/quiz",
                    json={"module_id": "nope", "answers": [0, 0, 0, 0, 0]},
                    headers=bearer(member.phone))
    assert r.status_code == 404


def test_quiz_fail_does_not_complete(client, member, db):
    enroll(client, member.phone)
    mid = module_ids()[0]
    r = client.post("/api/course/quiz",
                    json={"module_id": mid, "answers": wrong_answers(mid)},
                    headers=bearer(member.phone))
    body = r.json()
    assert r.status_code == 200
    assert body["passed"] is False
    assert body["score"] < body["pass_score"]
    assert body["module_complete"] is False
    assert body["correct"] == [False] * 5
    # answer key is NOT revealed
    assert "answer" not in str(body).lower().replace('"correct"', '')
    row = db.query(CourseModuleProgress).filter_by(
        phone=member.phone, module_id=mid).one()
    assert row.quiz_passed is False
    assert row.quiz_attempts == 1


def test_quiz_pass_completes_module(client, member, db):
    enroll(client, member.phone)
    mid = module_ids()[0]
    r = client.post("/api/course/quiz",
                    json={"module_id": mid, "answers": correct_answers(mid)},
                    headers=bearer(member.phone))
    body = r.json()
    assert body["passed"] is True
    assert body["score"] == 5
    assert body["module_complete"] is True
    status = client.get("/api/course/status",
                        headers=bearer(member.phone)).json()
    assert status["modules_complete"] == 1
    assert status["progress_pct"] == round(100 / 6)
    m = next(x for x in status["modules"] if x["id"] == mid)
    assert m["state"] == "complete"


def test_quiz_best_score_kept(client, member, db):
    enroll(client, member.phone)
    mid = module_ids()[0]
    client.post("/api/course/quiz",
                json={"module_id": mid, "answers": wrong_answers(mid)},
                headers=bearer(member.phone))
    # 4/5 passes (pass_score) and records the best
    answers = correct_answers(mid)
    answers[0] = (answers[0] + 1) % 4
    r = client.post("/api/course/quiz",
                    json={"module_id": mid, "answers": answers},
                    headers=bearer(member.phone))
    assert r.json()["passed"] is True
    assert r.json()["score"] == 4
    row = db.query(CourseModuleProgress).filter_by(
        phone=member.phone, module_id=mid).one()
    assert row.quiz_best == 4
    assert row.quiz_attempts == 2


# --- certificate ---------------------------------------------------------------

def test_certificate_404_before_completion(client, member):
    enroll(client, member.phone)
    mid = module_ids()[0]
    client.post("/api/course/quiz",
                json={"module_id": mid, "answers": correct_answers(mid)},
                headers=bearer(member.phone))
    r = client.get("/api/course/certificate", headers=bearer(member.phone))
    assert r.status_code == 404


def test_certificate_issued_after_all_modules(client, member, db):
    enroll(client, member.phone)
    for mid in module_ids():
        r = client.post("/api/course/quiz",
                        json={"module_id": mid,
                              "answers": correct_answers(mid)},
                        headers=bearer(member.phone))
        assert r.json()["passed"] is True
    status = client.get("/api/course/status",
                        headers=bearer(member.phone)).json()
    assert status["certified"] is True
    assert status["progress_pct"] == 100
    assert status["certificate_id"] == certificate_id_for(member.phone)

    r = client.get("/api/course/certificate", headers=bearer(member.phone))
    assert r.status_code == 200
    body = r.json()
    assert body["certificate_id"] == certificate_id_for(member.phone)
    assert body["certified_at"]
    assert body["course_title"]
    # idempotent: exactly one certificate row
    assert db.query(CourseCertificate).filter_by(
        phone=member.phone).count() == 1
    enrollment = db.get(CourseEnrollment, member.phone)
    assert enrollment.completed_at is not None


# --- sanitized content -----------------------------------------------------------

def test_module_payload_has_no_answer_keys(client, member):
    enroll(client, member.phone)
    for mid in module_ids():
        r = client.get(f"/api/course/modules/{mid}",
                       headers=bearer(member.phone))
        assert r.status_code == 200
        payload = r.json()
        assert len(payload["lessons"]) >= 3
        assert len(payload["quiz"]) == 5
        for q in payload["quiz"]:
            assert "answer" not in q
            assert len(q["options"]["en"]) == 4
            assert len(q["options"]["es"]) == 4
    r = client.get("/api/course/modules/unknown",
                   headers=bearer(member.phone))
    assert r.status_code == 404


# --- referrals ---------------------------------------------------------------------

def test_referral_code_stable_and_formatted(client, member):
    enroll(client, member.phone)
    r1 = client.get("/api/course/referrals", headers=bearer(member.phone))
    r2 = client.get("/api/course/referrals", headers=bearer(member.phone))
    assert r1.status_code == 200
    code = r1.json()["referral_code"]
    assert code == r2.json()["referral_code"]
    assert code == referral_code_for(member.phone)
    assert re.fullmatch(r"EMB-[A-Z2-7]{6}(-[0-9]+)?", code)
    assert r1.json()["signups"] == 0
    assert r1.json()["referred"] == []
    assert "5%" in r1.json()["program"]["reward"]


def test_referral_requires_auth(client):
    assert client.get("/api/course/referrals").status_code == 401


def test_internal_referral_attribution(client, member, db):
    friend = seed_member(db, phone="+15550003333", name="Friend")
    code = client.get("/api/course/referrals",
                      headers=bearer(member.phone)).json()["referral_code"]
    # secret required
    r = client.post("/api/internal/course/referral",
                    json={"referrer_code": code,
                          "referred_phone": friend.phone})
    assert r.status_code == 403
    # unknown code
    r = client.post("/api/internal/course/referral",
                    json={"referrer_code": "EMB-XXXXXX",
                          "referred_phone": friend.phone}, headers=BRAIN)
    assert r.status_code == 404
    # self-referral rejected
    r = client.post("/api/internal/course/referral",
                    json={"referrer_code": code,
                          "referred_phone": member.phone}, headers=BRAIN)
    assert r.status_code == 400
    # attribution recorded
    r = client.post("/api/internal/course/referral",
                    json={"referrer_code": code,
                          "referred_phone": friend.phone}, headers=BRAIN)
    assert r.status_code == 200
    # idempotent per referred phone
    r = client.post("/api/internal/course/referral",
                    json={"referrer_code": code,
                          "referred_phone": friend.phone}, headers=BRAIN)
    assert r.status_code == 200
    assert db.query(ReferralEvent).filter_by(
        referred_phone=friend.phone).count() == 1
    stats = client.get("/api/course/referrals",
                       headers=bearer(member.phone)).json()
    assert stats["signups"] == 1
    assert stats["referred"][0]["phone_masked"] == "••••3333"
    assert "at" in stats["referred"][0]


# --- content compliance --------------------------------------------------------------

# Non-negotiable: education framing only. No yield/return promises, no live
# token-sale claims. Negated mentions ("no token sale is live") are allowed.
BANNED_YIELD = [
    "guaranteed return", "guaranteed profit", "guaranteed income",
    "get rich", "risk-free", "can't lose", "double your money",
]
BANNED_LIVE_SALE = [
    r"(?<!no )(?<!not )token sale is live",
    r"(?<!no )(?<!not )buy tokens now",
    r"(?<!no )(?<!not )offering is open",
    r"(?<!no )(?<!not )tokens are on sale",
    r"(?<!no )(?<!not )venta de tokens está abierta",
    r"(?<!no )(?<!not )compra tokens ahora",
]


def _all_copy():
    texts = []
    manifest = course_content.load_manifest()
    for key in ("tagline", "description", "compliance_note"):
        for lang in ("en", "es"):
            texts.append((f"course.json:{key}:{lang}",
                          manifest[key][lang]))
    for mid in module_ids():
        full = course_content.load_module(mid)
        for l in full["lessons"]:
            for lang in ("en", "es"):
                texts.append((f"{mid}:{l['id']}:{lang}",
                              l["title"][lang] + " " + " ".join(l["body"][lang])))
        for q in full["quiz"]:
            for lang in ("en", "es"):
                texts.append((f"{mid}:{q['id']}:{lang}",
                              q["question"][lang] + " " +
                              " ".join(q["options"][lang])))
    return texts


def test_content_has_no_yield_promises():
    violations = [(loc, p) for loc, text in _all_copy()
                  for p in BANNED_YIELD if p in text.lower()]
    assert violations == [], f"yield-promise copy found: {violations}"


def test_content_has_no_live_token_sale_claims():
    violations = []
    for loc, text in _all_copy():
        for pat in BANNED_LIVE_SALE:
            if re.search(pat, text, re.IGNORECASE):
                violations.append((loc, pat))
    assert violations == [], f"live-sale claim found: {violations}"


def test_content_schema_complete():
    manifest = course_content.load_manifest()
    assert manifest["price_usd"] == 100
    assert len(manifest["modules"]) == 6
    for mid in manifest["modules"]:
        full = course_content.load_module(mid)
        assert len(full["lessons"]) >= 3
        assert len(full["quiz"]) == 5
        for q in full["quiz"]:
            assert 0 <= q["answer"] <= 3
            assert len(q["options"]["en"]) == 4
            assert len(q["options"]["es"]) == 4
    with pytest.raises(KeyError):
        course_content.load_module("no-such-module")


# --- flat authoring schema (parallel content set) ---------------------------------

FLAT_MODULE = {
    "module_id": "M9",
    "title_en": "Flat Schema Test",
    "title_es": "Prueba de esquema plano",
    "lessons_en": [{"heading": "Lesson one", "body": "Body one."}],
    "lessons_es": [{"heading": "Lección uno", "body": "Cuerpo uno."}],
    "quiz": [{
        "q_en": "One plus one?",
        "q_es": "¿Uno más uno?",
        "choices": [
            {"en": "One", "es": "Uno"},
            {"en": "Two", "es": "Dos"},
            {"en": "Three", "es": "Tres"},
            {"en": "Four", "es": "Cuatro"},
        ],
        "correct_index": 1,
    }],
}


@pytest.fixture()
def flat_content_dir(tmp_path):
    d = tmp_path / "content"
    d.mkdir()
    (d / "module-09-flat-test.json").write_text(
        json.dumps(FLAT_MODULE), encoding="utf-8")
    course_content.set_content_dir(d)
    yield d
    course_content.set_content_dir(course_content.DEFAULT_CONTENT_DIR)


def test_flat_schema_normalizes(flat_content_dir):
    manifest = course_content.load_manifest()
    # no course.json -> synthesized manifest
    assert manifest["modules"] == ["M9"]
    assert manifest["pass_score"] == 4
    mods = course_content.list_modules()
    assert len(mods) == 1
    assert mods[0]["id"] == "M9"
    assert mods[0]["title"]["en"] == "Flat Schema Test"
    assert mods[0]["lesson_count"] == 1
    assert mods[0]["quiz_count"] == 1

    full = course_content.load_module("M9")
    assert full["lessons"][0]["title"]["es"] == "Lección uno"
    assert full["lessons"][0]["body"]["en"] == ["Body one."]
    assert course_content.answer_key("M9") == [1]

    # sanitized view has no answer key
    san = course_content.sanitized_module("M9")
    assert "answer" not in san["quiz"][0]
    assert san["quiz"][0]["options"]["es"][1] == "Dos"

    # stem alias also resolves
    assert course_content.load_module("module-09-flat-test")["id"] == "M9"


def test_flat_schema_quiz_grades(client, member, db, flat_content_dir):
    r = client.post("/api/internal/course/enroll",
                    json={"phone": member.phone}, headers=BRAIN)
    assert r.status_code == 200
    # correct answer for the flat module
    r = client.post("/api/course/quiz",
                    json={"module_id": "M9", "answers": [1]},
                    headers=bearer(member.phone))
    assert r.status_code == 200
    assert r.json()["passed"] is True
    status = client.get("/api/course/status",
                        headers=bearer(member.phone)).json()
    assert status["modules_total"] == 1
    assert status["certified"] is True  # single-module course completes
    cert = client.get("/api/course/certificate",
                      headers=bearer(member.phone))
    assert cert.status_code == 200
