# 🗓️ Slotify — Smart College Timetable Generator

> **Your Perfect Timetable, Without the Chaos.**  
> Create conflict-free college timetables in minutes. Manage faculty, subjects, classrooms, and academic schedules with one intelligent platform.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Framework](https://img.shields.io/badge/Framework-Flask-green.svg)](https://palletsprojects.com/p/flask/)
[![Database](https://img.shields.io/badge/Database-SQLite-lightgrey.svg)](https://sqlite.org)
[![Aesthetics](https://img.shields.io/badge/Design-Swiss%20Grid%20Minimalism-315C45.svg)](#design-aesthetics)
[![Tests](https://img.shields.io/badge/Tests-27%20Passed-brightgreen.svg)](#automated-testing)

---

## 🌟 Interactive Landing Page & Complete Workflow

Slotify provides an end-to-end departmental scheduling platform with Swiss Grid Minimalism and modern campus aesthetics:

1. **Interactive Landing Page (`/`)**:
   - Modern campus header with navigation: Home, Features, How It Works, Dashboard, and Generate Timetable.
   - Hero section featuring headline *"Your Perfect Timetable, Without the Chaos."*
   - Interactive live timetable preview block with pastel cohort cells.
   - 6 Feature cards: Smart Timetable Generation, Faculty Management, Conflict Detection, Classroom & Lab Allocation, Academic Calendar, and Multi-format Exports.
   - 3-step explanation of the scheduling workflow.
   - Prominent Call to Action: *"Create My Timetable"*.

2. **One-Click Demo Experience (`Try with Demo Data`)**:
   - One-click action on landing page or workflow header loads a realistic 16-faculty, 16-subject, 11-room dataset into the 7-step wizard.
   - Pre-populates all inputs without prematurely publishing a schedule.
   - Safe Demo Data Controls: *Load Demo Data* and *Clear Demo Data* (purges only records tagged `is_demo = 1`, preserving manually created user records).

3. **7-Step Timetable Generator Wizard**:
   - **Step 1: Academic Setup** — Institution name, department, academic session, semester, working days (Mon–Sat), daily hours, theory/practical session durations, and protected lunch breaks.
   - **Step 2: Classes & Divisions** — Manage SE, TE, BE student strengths and laboratory batch configurations with dynamic CRUD.
   - **Step 3: Subjects** — Course codes, theory/practical weekly hours, consecutive practical session requirements, and preferred room types.
   - **Step 4: Faculty** — Initials, names, departments, slot preferences (Morning Slot 1 vs Afternoon Slot 2), weekly workloads, and qualified subject mappings.
   - **Step 5: Classrooms & Labs** — Lecture halls, hardware labs, and software centers with capacities, projectors, and air conditioning.
   - **Step 6: Schedule Preferences** — Hard constraints (zero faculty/room collisions, protected recess) vs soft optimization preferences (even distribution, slot matching, gap minimization).
   - **Step 7: Review & Generate** — Complete departmental summary breakdown, pre-flight constraint validation, and one-click submission to the backend CSP solver.

4. **Generation Results & Explorer Page**:
   - Weekly grid with pastel color palettes.
   - **View by Class / Division** (SE, TE, BE).
   - **View by Faculty** (dropdown with instant individual workload and schedule views).
   - **View by Room / Lab** (dropdown with room utilization schedules).
   - **Day Filters** (All Days, Mon, Tue, Wed, Thu, Fri, Sat).
   - **Cell Lock Toggles** (click `🔒` / `🔓` to fix a session in place during subsequent regenerations).
   - **Slot Editor** (click any cell to adjust subject, teacher, or room with real-time collision validation).
   - **Multi-Format Exports** (PDF, Excel `.xlsx`, Word `.docx`, CSV, and Print).

---

## 🏗️ Architecture & Technology Stack

- **Backend:** Python 3 with Flask web framework.
- **Database:** SQLite with normalized relational schema:
  - `teachers`, `teacher_subjects`, `classrooms`, `subjects`, `academic_years`, `divisions`, `batches`, `time_slots`, `working_days`, `holidays`, `timetables`, `timetable_versions`, `notifications`, `settings`.
- **Constraint Satisfaction (CSP) Engine:**
  - Backtracking search with Minimum Remaining Values (MRV) & Least Constraining Value (LCV) heuristics.
  - Multi-dimensional collision detection across faculty, rooms, cohorts, and protected lunch intervals.
- **Document Exporter:**
  - PDF: ReportLab with custom institutional header, pastel table styling, and metadata.
  - Excel: `openpyxl` with styled headers and border formatting.
  - Word: `python-docx` with formatted tables and session notes.
  - CSV: Standard RFC 4180 streaming export.
- **Frontend:** Single-page reactive application with Swiss Grid Minimalism (`#FAF5EB` warm cream, `#315C45` deep forest green, `#292E27` charcoal, and soft pastel cohort blocks).

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.10+ (tested with Python 3.14)
- `pip`

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Application
```bash
cd src
python3 app.py
```
Open **[http://127.0.0.1:5050](http://127.0.0.1:5050)** in your browser.

---

## 🧪 Automated Testing

Slotify includes an automated pytest suite covering 27 test cases:

```bash
pytest src/test_slotify.py
```

### Test Coverage Highlights:
- Landing page and workflow HTML structure verification.
- Faculty, Room, Subject, and Division CRUD operations.
- Input validation (email format, duplicate initials, unique room numbers).
- Idempotent demo dataset preloading and non-destructive demo erasing.
- Automated CSP timetable generation with 0 hard conflicts.
- Conflict detection for manual overlaps and protected recess violations.
- Slot locking preservation during re-generation.
- Version history snapshotting and restoration.
- PDF, Excel, and CSV binary export generation.
- Impossible constraint diagnostic reporting.

---

## 🎨 Design Aesthetics (Swiss Grid Campus Palette)

| Token | Hex | Usage |
| :--- | :--- | :--- |
| **Warm Cream** | `#FAF5EB` | Background canvas / parchment |
| **Forest Green** | `#315C45` | Primary brand accent & headers |
| **Charcoal** | `#292E27` | High-contrast readable typography |
| **Sage Light** | `#DCEBDD` | Secondary cards, borders & pills |
| **Terracotta** | `#B56E40` | Practical lab blocks & warnings |
| **Recess Yellow**| `#FBF6E8` | Protected lunch & break intervals |
