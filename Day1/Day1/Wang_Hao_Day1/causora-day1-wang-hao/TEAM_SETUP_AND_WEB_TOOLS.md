# Teammate Setup and Web Tools — Wang Day 1 v4.1

**You are receiving Wang's AI + Evidence module, not a complete three-person application.** No purchase, database, cloud deployment or real provider key is required for its local tests.

## Software: only what you need

| Task | Install / configure | Test performed in this handoff |
| --- | --- | --- |
| **Run Wang's ZIP locally** | Python **3.12** from [python.org](https://www.python.org/downloads/); create `.venv` and `pip install -r requirements.txt`. A terminal and PDF viewer suffice. Text files are read/written with explicit UTF-8: no global Windows locale change. | Python 3.12.3 and **50 pytest tests** passed with both UTF-8 and a simulated non-UTF-8 default. Actual Windows host not run here. |
| **Inspect/edit and share source** | Optional [Git](https://git-scm.com/downloads) and [VS Code](https://code.visualstudio.com/download). Do not assume this ZIP is the team's Git repository. | Git available; no repo modified. |
| **Run Xiangfeng v4.1 frontend validator / website** | Separately obtain the *original* v4.1 ZIP, install [Node.js](https://nodejs.org/en/download) compatible with its lockfile (tested **22.13.0**), then `npm ci` from its `causora/` directory. Run `node scripts/verify_v41.mjs /absolute/path/to/causora` from Wang's directory. | Typecheck, lint, 21 frontend tests, baseline build, adapted build and browser inspection passed in isolated extracted copies. |
| **Optional provider connectivity** | Server-side environment variables `OPENAI_API_BASE`, `OPENAI_API_KEY`; see **placeholder-only** `.env.example`. Only use a team-authorised OpenAI-compatible proxy that exposes both model IDs. | Four minimal plain/strict checks passed on the *current sandbox proxy only*. |

**Browser-first option:** You can view the **temporary** adapted static preview without installing development tools at `https://3001-iq2lfqky233l15mh2vzql-f764a424.sg2.manus.computer/` while this sandbox service remains active. This is not a permanent judging URL or a backend. Browser-based Python environments such as [Google Colab](https://colab.research.google.com/) can run a synthetic ZIP after manual upload, but **this v4.1 ZIP has not been independently executed in Colab**; the recorded results are from a clean Python/Node sandbox. Do not upload private contracts or secrets to a public notebook.

## Relevant websites (not all mandatory)

| Site | Use | Needed now? |
| --- | --- | --- |
| [GitHub](https://github.com/) | Team branch/PR and versioned integration | When the integration lead provides the team's repo. |
| [Google Colab](https://colab.research.google.com/) | Optional browser-only Python trial of **synthetic** fixtures | Optional, not part of this report's PASS results. |
| [ForgeHacks Devpost](https://forgehacks-2026.devpost.com/) | Team roster/rules and eventual entry | Check separately; do not treat this ZIP as submitted. |
| [OpenAI Platform](https://platform.openai.com/) / [Google AI Studio](https://aistudio.google.com/) | Direct-vendor keys **only if** team switches from its approved proxy | Not needed for this Day 1 package; no vendor-key verification claimed. |
| [Vercel](https://vercel.com/) / [Render](https://render.com/) | Future frontend/backend deployment | Not used for current module acceptance. |
| [Supabase](https://supabase.com/) | Optional persistent storage if the actual app requires it | Not required on Day 1. |

On Windows PowerShell, after setting `$env:PYTHONPATH="src"`, run `python -X utf8=0 -m pytest -q tests` to check compatibility with the system's default text encoding. **Expected: 50 passed.** This tests the module's Day 1 mock handoff, not a real simulator or human approval; those are later work. Never commit or upload a real `.env`/API key. The Day 1 UI is static; no actual `/api/*` endpoints were tested. See [`SELF_TEST_GUIDE.md`](SELF_TEST_GUIDE.md) for commands and acceptance boundaries.
