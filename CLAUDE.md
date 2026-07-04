# app_gstack — Federal-Style Activity Logger

Windows desktop app: employees log daily activities against department activity
codes (CP/MMC/ADV); monthly/quarterly rollups; federal-style PDF sign-off report.

- Spec: `APP_SPEC.md` (what). Architecture: `ARCHITECTURE.md` (how).
- Stack: Python 3.12+, PySide6, stdlib sqlite3 (no ORM), ReportLab, PyInstaller.
- Layering: `ui/` → `services/` → `repositories/` → `db/`. Qt imports only in
  `ui/`; reportlab imports only in `reports/`.
- The `.exe` is built ON WINDOWS only (GitHub Actions `windows-latest` or
  `scripts/build_windows.ps1`). Never run PyInstaller for the exe on macOS.
- Tests run headless on macOS: `pytest` (UI smoke tests use
  `QT_QPA_PLATFORM=offscreen`).

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec
