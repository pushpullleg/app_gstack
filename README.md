# app_gstack — Federal-Style Activity Logger

`app_gstack` is a Windows desktop application for logging daily employee activities against department activity codes, then generating federal-style monthly and quarterly rollups with sign-off-ready PDF output.

It is designed for teams that need:

- structured daily activity capture,
- code-based categorization (`CP`, `MMC`, `ADV`),
- auditable month/quarter summaries, and
- formal report artifacts suitable for supervisor/approver workflows.

---

## Table of Contents

- [What this app does](#what-this-app-does)
- [Who it is for](#who-it-is-for)
- [Core workflow (application POV)](#core-workflow-application-pov)
- [Key features](#key-features)
- [Activity codes](#activity-codes)
- [Reporting model](#reporting-model)
- [Data model (high-level)](#data-model-high-level)
- [Tech stack](#tech-stack)
- [Architecture and layering rules](#architecture-and-layering-rules)
- [Project structure](#project-structure)
- [Installation and local development](#installation-and-local-development)
- [Running the app](#running-the-app)
- [Testing](#testing)
- [Building the Windows executable](#building-the-windows-executable)
- [Operational notes](#operational-notes)
- [Troubleshooting](#troubleshooting)
- [Security and data handling notes](#security-and-data-handling-notes)
- [Roadmap ideas](#roadmap-ideas)
- [Contributing](#contributing)
- [License](#license)

---

## What this app does

`app_gstack` helps employees and supervisors maintain a consistent, defensible record of work activity by day and by approved activity code.

At a high level, users:

1. Enter daily activity records.
2. Assign each entry to an approved code (`CP`, `MMC`, `ADV`).
3. Review monthly and quarterly totals.
4. Produce a federal-style PDF report for formal sign-off.

The app prioritizes clarity, reproducibility, and reporting discipline over “free-form” note-taking.

---

## Who it is for

- Individual contributors who need to log daily work in a coded format.
- Supervisors/managers who need periodic summaries and printable reports.
- Administrative operations teams maintaining audit-friendly activity records.

---

## Core workflow (application POV)

### 1) Daily logging
Users open the app and enter one or more activities for the day, including:
- date,
- activity description,
- activity code (`CP` / `MMC` / `ADV`),
- duration or effort fields (as defined in app forms/spec).

### 2) Validation and storage
The application validates required fields and stores records in a local SQLite database.

### 3) Rollup review
Users can navigate to period summaries:
- **Monthly** rollups for operational reporting.
- **Quarterly** rollups for higher-level administrative reporting.

### 4) Sign-off report generation
For a selected period, users generate a formatted PDF report (ReportLab) intended for federal-style review/sign-off flow.

---

## Key features

- ✅ Desktop-first UX (PySide6)
- ✅ Structured coding taxonomy (`CP`, `MMC`, `ADV`)
- ✅ Daily activity capture
- ✅ Monthly and quarterly aggregation
- ✅ Formal PDF report output (sign-off style)
- ✅ Lightweight local persistence via `sqlite3` (stdlib)
- ✅ Windows `.exe` packaging support (PyInstaller)
- ✅ Automated tests runnable headlessly on macOS/Linux CI

---

## Activity codes

The system categorizes entries into department-defined activity codes:

- **CP**
- **MMC**
- **ADV**

> Definitions and policy-level interpretation of each code should follow your organization’s official guidance.  
> The app enforces structured selection; governance of meaning remains with your department policy.

---

## Reporting model

The reporting pipeline is designed to support accountability and formal review:

- Input granularity: **daily**
- Aggregation periods:
  - **monthly**
  - **quarterly**
- Output artifact: **PDF report**
- Intended use: supervisor or approving official sign-off process

If your team uses a specific naming convention or signature block standard, align templates and report metadata accordingly.

---

## Data model (high-level)

At a conceptual level, the app tracks:

- activity entries (date, code, description, time/effort),
- period boundaries (month/quarter),
- rollup totals by code and period,
- report metadata needed to render formal PDF output.

For canonical fields and constraints, see:
- `APP_SPEC.md` (functional requirements)
- `ARCHITECTURE.md` (implementation and boundaries)

---

## Tech stack

- **Python**: 3.12+
- **UI**: PySide6
- **Database**: `sqlite3` (Python standard library, no ORM)
- **PDF reports**: ReportLab
- **Packaging**: PyInstaller
- **Testing**: `pytest`

---

## Architecture and layering rules

The codebase follows strict separation of concerns:

- `ui/` → presentation and Qt widgets
- `services/` → application/business logic
- `repositories/` → persistence-facing abstractions
- `db/` → SQLite schema, initialization, low-level DB concerns
- `reports/` → PDF rendering/report generation

### Important import boundaries

- **Qt imports are allowed only in `ui/`**
- **ReportLab imports are allowed only in `reports/`**

These boundaries keep business logic testable and reduce coupling between UI/report engines and core logic.

---

## Project structure

Typical layout:

```text
app_gstack/
├─ ui/               # PySide6 screens, dialogs, controllers
├─ services/         # Use-cases, validations, period rollups
├─ repositories/     # Data access layer (sqlite3-backed repos)
├─ db/               # Schema, migrations/bootstrap, DB utilities
├─ reports/          # ReportLab PDF builders
├─ scripts/
│  └─ build_windows.ps1
├─ tests/
├─ APP_SPEC.md
├─ ARCHITECTURE.md
└─ README.md
```

(Actual filenames may vary; use this as conceptual orientation.)

---

## Installation and local development

### Prerequisites

- Python 3.12+
- `pip`
- OS for development/testing:
  - Windows recommended for full app + packaging
  - macOS/Linux supported for test runs

### Create environment and install dependencies

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt
```

If your repo uses dev dependencies separately:

```bash
pip install -r requirements-dev.txt
```

---

## Running the app

Use your project’s entry point (example):

```bash
python -m app_gstack
```

or

```bash
python path/to/main.py
```

If a specific launcher script exists, prefer that documented command.

---

## Testing

Run tests with `pytest`:

```bash
pytest
```

For headless UI smoke tests on macOS/Linux CI:

```bash
QT_QPA_PLATFORM=offscreen pytest
```

This avoids display-server requirements for Qt-based tests.

---

## Building the Windows executable

> **Important:** Build the `.exe` **on Windows only**.

Supported paths:

- GitHub Actions with `windows-latest`
- Local Windows script: `scripts/build_windows.ps1`

### Why Windows-only?
PyInstaller bundles platform-specific binaries and bootloaders.  
A Windows executable must be built in a Windows environment.

### Example local build (PowerShell)

```powershell
.\scripts\build_windows.ps1
```

Do **not** attempt to produce the Windows `.exe` from macOS.

---

## Operational notes

- Use consistent activity descriptions for cleaner rollups.
- Keep code usage (`CP/MMC/ADV`) aligned to your internal policy.
- Generate and archive monthly reports before quarter close to reduce reconciliation overhead.
- Treat exported PDFs as formal records under your organization’s retention policy.

---

## Troubleshooting

### UI fails to launch
- Verify PySide6 is installed.
- Confirm Python version is 3.12+.
- Check for missing platform plugins in custom environments.

### PDF generation errors
- Verify ReportLab dependency is installed.
- Confirm output path is writable.
- Inspect report input data for missing required fields.

### Database issues
- Confirm app can create/write SQLite DB files.
- Check file permissions and lock conflicts.
- Reinitialize local DB if schema drift occurred in development.

### CI UI tests fail on headless runners
- Ensure `QT_QPA_PLATFORM=offscreen` is set for test execution.

### Windows packaging fails
- Build on Windows only.
- Validate PyInstaller version and spec/script settings.
- Ensure all runtime assets are included in packaging config.

---

## Security and data handling notes

- SQLite DB is local by default; ensure endpoint device protections align with policy.
- Limit file-system access to authorized users on shared machines.
- If activity logs contain sensitive details, apply your org’s encryption/retention controls outside app scope as needed.
- PDF reports may contain operationally sensitive information; distribute on least-privilege principles.

---

## Roadmap ideas

- Role-based approval states
- Digital signature integration
- CSV import/export for reconciliation
- Admin-configurable code sets beyond `CP/MMC/ADV`
- Audit trail enhancements (record-level change history)
- Centralized multi-user sync mode (optional future architecture)

---

## Contributing

1. Read `APP_SPEC.md` and `ARCHITECTURE.md` first.
2. Respect layering boundaries (`ui -> services -> repositories -> db`).
3. Keep Qt imports in `ui/` only.
4. Keep ReportLab imports in `reports/` only.
5. Add/maintain tests for behavior changes.
6. For packaging changes, verify Windows build path.

---

## License

Add your project’s license here (e.g., MIT, proprietary internal use, etc.).
