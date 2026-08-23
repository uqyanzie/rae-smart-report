---
name: pyinstaller-packaging-guardian
description: Guards desktop executable packaging via PyInstaller, resolves writable database paths vs sys._MEIPASS, configures FastAPI static SPA mounting, manages automated browser launching, and handles hidden imports.
---

# PyInstaller Packaging Guardian

This skill defines path resolution safety rules, build configurations, static file mounting, and runtime lifecycle hooks for bundling the Python FastAPI + React application into a standalone Windows `.exe` desktop executable.

---

## 1. Core Directives & Boundaries

1. **Never Write to `sys._MEIPASS`:** When PyInstaller packages an application, bundled assets unpack into a temporary read-only directory referenced by `sys._MEIPASS`. Writing `app_data.db` here causes immediate runtime crashes.
2. **Writable Application Storage:** Store `app_data.db`, caches, and logs in persistent user storage (e.g. `%LOCALAPPDATA%/RAESmartReport` or next to the executable).
3. **Static SPA Asset Mounting:** FastAPI must mount the pre-built React `frontend/dist` directory with SPA catch-all routing fallback to `index.html`.
4. **Browser Auto-Launch Daemon:** Open default browser to `http://127.0.0.1:8000` via a non-blocking background thread on application boot.

---

## 2. Invariants & Decision Checklist

- [ ] Does `get_database_path()` resolve to `%LOCALAPPDATA%` or the executable directory, never `sys._MEIPASS`?
- [ ] Are FastAPI non-API routes forwarded to `index.html` for client-side routing?
- [ ] Is browser launching non-blocking (in a daemon thread after health check)?
- [ ] Are all dynamic uvicorn and sqlalchemy hidden imports included in `build.py`?

---

## 3. Modular Code References

- **Writable Path & Database Resolver:** [references/path_resolver.py](references/path_resolver.py)
- **FastAPI Static SPA Mounting:** [references/spa_mounting.py](references/spa_mounting.py)
- **Background Browser Launcher:** [references/browser_launcher.py](references/browser_launcher.py)
- **PyInstaller Build Template:** [references/build_template.py](references/build_template.py)
