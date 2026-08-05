# ALT — Final QA Report (ALT-009)

## Summary

59 Python files across ALT-001 through ALT-008, integrated into a single
working Streamlit application. All modules compile cleanly and the
automated test suite passes.

## Test Results

```
47 passed, 0 failed
```

Coverage areas: registration/login/lockout/password reset, translation
orchestration (validation, auto-detect, NLLB→Marian fallback, history
persistence), history search/filter/favorites/export (all 5 formats
produce real non-empty files), admin user management, language registry
integrity (54 languages incl. mandatory Yoruba/Hausa/Igbo), security
utilities (hashing, validation, rate limiting), file validation.

Additionally verified manually against real dependencies (not just
mocks) during development:
- Real SQLite database read/write across every service
- Real OCR extraction via an installed Tesseract binary on a generated test image
- Real DOCX and PDF file generation (python-docx, reportlab)
- Real SQLite backup/restore via the SQLite backup API, including a
  before/after data-loss verification
- Real psutil system metrics

## What Could Not Be Tested In This Environment

- **NLLB-200 / MarianMT live inference** — this development environment has
  no network route to Hugging Face, so actual model weights could not be
  downloaded. `ai/model_manager.py`'s loading and generation code is written
  against the current `transformers` API but was exercised via dependency
  injection (mocked at the `ModelManager.generate_nllb`/`generate_marian`
  boundary) rather than with real weights. **Action for the developer:**
  run `streamlit run app.py` and perform a real translation on a machine
  with internet access before considering this feature fully verified.
- **Google Speech-to-Text / gTTS** — both call external Google APIs not
  reachable from this environment. The orchestration code is correct and
  was confirmed to fail *gracefully* (proper exception, friendly message)
  when the network call fails, but a real transcription/synthesis was
  never observed. **Action for the developer:** test with real audio
  on a machine with internet access.
- **GPU inference path** — `ModelManager.get_device()` correctly detects
  and would use CUDA if available, but this environment has no GPU, so only
  the CPU code path was exercised.

## Bugs Found and Fixed During Development

1. `register_user` returned a SQLAlchemy object detached from its session,
   which raised `DetachedInstanceError` on attribute access after the
   session closed. Fixed by returning a plain `SimpleNamespace` snapshot.
2. Failed-login/lockout counters were being rolled back by the same
   transaction that raised the resulting `AuthenticationError`, silently
   defeating the lockout policy. Fixed by restructuring `login_user` so
   bookkeeping commits before the error is raised.

Both were caught by writing functional tests against a real database
rather than only checking syntax — a reminder that syntax-clean code is
not the same as correct code.

## Known Non-Blocking Issues

- `datetime.utcnow()` deprecation warnings under Python 3.12+ (functionally
  correct; not migrated to timezone-aware datetimes to avoid late-stage
  regression risk — see `docs/ARCHITECTURE.md`).
- `PyPDF2` and `pydub` were in the original dependency list but never
  actually used in the final implementation (pdfplumber covers PDF
  extraction, reportlab covers PDF generation) — removed from
  `requirements.txt` to avoid unused packages.
- Rate limiting is in-process/single-instance only (documented, by design,
  for the target single-instance Streamlit deployment).

## No Placeholder Code

A repository-wide search for `TODO`, `FIXME`, `XXX`, `NotImplementedError`,
and stub patterns found no incomplete implementations — the two incidental
matches were Streamlit's own `placeholder=` UI parameter, not code stubs.

## Recommendation

This codebase is ready for a developer to clone, `pip install -r
requirements.txt`, and run locally with internet access to complete
first-run model downloads. It is not recommended to deploy to a
public-facing production environment without: setting a real
`ALT_SECRET_KEY`, deploying behind HTTPS, and running a real end-to-end
smoke test of translation/voice/OCR against live model weights first.
