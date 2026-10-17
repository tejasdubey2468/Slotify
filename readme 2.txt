Slotify — Smart College Timetable Management & Scheduling Platform
=================================================================

Slotify is a Flask-based academic timetable generator for colleges. It lets
administrators manage departments, academic years, divisions/batches, subjects,
classrooms/labs, faculty with workloads and availability, then automatically
generates conflict-free timetables for SE/TE/BE divisions, validates them,
tracks versions, and exports to PDF/Excel/Word/CSV.

CORE LOGIC
----------

1. Scheduling engine (src/scheduler.py)
   - Constraint Satisfaction Problem (CSP) solver: generate_schedules_csp()
     builds per-division grids (days x time slots) and fills them session by
     session while honoring hard constraints:
       * No faculty double-booking (teacher collision)
       * No room/lab double-booking (room collision)
       * No division double-booking
       * Recess slots are protected (no classes during lunch)
       * Teacher must be qualified for the subject (assignments check)
       * Faculty unavailable slots respected
       * Room type matching (theory -> classroom, practical -> laboratory)
       * Room capacity >= division/batch strength
       * Practical sessions occupy consecutive 2-slot blocks
       * Daily/weekly faculty workload caps enforced
       * Locked sessions preserved across re-generation
   - Soft optimizations: even subject distribution across the week
     (max 1 theory of same subject per day), faculty slot preference
     (morning/afternoon/flexible), minimized consecutive lectures
     (max 3), balanced daily workload.
   - Heuristics: MRV-style ordering (fewest valid options first for
     practicals), randomized day/slot order, slot-preference scoring for
     faculty (LCV-like preference), diagnostics for unassigned sessions.
   - Fallback legacy scheduler (generate_schedules) for the original
     teacher-list format; detects_conflicts() runs a full multi-dimensional
     audit reporting hard errors (teacher overlap, room overlap, division
     overlap, recess violation) and soft warnings (daily/weekly workload,
     consecutive lectures).

2. Database layer (src/database.py)
   - SQLite (slotify.db) with schema: departments, academic_years, divisions,
     batches, subjects, classrooms, teachers, teacher_subjects,
     time_slots, working_days, holidays, timetables, timetable_versions,
     notifications, settings.
   - Demo/user separation via is_demo flag: one-click load/erase/reset of
     sample data without touching user records.
   - Timetable versioning: every generation/save/restore creates a versioned
     snapshot with change summary; publish workflow blocks publication while
     unresolved hard conflicts remain.

3. API controller (src/app.py)
   - Flask REST API + SPA frontend (src/templates/index.html).
   - Endpoints for CRUD of departments, years, divisions, subjects, classrooms,
     teachers, time slots, working days, holidays.
   - Timetable endpoints: generate, current, validate, update_slot,
     toggle_lock, versions, restore, publish, save.
   - Notifications center, dashboard stats/KPIs, settings, demo controls.
   - Multi-format export: /api/export/<format>/<target>/<id> for year,
     faculty, classroom targets.

4. Exporter (src/exporter.py)
   - reportlab -> PDF (landscape A4), openpyxl -> Excel (.xlsx),
     python-docx -> Word (.docx), csv module -> CSV (.csv).
   - Exports class timetables, individual faculty timetables, and room
     utilization schedules with institution branding.

TECH STACK
----------
- Language: Python 3
- Backend framework: Flask (>=3.0.0)
- Database: SQLite (file-based, slotify.db)
- Export libraries: reportlab (PDF), openpyxl (Excel), python-docx (Word)
- Frontend: vanilla HTML/JS single-page app consuming the Flask API
- Config: .env (SECRET_KEY, PORT=5050, FLASK_ENV)

RUN
---
  pip install -r src/requirements.txt
  cp .env.example .env   # customize SECRET_KEY/PORT if needed
  python src/app.py      # serves on http://127.0.0.1:5050

FILES
-----
  src/app.py          Flask API controller & route definitions
  src/scheduler.py    CSP timetable engine + conflict detection
  src/database.py     SQLite persistence, CRUD, demo controls, versioning
  src/exporter.py     PDF/Excel/Word/CSV export engine
  src/timetable.py    Legacy console scheduler prototype
  src/templates/index.html  Frontend SPA
  requirements.txt    Python dependencies
  .env.example        Environment configuration template
