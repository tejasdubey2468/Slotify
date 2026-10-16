# Slotify 🗓️ — Smart College Timetable Management & Scheduling Platform

![Cover image](assets/TG-Cover.png)

**Slotify 🗓️** is a comprehensive, production-oriented academic scheduling platform designed for engineering colleges and universities. It transforms manual, error-prone timetable planning into an automated, conflict-free scheduling workflow supporting multi-year, multi-department, classroom, and faculty allocations.

---

## 🌟 Key Features

### 1. Swiss Grid Minimalism & Modern Campus Aesthetics
- Curated academic palette: Warm cream (`#FAF5EB`), Forest green (`#315C45`), Soft sage (`#DCEBDD`), Mint (`#D5EEE3`), Pale terracotta (`#F3DDD0`), Soft lavender (`#E9E0F2`), and Butter yellow (`#F5EDC9`).
- Rounded geometry (10–14px radii), restrained shadows, and clear typography (Inter & Manrope).
- Visually distinctive pastel timetable session blocks with subject, teacher initials, room badge, and time range.

### 2. Constraint-Solving Timetable Generation Engine
- **Hard Constraints (Zero Violations Guaranteed):**
  - No teacher can be scheduled simultaneously across SE, TE, or BE classes.
  - No classroom or laboratory can be double-booked.
  - Designated **Recess & Lunch Break (1:45 PM – 2:15 PM)** is strictly protected from lecture scheduling.
  - Practical sessions are allocated in consecutive 2-hour blocks with dedicated laboratories.
- **Soft Constraints (Optimization):**
  - Teacher preferred time slots (Slot A Morning, Slot B Afternoon, Slot C Full Day, Slot D Flexible).
  - Balanced daily and weekly instructional workload distribution.

### 3. Faculty Directory & Personalized Schedules
- Searchable directory of 16 full-time faculty members with designations and weekly workload caps.
- Dedicated **Individual Faculty Timetables**: view any professor's personalized 6-day teaching matrix, assigned classrooms, and free periods.
- Dedicated one-click PDF, Excel, and Word exports for individual faculty schedules.

### 4. Classroom & Laboratory Visibility
- Complete registry of 5 lecture halls (Rooms 301, 302, 303, 401, 402) and 6 specialized labs (Labs 701, 702, 704, 501, 108, LL).
- Interactive **Classroom Timetable View**: inspect weekly occupancy, room utilization percentage, and scheduled batches.

### 5. Multi-Format Export Center
- **PDF Export (`reportlab`)**: Clean landscape A4 institutional timetable with official sign-off headers.
- **Excel Export (`openpyxl`)**: Stylized `.xlsx` workbook with auto-fitted columns, header formatting, and gridlines.
- **Word Export (`python-docx`)**: Formatted `.docx` document with styled schedule tables.
- **CSV Export**: Machine-readable RFC-4180 CSV export.
- **Print-Friendly View**: Clean `@media print` CSS for direct browser printing.

### 6. Academic Calendar & Official Holidays
- Full-year academic calendar with official national, state, and institutional holiday schedules for 2026–2027.
- Complete CRUD controls to add, edit, or remove institution-specific holiday entries.

### 7. Version History & Approval Workflow
- Revision audit trail tracking version numbers, draft/approved/published statuses, conflict counts, timestamps, and authors.
- Safe one-click version restoration with new audit records.

### 8. Smart Conflict Detection Center
- Real-time constraint validator identifying teacher overlaps, room collisions, and recess violations.
- Direct click-to-edit capability on timetable cells with instant conflict recalculation.

---

## 🏛️ Project Architecture

```
Slotify/
├── assets/                     # Architectural diagrams & cover images
├── src/
│   ├── app.py                  # Flask application & REST API controller
│   ├── database.py             # SQLite persistent storage & CRUD methods
│   ├── scheduler.py            # Constraint validation & scheduling solver
│   ├── exporter.py             # Multi-format export engine (PDF, XLSX, DOCX, CSV)
│   ├── templates/
│   │   └── index.html          # Slotify single-page application interface
│   ├── requirements.txt        # Python package dependencies
│   └── timetable.py            # Legacy scheduling core
├── .env.example                # Environment configuration template
├── requirements.txt            # Root dependencies configuration
├── .gitignore                  # Git exclusions for secrets, databases & artifacts
└── README.md                   # Platform documentation
```

---

## 🚀 Quickstart & Local Installation

### Prerequisites
- Python 3.9+
- pip

### 1. Install Dependencies
```bash
cd src
pip install -r requirements.txt
```

### 2. Run the Platform
```bash
python app.py
```
*Slotify will start automatically on `http://127.0.0.1:5000` (or `http://127.0.0.1:5001` if port 5000 is occupied).*

### 3. Open in Browser
Visit **`http://127.0.0.1:5000/`** to access the complete interactive interface.

---

## 🧪 Testing

To execute automated validation of the database, constraint solver, and multi-format exports:

```bash
# Verify database seeding and CRUD:
python -c "import database; database.init_db(); print(database.get_dashboard_stats())"

# Verify constraint solver:
python -c "import database, scheduler; teachers = database.get_teachers_legacy_format(); data, conflicts = scheduler.generate_schedules(teachers); print(f'Hard conflicts: {len(conflicts)}')"

# Verify multi-format exports:
python -c "import database, scheduler, exporter; t = database.get_teachers_legacy_format(); d, _ = scheduler.generate_schedules(t); exporter.export_pdf('Test', 'SE', ['Day']+d['timeSlots'], d['se'])"
```

---

## 👥 Authors & Credits
- **Slotify Development Team** — Advanced Academic Scheduling Solutions
- Original Base Project: [Nilesh Parab](https://github.com/nileshparab42)
