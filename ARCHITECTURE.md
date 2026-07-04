<!-- /autoplan restore point: ~/.gstack/projects/app_gstack/main-autoplan-restore-20260703-235232.md -->
# Architecture — Federal-Style Activity Logger

Companion to `APP_SPEC.md`. This is the build plan: stack decisions, module layout,
schema, data flow, report engine, packaging. Spec wins on *what*; this document
decides *how*.

---

## 1. Decisions (with rationale)

| Decision | Choice | Why |
|---|---|---|
| GUI framework | **PySide6** (Qt 6) | Two of four core views are filterable grids. `QTableView` + `QSortFilterProxyModel` gives sorting and dept/UIN filtering nearly free; `QDateEdit` gives calendar pickers; validators are built in. Accepted cost: bigger exe (~100–150 MB). Decision logged 2026-07-03, user-confirmed. |
| DB access | **stdlib `sqlite3`, no ORM** | One local file, four tables, simple queries. An ORM adds a dependency and PyInstaller surface area for zero benefit at this scale. Plain SQL in repository classes keeps everything inspectable. |
| PDF engine | **ReportLab (Platypus)** | Per spec. Platypus flowables (Table, Paragraph, Spacer) map directly to the header/body/signature structure. Base-14 fonts only (Times-Roman/Helvetica) — no font embedding, no PyInstaller font issues, and Times matches the federal-document look. |
| Page size | **US Letter (8.5×11"), 1" margins** | "Federal-style" implies US government formatting; that is Letter, not A4. |
| Data location | **`%LOCALAPPDATA%\ActivityLogger\`** by default | A onefile exe unpacks to a temp dir and Program Files is write-protected, so "next to the exe" is unsafe as a default. Portable mode (below) covers the USB-stick case. |
| Quarter scheme | **Calendar quarters by default, federal fiscal (Oct–Sep) via config** | "Federal-style" cuts both ways: US federal FY Q1 = Oct–Dec. Which one your org means is a data question, not a code question — so it's a config switch, not a rewrite. |
| Departments & codes | **Data-driven (seeded tables), never hardcoded** | The spec's "[4th Dept Placeholder]" dissolves: adding a department or activity code is an INSERT, not a release. |
| Packaging | **PyInstaller onefile, windowed, built on Windows** | PyInstaller cannot cross-compile. Dev happens on macOS; the `.exe` is produced by a GitHub Actions `windows-latest` job (or any Windows box running `scripts/build_windows.ps1`). |
| Python | **3.12** | Current sweet spot for PySide6 + PyInstaller compatibility. Pin in `pyproject.toml` and CI. |

**Non-goals (v1):** no network/server, no authentication, no multi-user concurrency
beyond one machine, no admin UI for editing code catalogs (seed data + SQL for now).

---

## 2. Layering

Strict one-way dependencies. The UI is the only layer that imports Qt; `reports/`
is pure ReportLab; everything below `services/` is plain Python + sqlite3. This is
what makes the GUI swappable and the core testable without a display.

```
┌─────────────────────────────────────────────┐
│ ui/            PySide6: windows, views,     │
│                Qt table models, dialogs     │
└──────────────────────┬──────────────────────┘
                       │ calls
┌──────────────────────▼──────────────────────┐
│ services/      validation, logging,         │
│                aggregation, period math     │
│ reports/       federal_report (ReportLab)   │
└──────────────────────┬──────────────────────┘
                       │ calls
┌──────────────────────▼──────────────────────┐
│ repositories/  plain-SQL CRUD per table     │
└──────────────────────┬──────────────────────┘
                       │ uses
┌──────────────────────▼──────────────────────┐
│ db/            connection, PRAGMAs,         │
│                migrations, seed data        │
│ models/        frozen dataclasses           │
│ config.py      paths, settings, portable    │
└─────────────────────────────────────────────┘
```

Rule of thumb: `from PySide6 import ...` outside `ui/` is a review failure.
`import reportlab` outside `reports/` likewise.

---

## 3. Project layout

```
app_gstack/
├── APP_SPEC.md
├── ARCHITECTURE.md
├── pyproject.toml               # deps: PySide6, reportlab; dev: pytest, pytest-qt, pypdf, pyinstaller
├── src/activity_logger/
│   ├── __main__.py              # `python -m activity_logger`
│   ├── app.py                   # QApplication bootstrap, wiring, excepthook
│   ├── config.py                # data dir resolution, portable mode, config.json
│   ├── db/
│   │   ├── connection.py        # connect(): foreign_keys=ON, WAL, row_factory
│   │   ├── migrations.py        # PRAGMA user_version, ordered forward-only scripts
│   │   └── seed.py              # CP/MMC/ADV depts + activity code catalog
│   ├── models/entities.py       # Department, ActivityCode, Employee, LogEntry (frozen dataclasses)
│   ├── repositories/
│   │   ├── departments.py
│   │   ├── activity_codes.py
│   │   ├── employees.py
│   │   ├── log_entries.py
│   │   └── generated_reports.py
│   ├── services/
│   │   ├── validation.py        # UIN pattern, hours bounds, dept↔code consistency
│   │   ├── logging_service.py   # create/update/delete entry, upsert employee
│   │   ├── aggregation_service.py  # monthly rows, quarterly rollup
│   │   ├── periods.py           # month/quarter date-range math (calendar + fiscal)
│   │   ├── csv_io.py            # CSV export / UUID-keyed transactional import
│   │   └── report_service.py    # generate → archive copy → hash compare → log row
│   ├── reports/
│   │   ├── federal_report.py    # build_report(ReportData, out_path) — pure, no Qt
│   │   └── styles.py            # fonts, rules, signature-block geometry
│   └── ui/
│       ├── main_window.py       # QMainWindow + QTabWidget (3 tabs) + File menu
│       ├── views/
│       │   ├── entry_view.py    # data entry form
│       │   ├── monthly_view.py  # grid + month picker + filter bar
│       │   └── quarterly_view.py# aggregate grid + employee/quarter pickers + PDF button
│       ├── models_qt/
│       │   ├── log_table_model.py    # QAbstractTableModel over list[LogEntry]
│       │   └── aggregate_model.py
│       └── widgets/dept_code_picker.py  # dept combo → filtered code combo (reused)
├── tests/
│   ├── test_migrations.py
│   ├── test_repositories.py
│   ├── test_periods.py          # quarter boundaries, fiscal mode, leap day
│   ├── test_aggregation.py
│   ├── test_csv_io.py           # round-trip no-op, transactional abort, name mismatch
│   ├── test_report_archive.py   # hash stability, divergence warning both ways
│   └── test_report_golden.py    # deterministic PDF with injected clock
├── packaging/
│   ├── activity_logger.spec     # PyInstaller spec (onefile, windowed, Qt excludes)
│   └── app.ico
├── scripts/build_windows.ps1    # venv → pip install → pytest → pyinstaller
└── .github/workflows/build-windows.yml  # windows-latest → ActivityLogger.exe artifact
```

---

## 4. Database schema

SQLite, WAL mode, `foreign_keys=ON`, dates stored as ISO-8601 TEXT. Versioned via
`PRAGMA user_version` with forward-only numbered migrations in `db/migrations.py`.

```sql
CREATE TABLE departments (
    id      INTEGER PRIMARY KEY,
    code    TEXT NOT NULL UNIQUE,      -- 'CP', 'MMC', 'ADV', ...
    name    TEXT NOT NULL,
    active  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE activity_codes (
    id            INTEGER PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    code          TEXT NOT NULL UNIQUE,   -- 'CP-01', 'MMC-02', ...
    description   TEXT NOT NULL DEFAULT '',
    active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE employees (
    uin           TEXT PRIMARY KEY,       -- natural key per spec; TEXT keeps leading zeros
    name          TEXT NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(id)  -- home dept = form default
);

CREATE TABLE log_entries (
    id               INTEGER PRIMARY KEY,
    entry_uuid       TEXT NOT NULL UNIQUE,  -- uuid4 at insert; stable identity
                                            -- across installs (CSV merge key)
    employee_uin     TEXT NOT NULL REFERENCES employees(uin) ON UPDATE CASCADE,
    entry_date       TEXT NOT NULL,       -- 'YYYY-MM-DD'
    hours            REAL NOT NULL CHECK (hours > 0 AND hours <= 24),
    activity_code_id INTEGER NOT NULL REFERENCES activity_codes(id),
    description      TEXT NOT NULL DEFAULT '',
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT
);

-- Archive of every generated report: paper is the system of record, so a
-- signed page must always be reproducible and divergence must be detectable.
CREATE TABLE generated_reports (
    id            INTEGER PRIMARY KEY,
    employee_uin  TEXT NOT NULL REFERENCES employees(uin) ON UPDATE CASCADE,
    period_start  TEXT NOT NULL,          -- 'YYYY-MM-DD'
    period_end    TEXT NOT NULL,
    quarter_scheme TEXT NOT NULL,         -- 'calendar' | 'federal_fiscal'
    generated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    file_path     TEXT NOT NULL,          -- copy under <data dir>/reports/
    data_hash     TEXT NOT NULL           -- SHA-256 of canonical ReportData
);

CREATE INDEX idx_logs_date ON log_entries(entry_date);
CREATE INDEX idx_logs_uin  ON log_entries(employee_uin);
CREATE INDEX idx_logs_code ON log_entries(activity_code_id);
CREATE INDEX idx_reports_uin_period ON generated_reports(employee_uin, period_start, period_end);
```

**Deliberate choice — the entry's department is *derived*, not stored.** An activity
code belongs to exactly one department, so a log's department is
`activity_codes.department_id`, reachable by join. This stays historically accurate
when an employee transfers: old entries keep old codes, so old reports don't change.
`employees.department_id` is only the default selection in the entry form.

Seed data (`db/seed.py`): the three departments plus their code catalogs
(`CP-01…`, `MMC-01…`, `ADV-01…`) with placeholder descriptions — replace with the
real catalog when you have it. Adding the 4th department later = one INSERT plus its codes.

---

## 5. Data flows

**Save an entry** (Data Entry view):
```
form submit → ValidationService (UIN pattern, hours 0<h≤24, date sanity,
              code belongs to selected dept)
            → LoggingService.save(entry)
                ├─ EmployeeRepo.upsert(uin, name, dept)   # remembers people; QCompleter feeds off this
                └─ LogEntryRepo.insert(entry)
            → status-bar confirmation + form reset (dept/date sticky)
```

**Monthly Master view:**
```
month picker → AggregationService.monthly_rows(year, month)
             → SELECT joined rows (entry + employee + code + dept) for date range
             → LogTableModel (QAbstractTableModel)
             → QSortFilterProxyModel  ← dept combo + UIN/name search box
             → QTableView (click-to-sort, context menu: Edit / Delete with confirm)
```
Department filtering happens on the *derived* dept (via the activity code join).

**Quarterly Aggregate + PDF:**
```
(employee, year, quarter) → periods.quarter_range(scheme)   # calendar or federal fiscal
                          → AggregationService.quarterly(uin, range)
                              SELECT ac.code, ac.description, SUM(l.hours)
                              GROUP BY ac.code  (+ grand total)
                          → on-screen grid (all-employees mode available for browsing)
                          → [Generate PDF] → ReportData (frozen dataclass)
                          → reports.federal_report.build_report(data, path)   # QRunnable worker
                          → os.startfile(path)  # opens in default PDF viewer
```
The PDF requires a specific employee (the header and signature block are per-person);
the on-screen grid also offers an "All employees" browse mode.

---

## 6. Report engine (`reports/federal_report.py`)

Pure function: `build_report(data: ReportData, out_path: Path) -> None`. No Qt, no
database — everything arrives in `ReportData`. That makes golden-file testing trivial
(inject a fixed timestamp; assert extracted text).

Page layout (Letter, 1" margins, Times-Roman):

```
┌──────────────────────────────────────────────────────┐
│              {ORG NAME}   (config.json)              │
│         QUARTERLY ACTIVITY REPORT — {FY/Q}           │
│ ──────────────────────────────────────────────────── │
│ Name: ____________  UIN: ________  Dept: ___________ │
│ Reporting Period: {start} – {end}                    │
│ ──────────────────────────────────────────────────── │
│  ACTIVITY CODE │ DESCRIPTION            │ TOTAL HRS  │
│  CP-01         │ …                      │    42.50   │
│  CP-02         │ …                      │    13.25   │
│  ────────────────────────────────────── │ ────────── │
│  GRAND TOTAL                            │    55.75   │
│                                                      │
│ CERTIFICATION                                        │
│ I certify the above is a true record of activities.  │
│                                                      │
│ Employee:  ______________________   Date: __________ │
│            {Typed Name} ({UIN})                      │
│ Supervisor:______________________   Date: __________ │
│ Director:  ______________________   Date: __________ │
│                                                      │
│ Generated {timestamp}                    Page 1 of 1 │
└──────────────────────────────────────────────────────┘
```

Implementation notes: Platypus `Table` for the body with a `GRAND TOTAL` row;
signature block is a `Table` with bottom-ruled empty cells (never underscore
characters — rules stay aligned when names vary in length); employee line carries
the typed name + UIN under the rule per spec; footer via `onPage` canvas callback
(timestamp + page numbers). Multi-page bodies repeat the column header row.
User-entered text (descriptions, names) is XML-escaped before reaching any
Platypus `Paragraph` — ReportLab parses inline markup, so a raw `<` or `&` in a
description is a crash otherwise.

**Archive-on-generate** (`services/report_service.py`): every successful
generation copies the PDF to
`<data dir>/reports/{UIN}_{YYYY}Q{n}_{YYYYMMDD-HHMMSS}.pdf` (filesystem-safe
tokens — no colons; Windows is the target OS) and inserts a
`generated_reports` row. `data_hash` is SHA-256 over a stable serialization
of ReportData **excluding the generation timestamp** (employee fields, period
bounds, scheme, org name, ordered code/description/hours rows, grand total) —
regenerating unchanged data yields an identical hash and no warning.
Regenerating a period that already has an archived report compares hashes and
warns only on mismatch (data changed since the archived, possibly signed,
copy). Identical period + data reproduces identical report text, excluding
the generation timestamp footer (the golden test injects a fixed clock).

---

## 7. UI composition (PySide6)

`MainWindow` = `QTabWidget` with three tabs matching the spec's views, plus a File
menu (Export PDF…, Export entries to CSV…, Import entries from CSV…, Back up
database…, Quit).

**CSV round trip** (`services/csv_io.py`): export all entries or a date range,
columns `entry_uuid, uin, employee_name, department_code, activity_code,
entry_date, hours, description, created_at`. Import matches rows by
`entry_uuid` — existing UUID = skip (count reported), new UUID = insert
through the same validation as manual entry. Import is insert-only: edits to
existing entries do not propagate between machines in v1 (skip counts make
that visible). Imported rows keep the CSV's `created_at`. A newly created
employee's home department is the department of their most recent row in the
file (latest `entry_date`, ties broken by last occurrence). Unknown activity
codes/departments abort the import with a per-row error report before any
write (single transaction, no partial imports). Re-importing an exported file
is a no-op. Employees upsert by UIN; a UIN arriving with a different name is
reported, never silently renamed.

- **Data Entry:** `QLineEdit` name + UIN (with `QCompleter` fed from `employees`),
  dept `QComboBox` → repopulates activity-code `QComboBox` (the shared
  `dept_code_picker` widget), `QDateEdit` with calendar popup (defaults today),
  `QDoubleSpinBox` hours (0.25 step, 0–24), `QPlainTextEdit` description.
  Save button disabled until valid; a "today's entries" strip below the form for
  immediate feedback.
- **Monthly Master:** month stepper (◀ July 2026 ▶), filter bar (dept combo,
  UIN/name search), `QTableView` sorted by date desc. Edit opens the entry in a
  dialog reusing the entry form; Delete confirms first.
- **Quarterly Aggregate:** year + quarter pickers (labels follow the configured
  scheme, e.g. "FY26 Q3" in fiscal mode), employee selector (or All), aggregate
  grid, **Generate PDF** button → save dialog → worker thread → open file.

Threading: SQLite calls are local and fast — they stay on the UI thread. PDF
generation runs in a `QRunnable` on `QThreadPool` so the window never freezes.
One `sqlite3` connection owned by the main thread; the worker gets plain
`ReportData`, never a connection.

---

## 8. Config, paths, logging

`config.py` resolves the data directory once, at startup:

1. `ACTIVITY_LOGGER_HOME` env var, if set → use it (portable / testing).
2. `portable.flag` file next to the executable → use the exe's directory
   (USB-stick mode; detected via `sys.frozen` / `sys.executable`).
3. Otherwise → `%LOCALAPPDATA%\ActivityLogger\` (macOS dev fallback:
   `~/Library/Application Support/ActivityLogger/`).

**Startup writability check:** `connection.py` verifies the data directory is writable
before returning the connection. If `os.access(data_dir, os.W_OK)` fails (e.g. network
share, permissions problem), a `QMessageBox.critical()` shows the exact path and exits
cleanly. SQLite `OperationalError` messages are cryptic; catch this at the entry point.

Contents of the data dir: `activity_logger.db` (name per spec), `config.json`,
`logs/app.log` (rotating, 3×1 MB). `config.json` is created with defaults on first
run:

```json
{
  "org_name": "YOUR ORGANIZATION NAME",
  "quarter_scheme": "calendar",        // or "federal_fiscal" (FY starts Oct 1)
  "uin_pattern": "^[A-Za-z0-9-]{4,20}$",
  "theme": "system"                    // Qt Fusion style; light/dark/system
}
```

`app.py` installs a `sys.excepthook` that logs the traceback and shows a
"something went wrong" dialog with the log-file path — an internal tool that dies
silently never gets its bugs reported.

---

## 9. Packaging & CI

**Hard constraint: PyInstaller does not cross-compile.** You develop on macOS; the
`.exe` must be produced on Windows. Two supported paths, same spec file:

- `scripts/build_windows.ps1` — any Windows box: create venv, `pip install .`,
  run pytest, run `pyinstaller packaging/activity_logger.spec`.
- `.github/workflows/build-windows.yml` — `windows-latest`, Python 3.12, pytest,
  PyInstaller, uploads `ActivityLogger.exe` as an artifact on tag push or manual
  dispatch. This is the recommended path (requires pushing this folder to GitHub).

Spec-file essentials: `onefile`, `windowed` (no console), `icon=packaging/app.ico`,
name `ActivityLogger`. Exclude unused Qt heavyweights to keep size and startup
sane: `QtWebEngineCore`, `QtQml`, `Qt3D*`, `QtCharts`, `QtMultimedia`,
`QtNetwork` (nothing here touches the network). Expect ~100–150 MB and a few
seconds of first-launch unpack — normal for onefile Qt. If startup time ever
matters more than single-file distribution, switch to `onedir` + a zip; the spec
file keeps both one flag apart.

**Top deployment risk — unsigned exe on locked-down machines.** AppLocker/SRP
can block unsigned executables outside Program Files, and AV commonly
quarantines unsigned PyInstaller onefile binaries; "no admin rights" means the
user can't grant exceptions. Gate: as soon as CI produces artifacts (before any
UI milestone), run a minimal PySide6 hello-world exe on one real target
machine. Fallbacks in order: onedir build zipped (different AV profile), IT
whitelist request with the file hash, code-signing certificate.

---

## 10. Testing strategy

All core logic tests run headless (no display, no Windows box needed — they run on
your Mac and in CI):

- `test_migrations.py` — fresh DB reaches latest `user_version`; re-running is a no-op.
- `test_repositories.py` — CRUD against a temp-file DB; FK violations rejected;
  employee upsert semantics.
- `test_periods.py` — the bug farm: quarter boundaries (Dec 31 → Jan 1), federal
  fiscal mode (Oct 1 starts FY Q1), leap day, month ranges. **Boundary cases required:**
  entry on Q-last-day (e.g. Sep 30 calendar) must appear in Q3, not Q4; entry on
  Q-first-day of next quarter (Oct 1) must appear in Q4, not Q3. Both calendar and
  fiscal modes must pass these cases.
- `test_aggregation.py` — SUM-per-code math, grand total, empty quarter → empty
  report data (not a crash).
- `test_report_golden.py` — build a PDF with a fixed injected timestamp, extract
  text (pypdf), assert the header fields, every code row, grand total, and all
  three signature labels are present. **Mandatory case:** include a description
  containing XML-special characters (`<`, `>`, `&`) — e.g. `"Hours 3 < 4 & done"`.
  This tests that `xml.escape()` is applied before every Platypus `Paragraph()`;
  a missing escape crashes ReportLab silently at the director's desk.
- UI smoke (optional, `pytest-qt` with `QT_QPA_PLATFORM=offscreen`): tabs
  construct, dept combo filters the code combo, save button enables on valid input.

---

## 11. Build order

Each milestone is independently verifiable; the PDF engine lands *before* the UI
because the report is the product — the UI is data entry in service of it.

1. **Scaffold + data layer** — pyproject, config.py, db/ (connection, migrations,
   seed), models, repositories. Tests green.
2. **Services** — validation, periods, logging, aggregation, csv_io. Tests green.
3. **Report engine** — federal_report + styles + archive-on-generate + golden
   test. You can open a real PDF and judge the layout before any UI exists.
4. **UI** — main window, entry view, monthly view, quarterly view, wiring.
5. **Packaging** — spec file, build script, GitHub Actions, smoke-test the exe on
   a real Windows machine (launch, enter, aggregate, print).

**Deployment-risk gate (runs early, in parallel with 2-4):** once the GitHub
remote + Actions exist, build a hello-world PySide6 exe and run it on one real
target machine. If AppLocker/AV blocks it, switch fallbacks (see §9) before
investing in milestones 4-5 polish.

## 12. Assumptions & open items

- **Activity-code catalog is placeholder.** Real codes + descriptions slot into
  `db/seed.py` (or a later migration) whenever you have them.
- **UIN case: preserve exact case.** UIDs are stored as entered — no normalization.
  Consequence: `"A-04412"` and `"a-04412"` are different employees. Document this
  in the UI tooltip on the UIN field so data-entry clerks are consistent. CSV merge
  across machines will create duplicate records if case varies.
- **Validation errors display inline.** In the Data Entry form, validation failures
  (hours out of range, code/dept mismatch, UIN pattern fail) appear as a styled
  `QLabel` below the offending field — not a modal dialog, not status-bar-only.
  Status bar updates simultaneously but inline labels are the primary feedback.
- **Empty state for Monthly Master.** When no entries exist for the selected month,
  the table shows a centered message: "No entries for [Month YYYY]. Use the Data
  Entry tab to start logging."
- **Quarterly Report tab wireframe:** quarter picker (year `QSpinBox` + quarter
  `QComboBox`), employee selector (`QComboBox` with "All employees" option), aggregate
  `QTableView` (code, description, hours columns), **Generate PDF** button, and a
  `QLabel` warning zone that shows "Data has changed since report on {date} — verify
  the signed copy" when divergence is detected. Warning is orange, persistent until
  dismissed or a new quarter is selected.
- **Deployment model:** shared-machine or per-employee installs both work — the
  employees table and UIN filtering support either. No concurrent multi-machine
  writes to one DB file (SQLite on a network share is explicitly out).
- **Quarter scheme** defaults to calendar; flip `config.json` to `federal_fiscal`
  if your org reports on the federal fiscal year.
- **Adopted into v1 scope (office-hours session 2026-07-04):** CSV
  export/import with UUID-keyed merge (§7), `generated_reports` PDF archive
  with divergence warning (§4, §6), File → Back up database, edit/delete with
  confirmation. Admin UI for editing departments/codes is deliberately
  deferred; replacing placeholder codes is a seed-data edit + CI rebuild
  (consistent with the no-auto-update distribution model).
