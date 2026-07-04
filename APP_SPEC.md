# Project Specification: Federal-Style Activity Logger Desktop App

## Overview
A standalone Windows desktop application for logging daily employee activities across our core departments. The app must track time, aggregate tasks quarterly/monthly, and generate a formalized, printable federal-style sign-off report.

## Tech Stack Target
- **Language:** Python 3
- **GUI Framework:** CustomTkinter (or PySide6) for a clean modern desktop interface
- **Database:** SQLite (local file-based storage, self-contained)
- **Reporting:** ReportLab (for generating printable PDFs)

## Department & Activity Code Configuration
The app must support the following specific departments in a dropdown menu, each mapping to its respective daily activities:
- **CP** (e.g., CP-01, CP-02)
- **MMC** (e.g., MMC-01, MMC-02)
- **ADV** (e.g., ADV-01, ADV-02)
- **[4th Dept Placeholder]** (If applicable, otherwise restrict to the three above)

## Data Schema & Fields
Every log entry must contain:
- **Employee Info:** Name, Department (Dropdown selection), UIN (Unique Identification Number).
- **Log Info:** Date, Time Logged (Hours), Activity Code (filtered by the selected department), Detailed Description.

## Core Features & Views
1. **Data Entry View:** Form to input daily logs with fields listed above.
2. **Monthly Master View:** A grid/table view showing all logs for the current month, filterable by department or UIN.
3. **Quarterly Aggregate View:** A historical view aggregating previous quarters' logs, calculating overall time computed per activity code.
4. **Print / Export Engine:** Generates a formalized PDF formatted in a "systematized federal layout".
   - **Header:** Employee details (Name, UIN, Dept).
   - **Body:** Aggregated breakdown of tasks computed, displaying overall hours per code.
   - **Footer (Signatures):** Must include structured, empty signature and date lines for:
     1. Employee (with typed name/number)
     2. Supervisor
     3. Director

## Development Goal
Build the application code locally. Ensure data persists locally in an `activity_logger.db` file. Provide a compilation script using `pyinstaller` so it can be packaged into a single `.exe` for Windows.