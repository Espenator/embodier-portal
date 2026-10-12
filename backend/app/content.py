"""Course content loader.

Reads course JSON (course/content/*.json, one file per module + an optional
course.json manifest) from the repository. Two module schemas are accepted
and normalized to one canonical shape, because course content is authored
in parallel:

  canonical (nested):  {"id", "order", "title": {"en","es"},
                        "summary": {"en","es"},
                        "lessons": [{"id","title":{"en","es"},
                                     "body":{"en":[...],"es":[...]}}],
                        "quiz": [{"id","question":{"en","es"},
                                  "options":{"en":[4],"es":[4]},"answer":int}]}
  flat:                {"module_id", "title_en","title_es",
                        "lessons_en":[{"heading","body"}],
                        "lessons_es":[{"heading","body"}],
                        "quiz":[{"q_en","q_es","choices":[{"en","es"} x4],
                                 "correct_index"}]}

The backend serves a SANITIZED view to clients: lesson text and quiz
questions/options, but NEVER the answer keys — grading happens server-side
in routers/course.py.

In the Docker image the course/ directory is copied alongside app/
(see backend/Dockerfile). Tests point CONTENT_DIR at fixture content.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

# backend/app/content.py -> parents: app, backend, repo root
DEFAULT_CONTENT_DIR = Path(__file__).resolve().parents[2] / "course" / "content"

CONTENT_DIR = DEFAULT_CONTENT_DIR


def set_content_dir(path: str | Path) -> None:
    """Override the content directory (tests). Clears cached loads."""
    global CONTENT_DIR
    CONTENT_DIR = Path(path)
    load_manifest.cache_clear()
    load_module.cache_clear()
    list_modules.cache_clear()
    _file_index.cache_clear()


def _order_of(module_id: str) -> int:
    m = re.search(r"(\d+)\s*$", str(module_id))
    return int(m.group(1)) if m else 0


@lru_cache(maxsize=1)
def _file_index() -> dict[str, Path]:
    """Map module id (and filename stem) -> file, for module-*.json."""
    index: dict[str, Path] = {}
    if not CONTENT_DIR.is_dir():
        return index
    for path in sorted(CONTENT_DIR.glob("module-*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        mid = raw.get("id") or raw.get("module_id") or path.stem
        index[str(mid)] = path
        index[path.stem] = path
    return index


def _normalize_flat(raw: dict, fallback_id: str) -> dict:
    """Convert the flat authoring schema to the canonical nested shape."""
    mid = str(raw.get("module_id") or raw.get("id") or fallback_id)
    lessons_en = raw.get("lessons_en") or []
    lessons_es = raw.get("lessons_es") or []
    lessons = []
    for i, (le, ls) in enumerate(zip(lessons_en, lessons_es)):
        lid = f"{mid}-l{i + 1:02d}"
        lessons.append({
            "id": lid,
            "title": {"en": le.get("heading", ""), "es": ls.get("heading", "")},
            "body": {"en": [le.get("body", "")], "es": [ls.get("body", "")]},
        })
    quiz = []
    for i, q in enumerate(raw.get("quiz") or []):
        choices = q.get("choices") or []
        quiz.append({
            "id": f"{mid}-q{i + 1}",
            "question": {"en": q.get("q_en", ""), "es": q.get("q_es", "")},
            "options": {
                "en": [c.get("en", "") for c in choices],
                "es": [c.get("es", "") for c in choices],
            },
            "answer": int(q.get("correct_index", 0)),
        })
    return {
        "id": mid,
        "order": raw.get("order") or _order_of(mid),
        "title": {"en": raw.get("title_en", ""), "es": raw.get("title_es", "")},
        "summary": {"en": raw.get("summary_en", ""), "es": raw.get("summary_es", "")},
        "lessons": lessons,
        "quiz": quiz,
    }


def _normalize(raw: dict, fallback_id: str) -> dict:
    if isinstance(raw.get("title"), dict):
        out = dict(raw)
        out["id"] = str(raw.get("id") or fallback_id)
        out["order"] = raw.get("order") or _order_of(out["id"])
        return out
    return _normalize_flat(raw, fallback_id)


@lru_cache(maxsize=1)
def load_manifest() -> dict:
    path = CONTENT_DIR / "course.json"
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    # No manifest: synthesize one from the module files found.
    ids: list[str] = []
    paths = sorted(set(_file_index().values()), key=lambda p: p.name)
    for fpath in paths:
        try:
            raw = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception:
            continue
        mid = str(raw.get("id") or raw.get("module_id") or fpath.stem)
        if mid not in ids:
            ids.append(mid)
    ids.sort(key=_order_of)
    first = load_module(ids[0]) if ids else None
    title = (first["title"] if first else {"en": "Course", "es": "Curso"})
    return {
        "id": "investment-real-estate-course",
        "title": title,
        "tagline": {"en": "", "es": ""},
        "description": {"en": "", "es": ""},
        "price_usd": 100,
        "pass_score": 4,
        "modules": ids,
    }


@lru_cache(maxsize=1)
def list_modules() -> list[dict]:
    """Module metadata in order (no lesson bodies, no answer keys)."""
    manifest = load_manifest()
    out = []
    for module_id in manifest["modules"]:
        full = load_module(module_id)
        out.append({
            "id": full["id"],
            "order": full["order"],
            "title": full["title"],
            "summary": full["summary"],
            "lesson_count": len(full["lessons"]),
            "lesson_titles": [l["title"] for l in full["lessons"]],
            "quiz_count": len(full["quiz"]),
        })
    return out


@lru_cache(maxsize=32)
def load_module(module_id: str) -> dict:
    """Full module including answer keys. Server-side only — never returned
    to clients verbatim (see sanitized_module)."""
    path = _file_index().get(str(module_id))
    if path is None or not path.is_file():
        raise KeyError(f"unknown module: {module_id}")
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return _normalize(raw, path.stem)


def sanitized_module(module_id: str) -> dict:
    """Client-safe module: lessons + quiz questions/options, no answers."""
    full = load_module(module_id)
    return {
        "id": full["id"],
        "order": full["order"],
        "title": full["title"],
        "summary": full["summary"],
        "lessons": [
            {"id": l["id"], "title": l["title"], "body": l["body"]}
            for l in full["lessons"]
        ],
        "quiz": [
            {"id": q["id"], "question": q["question"],
             "options": q["options"]}
            for q in full["quiz"]
        ],
    }


def answer_key(module_id: str) -> list[int]:
    return [q["answer"] for q in load_module(module_id)["quiz"]]


def pass_score() -> int:
    return int(load_manifest().get("pass_score", 4))
