"""
Slotify 🗓️ — Database Module
SQLite-based persistent storage for the college timetable management platform.
Supports multi-department, academic years, divisions, batches, subjects, classrooms, labs,
teachers with multi-subject assignments, unavailability, time slots, recesses, holidays,
version history, notifications, origin tracking (demo vs user), and system settings.
"""

import sqlite3
import os
import json
import re
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'slotify.db')


def get_db():
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def dict_from_row(row):
    """Convert a sqlite3.Row to a dict."""
    if row is None:
        return None
    return dict(row)


def init_db():
    """Initialize database tables and run automatic migrations."""
    conn = get_db()
    c = conn.cursor()

    # ── Departments ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            hod_name TEXT DEFAULT '',
            is_demo INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Academic Years ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS academic_years (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            year_number INTEGER NOT NULL,
            department_id INTEGER DEFAULT 1,
            is_demo INTEGER DEFAULT 0,
            FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
        )
    ''')

    # ── Divisions ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS divisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            academic_year_id INTEGER NOT NULL,
            strength INTEGER DEFAULT 60,
            batch_count INTEGER DEFAULT 3,
            notes TEXT DEFAULT '',
            is_demo INTEGER DEFAULT 0,
            FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE
        )
    ''')

    # ── Batches (for division practical sessions) ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            division_id INTEGER NOT NULL,
            strength INTEGER DEFAULT 20,
            is_demo INTEGER DEFAULT 0,
            FOREIGN KEY (division_id) REFERENCES divisions(id) ON DELETE CASCADE
        )
    ''')

    # ── Subjects ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            subject_type TEXT DEFAULT 'theory',
            theory_hours_per_week INTEGER DEFAULT 0,
            practical_hours_per_week INTEGER DEFAULT 0,
            tutorial_hours_per_week INTEGER DEFAULT 0,
            credits INTEGER DEFAULT 0,
            academic_year_id INTEGER,
            is_elective BOOLEAN DEFAULT 0,
            preferred_room TEXT DEFAULT '',
            required_room_type TEXT DEFAULT 'classroom',
            assigned_divisions TEXT DEFAULT '',
            session_duration INTEGER DEFAULT 1,
            is_demo INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE SET NULL
        )
    ''')

    # ── Classrooms ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS classrooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            room_number TEXT NOT NULL UNIQUE,
            room_type TEXT DEFAULT 'classroom',
            capacity INTEGER DEFAULT 60,
            floor_number INTEGER DEFAULT 0,
            building TEXT DEFAULT 'Main Academic Block',
            has_projector BOOLEAN DEFAULT 1,
            has_ac BOOLEAN DEFAULT 0,
            is_available BOOLEAN DEFAULT 1,
            is_demo INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Teachers / Faculty ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id TEXT DEFAULT '',
            name TEXT NOT NULL,
            initials TEXT NOT NULL,
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            department_id INTEGER DEFAULT 1,
            designation TEXT DEFAULT 'Assistant Professor',
            time_slot TEXT DEFAULT 'C',
            max_hours_per_day INTEGER DEFAULT 6,
            max_hours_per_week INTEGER DEFAULT 24,
            max_consecutive_lectures INTEGER DEFAULT 3,
            unavailable_slots TEXT DEFAULT '',
            assigned_divisions TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            is_active BOOLEAN DEFAULT 1,
            is_demo INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
        )
    ''')

    # ── Teacher–Subject Assignments ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS teacher_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            academic_year_id INTEGER,
            theory_hours INTEGER DEFAULT 0,
            practical_hours INTEGER DEFAULT 0,
            lab_room TEXT DEFAULT '',
            is_demo INTEGER DEFAULT 0,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE SET NULL
        )
    ''')

    # ── Time Slots ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_number INTEGER NOT NULL UNIQUE,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            slot_type TEXT DEFAULT 'regular',
            is_active BOOLEAN DEFAULT 1,
            is_demo INTEGER DEFAULT 0
        )
    ''')

    # ── Working Days ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS working_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_name TEXT NOT NULL UNIQUE,
            day_number INTEGER NOT NULL UNIQUE,
            is_working BOOLEAN DEFAULT 1,
            is_demo INTEGER DEFAULT 0
        )
    ''')

    # ── Holidays ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            holiday_type TEXT DEFAULT 'public',
            description TEXT DEFAULT '',
            is_demo INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Generated Timetables ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS timetables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            academic_year_code TEXT NOT NULL,
            timetable_data TEXT NOT NULL,
            conflicts_count INTEGER DEFAULT 0,
            is_published BOOLEAN DEFAULT 0,
            is_demo INTEGER DEFAULT 0,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Timetable Versions ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS timetable_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_number INTEGER NOT NULL,
            name TEXT NOT NULL,
            academic_year_code TEXT NOT NULL,
            status TEXT DEFAULT 'Draft',
            change_summary TEXT DEFAULT '',
            created_by TEXT DEFAULT 'Academic Administrator',
            timetable_data TEXT NOT NULL,
            conflicts_count INTEGER DEFAULT 0,
            is_demo INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Notifications ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            category TEXT DEFAULT 'system',
            link TEXT DEFAULT '',
            is_read BOOLEAN DEFAULT 0,
            is_demo INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Settings (key-value store) ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    # ── Run Migrations for columns added to pre-existing tables ──
    _run_migrations(c)

    # ── Seed defaults if empty ──
    _seed_defaults(c)

    conn.commit()
    conn.close()


def _run_migrations(c):
    """Ensure any newly added columns exist in older database files."""
    def get_existing_columns(table_name):
        c.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in c.fetchall()]

    # Departments migrations
    dept_cols = get_existing_columns('departments')
    if 'is_demo' not in dept_cols:
        c.execute("ALTER TABLE departments ADD COLUMN is_demo INTEGER DEFAULT 0")

    # Academic years migrations
    ay_cols = get_existing_columns('academic_years')
    if 'is_demo' not in ay_cols:
        c.execute("ALTER TABLE academic_years ADD COLUMN is_demo INTEGER DEFAULT 0")

    # Divisions migrations
    div_cols = get_existing_columns('divisions')
    if 'batch_count' not in div_cols:
        c.execute("ALTER TABLE divisions ADD COLUMN batch_count INTEGER DEFAULT 3")
    if 'notes' not in div_cols:
        c.execute("ALTER TABLE divisions ADD COLUMN notes TEXT DEFAULT ''")
    if 'is_demo' not in div_cols:
        c.execute("ALTER TABLE divisions ADD COLUMN is_demo INTEGER DEFAULT 0")

    # Subjects migrations
    sub_cols = get_existing_columns('subjects')
    if 'required_room_type' not in sub_cols:
        c.execute("ALTER TABLE subjects ADD COLUMN required_room_type TEXT DEFAULT 'classroom'")
    if 'assigned_divisions' not in sub_cols:
        c.execute("ALTER TABLE subjects ADD COLUMN assigned_divisions TEXT DEFAULT ''")
    if 'session_duration' not in sub_cols:
        c.execute("ALTER TABLE subjects ADD COLUMN session_duration INTEGER DEFAULT 1")
    if 'is_demo' not in sub_cols:
        c.execute("ALTER TABLE subjects ADD COLUMN is_demo INTEGER DEFAULT 0")

    # Classrooms migrations
    room_cols = get_existing_columns('classrooms')
    if 'is_demo' not in room_cols:
        c.execute("ALTER TABLE classrooms ADD COLUMN is_demo INTEGER DEFAULT 0")

    # Teachers migrations
    t_cols = get_existing_columns('teachers')
    if 'faculty_id' not in t_cols:
        c.execute("ALTER TABLE teachers ADD COLUMN faculty_id TEXT DEFAULT ''")
    if 'max_consecutive_lectures' not in t_cols:
        c.execute("ALTER TABLE teachers ADD COLUMN max_consecutive_lectures INTEGER DEFAULT 3")
    if 'unavailable_slots' not in t_cols:
        c.execute("ALTER TABLE teachers ADD COLUMN unavailable_slots TEXT DEFAULT ''")
    if 'assigned_divisions' not in t_cols:
        c.execute("ALTER TABLE teachers ADD COLUMN assigned_divisions TEXT DEFAULT ''")
    if 'notes' not in t_cols:
        c.execute("ALTER TABLE teachers ADD COLUMN notes TEXT DEFAULT ''")
    if 'is_demo' not in t_cols:
        c.execute("ALTER TABLE teachers ADD COLUMN is_demo INTEGER DEFAULT 0")

    # Teacher subjects migrations
    ts_cols = get_existing_columns('teacher_subjects')
    if 'is_demo' not in ts_cols:
        c.execute("ALTER TABLE teacher_subjects ADD COLUMN is_demo INTEGER DEFAULT 0")

    # Holidays migrations
    h_cols = get_existing_columns('holidays')
    if 'is_demo' not in h_cols:
        c.execute("ALTER TABLE holidays ADD COLUMN is_demo INTEGER DEFAULT 0")

    # Timetables migrations
    tt_cols = get_existing_columns('timetables')
    if 'is_demo' not in tt_cols:
        c.execute("ALTER TABLE timetables ADD COLUMN is_demo INTEGER DEFAULT 0")

    # Timetable versions migrations
    v_cols = get_existing_columns('timetable_versions')
    if 'is_demo' not in v_cols:
        c.execute("ALTER TABLE timetable_versions ADD COLUMN is_demo INTEGER DEFAULT 0")

    # Notifications migrations
    n_cols = get_existing_columns('notifications')
    if 'is_demo' not in n_cols:
        c.execute("ALTER TABLE notifications ADD COLUMN is_demo INTEGER DEFAULT 0")


def _seed_defaults(c):
    """Seed foundational settings and structural entities."""
    # 1. Departments
    c.execute("SELECT COUNT(*) FROM departments")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO departments (name, code, hod_name, is_demo) VALUES (?, ?, ?, 1)",
                  ("Computer Engineering", "CE", "Dr. Rajesh Sharma"))
        c.execute("INSERT INTO departments (name, code, hod_name, is_demo) VALUES (?, ?, ?, 1)",
                  ("Information Technology", "IT", "Dr. Sunita Kulkarni"))
        c.execute("INSERT INTO departments (name, code, hod_name, is_demo) VALUES (?, ?, ?, 1)",
                  ("AI & Data Science", "AIDS", "Dr. Manoj Patel"))

    # 2. Academic Years
    c.execute("SELECT COUNT(*) FROM academic_years")
    if c.fetchone()[0] == 0:
        for name, code, num in [
            ("SE — Second Year", "SE", 2),
            ("TE — Third Year", "TE", 3),
            ("BE — Final Year", "BE", 4)
        ]:
            c.execute("INSERT INTO academic_years (name, code, year_number, is_demo) VALUES (?, ?, ?, 1)",
                      (name, code, num))

    # 3. Settings
    c.execute("SELECT COUNT(*) FROM settings")
    if c.fetchone()[0] == 0:
        defaults = {
            'institution_name': 'Slotify Institute of Technology',
            'department_name': 'Department of Computer Engineering',
            'academic_session': '2026–2027',
            'semester': 'Odd Semester (Term I)',
            'college_opening_time': '09:00',
            'college_closing_time': '17:00',
            'lecture_duration_minutes': '60',
            'recess_start': '1:45',
            'recess_end': '2:15',
            'short_break_duration': '10',
            'max_lectures_per_day': '6',
            'max_consecutive_lectures': '3',
            'allow_saturday': '1',
            'working_days': 'MON,TUE,WED,THU,FRI,SAT',
            'active_department': 'Computer Engineering'
        }
        for k, v in defaults.items():
            c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (k, v))

    # 4. Time Slots
    c.execute("SELECT COUNT(*) FROM time_slots")
    if c.fetchone()[0] == 0:
        slots = [
            (1, "9:45",  "10:45", "regular"),
            (2, "10:45", "11:45", "regular"),
            (3, "11:45", "12:45", "regular"),
            (4, "12:45", "1:45",  "regular"),
            (5, "1:45",  "2:15",  "recess"),
            (6, "2:15",  "3:15",  "regular"),
            (7, "3:15",  "4:15",  "regular"),
        ]
        for s in slots:
            c.execute("INSERT INTO time_slots (slot_number, start_time, end_time, slot_type, is_demo) VALUES (?,?,?,?,1)", s)

    # 5. Working Days
    c.execute("SELECT COUNT(*) FROM working_days")
    if c.fetchone()[0] == 0:
        for day, num, working in [
            ("MON", 1, 1), ("TUE", 2, 1), ("WED", 3, 1),
            ("THU", 4, 1), ("FRI", 5, 1), ("SAT", 6, 1)
        ]:
            c.execute("INSERT INTO working_days (day_name, day_number, is_working, is_demo) VALUES (?,?,?,1)",
                      (day, num, working))

    # 6. Check if faculty and sample data exist
    c.execute("SELECT COUNT(*) FROM teachers")
    if c.fetchone()[0] == 0:
        _seed_demo_dataset(c)


def _seed_demo_dataset(c):
    """Seed comprehensive, internally-consistent sample academic data marked with is_demo = 1."""
    # Lookup year IDs
    ay_map = {}
    for r in c.execute("SELECT id, code FROM academic_years"):
        ay_map[r['code']] = r['id']

    # Divisions
    divisions_seed = [
        ("Div A", ay_map.get('SE', 1), 65, 3),
        ("Div B", ay_map.get('SE', 1), 60, 3),
        ("Div A", ay_map.get('TE', 2), 65, 3),
        ("Div A", ay_map.get('BE', 3), 62, 3)
    ]
    for dname, yid, strength, bcount in divisions_seed:
        c.execute("SELECT id FROM divisions WHERE name = ? AND academic_year_id = ?", (dname, yid))
        row = c.fetchone()
        if not row:
            c.execute("""
                INSERT INTO divisions (name, academic_year_id, strength, batch_count, is_demo)
                VALUES (?, ?, ?, ?, 1)
            """, (dname, yid, strength, bcount))
            div_id = c.lastrowid
            for bidx in range(1, bcount + 1):
                c.execute("""
                    INSERT INTO batches (name, division_id, strength, is_demo)
                    VALUES (?, ?, ?, 1)
                """, (f"{dname}-B{bidx}", div_id, strength // bcount))

    # Classrooms & Labs
    rooms = [
        ("Classroom 301", "301", "classroom", 75, 3, "Main Academic Block", 1, 1),
        ("Classroom 302", "302", "classroom", 75, 3, "Main Academic Block", 1, 1),
        ("Classroom 303", "303", "classroom", 70, 3, "Main Academic Block", 1, 0),
        ("Classroom 401", "401", "classroom", 75, 4, "Main Academic Block", 1, 1),
        ("Classroom 402", "402", "classroom", 75, 4, "Main Academic Block", 1, 0),
        ("Lab 701 (Systems Lab)", "701", "laboratory", 35, 7, "Tech Annex", 1, 1),
        ("Lab 702 (Algorithms Lab)", "702", "laboratory", 35, 7, "Tech Annex", 1, 1),
        ("Lab 704 (Networks & SPCC Lab)", "704", "laboratory", 35, 7, "Tech Annex", 1, 1),
        ("Lab 501 (AI & Python Lab)", "501", "laboratory", 35, 5, "Tech Annex", 1, 1),
        ("Lab 108 (Cyber Security Lab)", "108", "laboratory", 35, 1, "Tech Annex", 1, 1),
        ("Lab LL (Language & DBMS Lab)", "LL", "laboratory", 35, 2, "Central Block", 1, 1),
    ]
    for r in rooms:
        c.execute("SELECT id FROM classrooms WHERE room_number = ?", (r[1],))
        if not c.fetchone():
            c.execute("""
                INSERT INTO classrooms (name, room_number, room_type, capacity, floor_number, building, has_projector, has_ac, is_demo)
                VALUES (?,?,?,?,?,?,?,?,1)
            """, r)

    # Subjects for SE, TE, BE
    subjects_seed = [
        # SE Subjects
        ("Operating Systems", "OS", "theory", 3, 2, 0, 4, ay_map.get('SE', 1), "704", "laboratory"),
        ("Microprocessor Architecture", "MP", "theory", 3, 2, 0, 4, ay_map.get('SE', 1), "701", "laboratory"),
        ("Database Management Systems", "DBMS", "theory", 3, 2, 0, 4, ay_map.get('SE', 1), "LL", "laboratory"),
        ("Analysis of Algorithms", "AOA", "theory", 3, 2, 0, 4, ay_map.get('SE', 1), "702", "laboratory"),
        ("Python Programming Lab", "PYTHON", "practical", 2, 2, 0, 3, ay_map.get('SE', 1), "501", "laboratory"),
        ("Engineering Mathematics IV", "EM4", "theory", 3, 0, 0, 3, ay_map.get('SE', 1), "301", "classroom"),
        
        # TE Subjects
        ("System Programming & Compiler Construction", "SPCC", "theory", 3, 2, 0, 4, ay_map.get('TE', 2), "704", "laboratory"),
        ("Artificial Intelligence", "AI", "theory", 3, 2, 0, 4, ay_map.get('TE', 2), "501", "laboratory"),
        ("Cryptography & Network Security", "CNSS", "theory", 3, 2, 0, 4, ay_map.get('TE', 2), "108", "laboratory"),
        ("Mobile Computing", "MC", "theory", 3, 2, 0, 4, ay_map.get('TE', 2), "704", "laboratory"),
        ("Internet of Things", "IOT", "theory", 3, 0, 0, 3, ay_map.get('TE', 2), "302", "classroom"),
        ("Cloud Computing Lab", "CC", "practical", 0, 2, 0, 2, ay_map.get('TE', 2), "501", "laboratory"),

        # BE Subjects
        ("Human Machine Interaction", "HMI", "theory", 4, 2, 0, 4, ay_map.get('BE', 3), "702", "laboratory"),
        ("Engineering Management", "EM", "theory", 3, 0, 0, 3, ay_map.get('BE', 3), "401", "classroom"),
        ("Ad-hoc Wireless Networks", "AWN", "theory", 4, 2, 0, 4, ay_map.get('BE', 3), "501", "laboratory"),
        ("Distributed Computing", "DC", "theory", 4, 2, 0, 4, ay_map.get('BE', 3), "701", "laboratory"),
    ]

    sub_id_map = {}
    for s in subjects_seed:
        c.execute("SELECT id FROM subjects WHERE code = ? AND academic_year_id = ?", (s[1], s[7]))
        s_row = c.fetchone()
        if s_row:
            sub_id_map[(s[1], s[7])] = s_row[0]
        else:
            c.execute("""
                INSERT INTO subjects (name, code, subject_type, theory_hours_per_week, practical_hours_per_week,
                                      tutorial_hours_per_week, credits, academic_year_id, preferred_room,
                                      required_room_type, is_demo)
                VALUES (?,?,?,?,?,?,?,?,?,?,1)
            """, s)
            sub_id_map[(s[1], s[7])] = c.lastrowid

    # 16 Faculty Members with realistic qualifications, preferences, and multi-subject mappings
    faculty_seed = [
        ("FAC-001", "Prof. Chandan Gaikwad", "CG", "c.gaikwad@slotify.edu", "Associate Professor", "C", 6, 20, [
            ('OS', 'SE', 3, 2, '704')
        ]),
        ("FAC-002", "Prof. Niharika More", "NM", "n.more@slotify.edu", "Assistant Professor", "A", 6, 18, [
            ('MP', 'SE', 3, 2, '701')
        ]),
        ("FAC-003", "Dr. Ashish Gupta", "AG", "a.gupta@slotify.edu", "Professor", "C", 6, 20, [
            ('DBMS', 'SE', 3, 2, 'LL')
        ]),
        ("FAC-004", "Prof. Deepa Raut", "DR", "d.raut@slotify.edu", "Assistant Professor", "B", 6, 18, [
            ('AOA', 'SE', 3, 2, '702')
        ]),
        ("FAC-005", "Prof. Amit Sharma", "AS", "a.sharma@slotify.edu", "Assistant Professor", "C", 6, 18, [
            ('PYTHON', 'SE', 2, 2, '501')
        ]),
        ("FAC-006", "Prof. Anjali Joshi", "AJ", "a.joshi@slotify.edu", "Assistant Professor", "D", 6, 16, [
            ('EM4', 'SE', 3, 0, '301')
        ]),
        ("FAC-007", "Prof. Rajesh Jadhav", "RJ", "r.jadhav@slotify.edu", "Associate Professor", "A", 6, 20, [
            ('SPCC', 'TE', 3, 2, '704')
        ]),
        ("FAC-008", "Dr. Nupur Varma", "NV", "n.varma@slotify.edu", "Associate Professor", "C", 6, 20, [
            ('AI', 'TE', 3, 2, '501')
        ]),
        ("FAC-009", "Prof. Umesh Agrawal", "UA", "u.agrawal@slotify.edu", "Assistant Professor", "C", 6, 18, [
            ('CNSS', 'TE', 3, 2, '108')
        ]),
        ("FAC-010", "Prof. Rashmi Shah", "RS", "r.shah@slotify.edu", "Assistant Professor", "C", 6, 18, [
            ('MC', 'TE', 3, 2, '704')
        ]),
        ("FAC-011", "Dr. Devendra N. Roy", "DNR", "d.roy@slotify.edu", "Professor", "A", 6, 16, [
            ('IOT', 'TE', 3, 0, '302')
        ]),
        ("FAC-012", "Prof. Meena N. Rao", "MNR", "m.rao@slotify.edu", "Assistant Professor", "C", 6, 16, [
            ('CC', 'TE', 0, 2, '501')
        ]),
        ("FAC-013", "Prof. Sanjay Singh", "SS", "s.singh@slotify.edu", "Associate Professor", "A", 6, 22, [
            ('HMI', 'BE', 4, 2, '702')
        ]),
        ("FAC-014", "Prof. Vikas Joshi", "VJ", "v.joshi@slotify.edu", "Assistant Professor", "C", 6, 18, [
            ('EM', 'BE', 3, 0, '401')
        ]),
        ("FAC-015", "Prof. Tushar R. Patil", "TRP", "t.patil@slotify.edu", "Assistant Professor", "A", 6, 22, [
            ('AWN', 'BE', 4, 2, '501')
        ]),
        ("FAC-016", "Prof. Sonal Sharma", "SS2", "s.sharma2@slotify.edu", "Assistant Professor", "B", 6, 22, [
            ('DC', 'BE', 4, 2, '701')
        ]),
    ]

    for fid, fname, inits, email, desig, slot, max_d, max_w, assigns in faculty_seed:
        c.execute("SELECT id FROM teachers WHERE initials = ?", (inits,))
        t_row = c.fetchone()
        if t_row:
            t_id = t_row[0]
            # Ensure it is marked as demo
            c.execute("UPDATE teachers SET is_demo = 1 WHERE id = ?", (t_id,))
        else:
            c.execute("""
                INSERT INTO teachers (faculty_id, name, initials, email, designation, time_slot,
                                      max_hours_per_day, max_hours_per_week, is_demo)
                VALUES (?,?,?,?,?,?,?,?,1)
            """, (fid, fname, inits, email, desig, slot, max_d, max_w))
            t_id = c.lastrowid

        for scode, ycode, th, pt, lab in assigns:
            s_id = sub_id_map.get((scode, ay_map.get(ycode)))
            if s_id:
                c.execute("""
                    SELECT id FROM teacher_subjects WHERE teacher_id = ? AND subject_id = ?
                """, (t_id, s_id))
                if not c.fetchone():
                    c.execute("""
                        INSERT INTO teacher_subjects (teacher_id, subject_id, academic_year_id,
                                                      theory_hours, practical_hours, lab_room, is_demo)
                        VALUES (?,?,?,?,?,?,1)
                    """, (t_id, s_id, ay_map.get(ycode), th, pt, lab))

    # Holidays (Official calendar)
    holidays_list = [
        ("Republic Day", "2026-01-26", "national", "National Holiday honoring Constitution Day"),
        ("Holi (Rangapanchami)", "2026-03-04", "public", "Spring Festival of Colors"),
        ("Gudi Padwa / Ugadi", "2026-03-19", "state", "Traditional New Year Celebration"),
        ("Eid-ul-Fitr", "2026-03-21", "public", "Islamic Festival"),
        ("Dr. Ambedkar Jayanti", "2026-04-14", "public", "Commemoration of Dr. B.R. Ambedkar"),
        ("Maharashtra Day / Labor Day", "2026-05-01", "state", "State Foundation Day"),
        ("Independence Day", "2026-08-15", "national", "National Independence Day"),
        ("Ganesh Chaturthi", "2026-09-14", "state", "Ten-day Ganesh Festival commencement"),
        ("Mahatma Gandhi Jayanti", "2026-10-02", "national", "Birth anniversary of Mahatma Gandhi"),
        ("Dussehra (Vijaya Dashami)", "2026-10-20", "public", "Triumph of Good festival"),
        ("Mid-Semester Academic Break", "2026-10-22", "academic", "Institutional mid-term review week"),
        ("Diwali (Laxmi Pujan)", "2026-11-08", "public", "Festival of Lights"),
        ("Diwali (Balipratipada)", "2026-11-09", "public", "New Vikram Samvat Year"),
        ("Guru Nanak Jayanti", "2026-11-24", "public", "Guru Nanak Prakash Utsav"),
        ("Semester Final Exams", "2026-12-01", "academic", "University Winter Session Examinations"),
        ("Christmas Day", "2026-12-25", "public", "Christmas Celebration"),
    ]
    for h in holidays_list:
        c.execute("SELECT id FROM holidays WHERE date = ? AND name = ?", (h[1], h[0]))
        if not c.fetchone():
            c.execute("INSERT INTO holidays (name, date, holiday_type, description, is_demo) VALUES (?,?,?,?,1)", h)

    # Initial notifications
    notifs = [
        ("Welcome to Slotify 🗓️", "Smart College Timetable Management & Scheduling Platform is ready.", "system", ""),
        ("Academic Calendar Loaded", "Official 2026-2027 holiday schedule and examination dates configured.", "holiday", "#calendar"),
        ("Classrooms & Labs Verified", "5 smart lecture halls and 6 high-capacity labs mapped for allocation.", "room_change", "#classrooms"),
        ("Faculty Directory Active", "16 departmental faculty profiles linked with weekly teaching qualifications.", "system", "#faculty"),
    ]
    for n in notifs:
        c.execute("SELECT id FROM notifications WHERE title = ?", (n[0],))
        if not c.fetchone():
            c.execute("INSERT INTO notifications (title, message, category, link, is_demo) VALUES (?,?,?,?,1)", n)


# ═════════════════════════════════════════════════════════
# DEMO DATA ONE-CLICK CONTROLS (REQUIREMENT 4)
# ═════════════════════════════════════════════════════════
def load_demo_data():
    """
    Safely load a complete, internally-consistent sample dataset.
    All records inserted are tagged with is_demo = 1.
    Will NOT create duplicate records if demo data is already loaded.
    Will NOT touch or overwrite any user-created records (is_demo = 0).
    """
    conn = get_db()
    c = conn.cursor()

    # Check if demo data is already loaded
    c.execute("SELECT COUNT(*) FROM teachers WHERE is_demo = 1 AND is_active = 1")
    demo_teachers_count = c.fetchone()[0]

    if demo_teachers_count > 0:
        conn.close()
        return {
            'status': 'ok',
            'message': 'Demo dataset is already loaded.',
            'already_loaded': True
        }

    # Seed the demo dataset
    _seed_demo_dataset(c)
    conn.commit()
    conn.close()

    return {
        'status': 'ok',
        'message': 'Sample academic dataset loaded successfully (16 faculty, 16 subjects, 11 rooms/labs, 4 divisions).',
        'already_loaded': False
    }


def erase_demo_data():
    """
    Safely erase ONLY records created by the demo-data mechanism (is_demo = 1).
    All user-created faculty, subjects, rooms, divisions, and timetables (is_demo = 0)
    are strictly preserved. Uses a database transaction in proper dependency order.
    """
    conn = get_db()
    c = conn.cursor()

    try:
        c.execute("BEGIN TRANSACTION")

        # Count records to be removed
        c.execute("SELECT COUNT(*) FROM teachers WHERE is_demo = 1")
        demo_t_count = c.fetchone()[0]

        # 1. Timetables & versions marked demo
        c.execute("DELETE FROM timetable_versions WHERE is_demo = 1")
        c.execute("DELETE FROM timetables WHERE is_demo = 1")

        # 2. Teacher subject assignments marked demo
        c.execute("DELETE FROM teacher_subjects WHERE is_demo = 1")

        # 3. Faculty marked demo
        c.execute("DELETE FROM teachers WHERE is_demo = 1")

        # 4. Batches marked demo
        c.execute("DELETE FROM batches WHERE is_demo = 1")

        # 5. Subjects marked demo
        c.execute("DELETE FROM subjects WHERE is_demo = 1")

        # 6. Divisions marked demo
        c.execute("DELETE FROM divisions WHERE is_demo = 1")

        # 7. Classrooms marked demo
        c.execute("DELETE FROM classrooms WHERE is_demo = 1")

        # 8. Holidays marked demo
        c.execute("DELETE FROM holidays WHERE is_demo = 1")

        # 9. Notifications marked demo
        c.execute("DELETE FROM notifications WHERE is_demo = 1")

        conn.commit()
        conn.close()

        return {
            'status': 'ok',
            'message': f"Demo dataset removed successfully ({demo_t_count} sample faculty and related records purged). All user-created records preserved.",
            'purged_count': demo_t_count
        }
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


def reset_to_sample_data():
    """Reset demo environment: erases demo data, then reloads fresh demo data."""
    erase_demo_data()
    return load_demo_data()


# ═════════════════════════════════════════════════════════
# CRUD HELPERS — DEPARTMENTS & ACADEMIC YEARS
# ═════════════════════════════════════════════════════════
def get_departments():
    conn = get_db()
    rows = conn.execute("SELECT * FROM departments ORDER BY id").fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def add_department(name, code, hod_name=''):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO departments (name, code, hod_name, is_demo) VALUES (?,?,?,0)",
              (name.strip(), code.strip().upper(), hod_name.strip()))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def delete_department(dept_id):
    conn = get_db()
    conn.execute("DELETE FROM departments WHERE id = ?", (dept_id,))
    conn.commit()
    conn.close()

def get_academic_years():
    conn = get_db()
    rows = conn.execute("SELECT * FROM academic_years ORDER BY year_number").fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def add_academic_year(name, code, year_number, department_id=1):
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO academic_years (name, code, year_number, department_id, is_demo) VALUES (?,?,?,?,0)",
                  (name.strip(), code.strip().upper(), int(year_number), department_id))
        new_id = c.lastrowid
        conn.commit()
        return new_id
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════
# CRUD HELPERS — DIVISIONS & BATCHES
# ═════════════════════════════════════════════════════════
def get_divisions():
    conn = get_db()
    rows = conn.execute("""
        SELECT d.*, ay.code as year_code, ay.name as year_name
        FROM divisions d
        JOIN academic_years ay ON d.academic_year_id = ay.id
        ORDER BY ay.year_number, d.name
    """).fetchall()
    divisions = [dict_from_row(r) for r in rows]
    for d in divisions:
        b_rows = conn.execute("SELECT * FROM batches WHERE division_id = ? ORDER BY name", (d['id'],)).fetchall()
        d['batches'] = [dict_from_row(b) for b in b_rows]
    conn.close()
    return divisions

def get_division(div_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM divisions WHERE id = ?", (div_id,)).fetchone()
    d = dict_from_row(row) if row else None
    if d:
        b_rows = conn.execute("SELECT * FROM batches WHERE division_id = ? ORDER BY name", (div_id,)).fetchall()
        d['batches'] = [dict_from_row(b) for b in b_rows]
    conn.close()
    return d

def add_division(data):
    conn = get_db()
    c = conn.cursor()
    name = data['name'].strip()
    ay_id = int(data['academic_year_id'])
    strength = int(data.get('strength', 60))
    batch_count = int(data.get('batch_count', 3))
    notes = data.get('notes', '').strip()

    c.execute("""
        INSERT INTO divisions (name, academic_year_id, strength, batch_count, notes, is_demo)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (name, ay_id, strength, batch_count, notes))
    div_id = c.lastrowid

    # Create batches
    for b in range(1, batch_count + 1):
        bname = f"{name}-B{b}"
        bstrength = strength // batch_count
        c.execute("""
            INSERT INTO batches (name, division_id, strength, is_demo)
            VALUES (?, ?, ?, 0)
        """, (bname, div_id, bstrength))

    conn.commit()
    conn.close()
    return div_id

def update_division(div_id, data):
    conn = get_db()
    c = conn.cursor()
    name = data['name'].strip()
    ay_id = int(data['academic_year_id'])
    strength = int(data.get('strength', 60))
    batch_count = int(data.get('batch_count', 3))
    notes = data.get('notes', '').strip()

    c.execute("""
        UPDATE divisions
        SET name=?, academic_year_id=?, strength=?, batch_count=?, notes=?
        WHERE id=?
    """, (name, ay_id, strength, batch_count, notes, div_id))

    # Recreate batches
    c.execute("DELETE FROM batches WHERE division_id = ?", (div_id,))
    for b in range(1, batch_count + 1):
        bname = f"{name}-B{b}"
        bstrength = strength // batch_count
        c.execute("""
            INSERT INTO batches (name, division_id, strength, is_demo)
            VALUES (?, ?, ?, 0)
        """, (bname, div_id, bstrength))

    conn.commit()
    conn.close()

def delete_division(div_id):
    conn = get_db()
    conn.execute("DELETE FROM batches WHERE division_id = ?", (div_id,))
    conn.execute("DELETE FROM divisions WHERE id = ?", (div_id,))
    conn.commit()
    conn.close()


# ═════════════════════════════════════════════════════════
# CRUD HELPERS — SUBJECTS
# ═════════════════════════════════════════════════════════
def get_subjects():
    conn = get_db()
    rows = conn.execute("""
        SELECT s.*, ay.code as year_code, ay.name as year_name
        FROM subjects s
        LEFT JOIN academic_years ay ON s.academic_year_id = ay.id
        ORDER BY s.academic_year_id, s.name
    """).fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def get_subject(sub_id):
    conn = get_db()
    row = conn.execute("""
        SELECT s.*, ay.code as year_code, ay.name as year_name
        FROM subjects s
        LEFT JOIN academic_years ay ON s.academic_year_id = ay.id
        WHERE s.id = ?
    """, (sub_id,)).fetchone()
    conn.close()
    return dict_from_row(row)

def add_subject(data):
    """Add new subject with validation."""
    conn = get_db()
    c = conn.cursor()

    code = data['code'].strip().upper()
    name = data['name'].strip()
    ay_id = data.get('academic_year_id')

    # Validate duplicate code within the same year
    if ay_id:
        existing = c.execute("SELECT id FROM subjects WHERE code = ? AND academic_year_id = ?", (code, ay_id)).fetchone()
        if existing:
            conn.close()
            raise ValueError(f"Subject with code '{code}' already exists for this academic year.")

    c.execute("""
        INSERT INTO subjects (name, code, subject_type, theory_hours_per_week,
            practical_hours_per_week, tutorial_hours_per_week, credits,
            academic_year_id, is_elective, preferred_room, required_room_type,
            assigned_divisions, session_duration, is_demo)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0)
    """, (
        name, code, data.get('subject_type', 'theory'),
        int(data.get('theory_hours_per_week', 0) or 0),
        int(data.get('practical_hours_per_week', 0) or 0),
        int(data.get('tutorial_hours_per_week', 0) or 0),
        int(data.get('credits', 0) or 0),
        ay_id,
        int(data.get('is_elective', 0) or 0),
        data.get('preferred_room', ''),
        data.get('required_room_type', 'classroom'),
        data.get('assigned_divisions', ''),
        int(data.get('session_duration', 1) or 1)
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_subject(sub_id, data):
    conn = get_db()
    c = conn.cursor()

    code = data['code'].strip().upper()
    name = data['name'].strip()
    ay_id = data.get('academic_year_id')

    # Check duplicate on other subjects
    existing = c.execute("SELECT id FROM subjects WHERE code = ? AND academic_year_id = ? AND id != ?",
                         (code, ay_id, sub_id)).fetchone()
    if existing:
        conn.close()
        raise ValueError(f"Another subject already has code '{code}' in this academic year.")

    c.execute("""
        UPDATE subjects SET name=?, code=?, subject_type=?,
            theory_hours_per_week=?, practical_hours_per_week=?,
            tutorial_hours_per_week=?, credits=?,
            academic_year_id=?, is_elective=?, preferred_room=?,
            required_room_type=?, assigned_divisions=?, session_duration=?
        WHERE id=?
    """, (
        name, code, data.get('subject_type', 'theory'),
        int(data.get('theory_hours_per_week', 0) or 0),
        int(data.get('practical_hours_per_week', 0) or 0),
        int(data.get('tutorial_hours_per_week', 0) or 0),
        int(data.get('credits', 0) or 0),
        ay_id,
        int(data.get('is_elective', 0) or 0),
        data.get('preferred_room', ''),
        data.get('required_room_type', 'classroom'),
        data.get('assigned_divisions', ''),
        int(data.get('session_duration', 1) or 1),
        sub_id
    ))
    conn.commit()
    conn.close()

def delete_subject(sub_id):
    conn = get_db()
    conn.execute("DELETE FROM teacher_subjects WHERE subject_id = ?", (sub_id,))
    conn.execute("DELETE FROM subjects WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()


# ═════════════════════════════════════════════════════════
# CRUD HELPERS — CLASSROOMS & LABORATORIES
# ═════════════════════════════════════════════════════════
def get_classrooms():
    conn = get_db()
    rows = conn.execute("SELECT * FROM classrooms ORDER BY room_type DESC, room_number").fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def get_classroom(room_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM classrooms WHERE id = ?", (room_id,)).fetchone()
    conn.close()
    return dict_from_row(row)

def add_classroom(data):
    conn = get_db()
    c = conn.cursor()

    room_num = data['room_number'].strip()
    name = data['name'].strip()

    existing = c.execute("SELECT id FROM classrooms WHERE room_number = ?", (room_num,)).fetchone()
    if existing:
        conn.close()
        raise ValueError(f"Room with number '{room_num}' already exists.")

    c.execute("""
        INSERT INTO classrooms (name, room_number, room_type, capacity,
            floor_number, building, has_projector, has_ac, is_available, is_demo)
        VALUES (?,?,?,?,?,?,?,?,?,0)
    """, (
        name, room_num, data.get('room_type', 'classroom'),
        int(data.get('capacity', 60) or 60),
        int(data.get('floor_number', 0) or 0),
        data.get('building', 'Main Academic Block'),
        1 if data.get('has_projector', True) else 0,
        1 if data.get('has_ac', False) else 0,
        1 if data.get('is_available', True) else 0
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_classroom(room_id, data):
    conn = get_db()
    c = conn.cursor()

    room_num = data['room_number'].strip()
    existing = c.execute("SELECT id FROM classrooms WHERE room_number = ? AND id != ?", (room_num, room_id)).fetchone()
    if existing:
        conn.close()
        raise ValueError(f"Another room with number '{room_num}' already exists.")

    c.execute("""
        UPDATE classrooms SET name=?, room_number=?, room_type=?, capacity=?,
            floor_number=?, building=?, has_projector=?, has_ac=?, is_available=?
        WHERE id=?
    """, (
        data['name'].strip(), room_num, data.get('room_type', 'classroom'),
        int(data.get('capacity', 60) or 60),
        int(data.get('floor_number', 0) or 0),
        data.get('building', 'Main Academic Block'),
        1 if data.get('has_projector', True) else 0,
        1 if data.get('has_ac', False) else 0,
        1 if data.get('is_available', True) else 0,
        room_id
    ))
    conn.commit()
    conn.close()

def delete_classroom(room_id):
    conn = get_db()
    conn.execute("DELETE FROM classrooms WHERE id = ?", (room_id,))
    conn.commit()
    conn.close()


# ═════════════════════════════════════════════════════════
# CRUD HELPERS — TEACHERS / FACULTY (REQUIREMENT 2B)
# ═════════════════════════════════════════════════════════
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def get_teachers(include_inactive=False):
    """Retrieve all teachers with multi-subject assignments and workload."""
    conn = get_db()
    query = """
        SELECT t.*, d.name as dept_name, d.code as dept_code
        FROM teachers t
        LEFT JOIN departments d ON t.department_id = d.id
    """
    if not include_inactive:
        query += " WHERE t.is_active = 1"
    query += " ORDER BY t.name"

    rows = conn.execute(query).fetchall()
    teachers = [dict_from_row(r) for r in rows]

    for t in teachers:
        assigns = conn.execute("""
            SELECT ts.*, s.name as subject_name, s.code as subject_code,
                   ay.code as year_code
            FROM teacher_subjects ts
            JOIN subjects s ON ts.subject_id = s.id
            LEFT JOIN academic_years ay ON ts.academic_year_id = ay.id
            WHERE ts.teacher_id = ?
        """, (t['id'],)).fetchall()
        t['assignments'] = [dict_from_row(a) for a in assigns]
        t['total_hours'] = sum(a['theory_hours'] + a['practical_hours'] for a in assigns)

    conn.close()
    return teachers

def get_teacher(teacher_id):
    conn = get_db()
    row = conn.execute("""
        SELECT t.*, d.name as dept_name, d.code as dept_code
        FROM teachers t
        LEFT JOIN departments d ON t.department_id = d.id
        WHERE t.id = ?
    """, (teacher_id,)).fetchone()
    teacher = dict_from_row(row) if row else None
    if teacher:
        assigns = conn.execute("""
            SELECT ts.*, s.name as subject_name, s.code as subject_code,
                   ay.code as year_code
            FROM teacher_subjects ts
            JOIN subjects s ON ts.subject_id = s.id
            LEFT JOIN academic_years ay ON ts.academic_year_id = ay.id
            WHERE ts.teacher_id = ?
        """, (teacher_id,)).fetchall()
        teacher['assignments'] = [dict_from_row(a) for a in assigns]
        teacher['total_hours'] = sum(a['theory_hours'] + a['practical_hours'] for a in assigns)
    conn.close()
    return teacher

def add_teacher(data):
    """Add a new faculty member with validation and multi-subject assignments."""
    conn = get_db()
    c = conn.cursor()

    name = data.get('name', '').strip()
    initials = data.get('initials', '').strip().upper()
    email = data.get('email', '').strip()
    faculty_id = data.get('faculty_id', '').strip().upper()

    if not name:
        conn.close()
        raise ValueError("Faculty name is required.")
    if not initials:
        conn.close()
        raise ValueError("Faculty initials/short code are required.")

    # Validate email format if provided
    if email and not EMAIL_REGEX.match(email):
        conn.close()
        raise ValueError(f"Invalid email format: '{email}'.")

    # Check duplicate initials or faculty_id
    if faculty_id:
        existing_fid = c.execute("SELECT id FROM teachers WHERE faculty_id = ? AND is_active = 1", (faculty_id,)).fetchone()
        if existing_fid:
            conn.close()
            raise ValueError(f"Faculty with ID '{faculty_id}' already exists.")

    existing_inits = c.execute("SELECT id FROM teachers WHERE initials = ? AND is_active = 1", (initials,)).fetchone()
    if existing_inits:
        conn.close()
        raise ValueError(f"Faculty member with initials '{initials}' already exists.")

    c.execute("""
        INSERT INTO teachers (faculty_id, name, initials, email, phone, department_id,
            designation, time_slot, max_hours_per_day, max_hours_per_week,
            max_consecutive_lectures, unavailable_slots, assigned_divisions, notes, is_demo)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
    """, (
        faculty_id or f"FAC-{initials}",
        name,
        initials,
        email,
        data.get('phone', '').strip(),
        data.get('department_id', 1),
        data.get('designation', 'Assistant Professor'),
        data.get('time_slot', 'C'),
        int(data.get('max_hours_per_day', 6) or 6),
        int(data.get('max_hours_per_week', 24) or 24),
        int(data.get('max_consecutive_lectures', 3) or 3),
        data.get('unavailable_slots', ''),
        data.get('assigned_divisions', ''),
        data.get('notes', ''),
    ))
    teacher_id = c.lastrowid

    # Add subject assignments
    for assign in data.get('assignments', []):
        sub_id = assign.get('subject_id')
        th = int(assign.get('theory_hours', 0) or 0)
        pt = int(assign.get('practical_hours', 0) or 0)
        if sub_id and (th > 0 or pt > 0):
            c.execute("""
                INSERT INTO teacher_subjects (teacher_id, subject_id,
                    academic_year_id, theory_hours, practical_hours, lab_room, is_demo)
                VALUES (?,?,?,?,?,?,0)
            """, (
                teacher_id, sub_id,
                assign.get('academic_year_id'),
                th, pt,
                assign.get('lab_room', '')
            ))

    conn.commit()
    conn.close()
    return teacher_id

def update_teacher(teacher_id, data):
    """Update teacher details and re-link assignments."""
    conn = get_db()
    c = conn.cursor()

    name = data.get('name', '').strip()
    initials = data.get('initials', '').strip().upper()
    email = data.get('email', '').strip()
    faculty_id = data.get('faculty_id', '').strip().upper()

    if not name:
        conn.close()
        raise ValueError("Faculty name is required.")
    if not initials:
        conn.close()
        raise ValueError("Faculty initials are required.")

    if email and not EMAIL_REGEX.match(email):
        conn.close()
        raise ValueError(f"Invalid email format: '{email}'.")

    # Check duplicates
    if faculty_id:
        existing_fid = c.execute("SELECT id FROM teachers WHERE faculty_id = ? AND id != ? AND is_active = 1",
                                 (faculty_id, teacher_id)).fetchone()
        if existing_fid:
            conn.close()
            raise ValueError(f"Another faculty member already has ID '{faculty_id}'.")

    existing_inits = c.execute("SELECT id FROM teachers WHERE initials = ? AND id != ? AND is_active = 1",
                              (initials, teacher_id)).fetchone()
    if existing_inits:
        conn.close()
        raise ValueError(f"Another faculty member already has initials '{initials}'.")

    c.execute("""
        UPDATE teachers SET faculty_id=?, name=?, initials=?, email=?, phone=?,
            department_id=?, designation=?, time_slot=?,
            max_hours_per_day=?, max_hours_per_week=?,
            max_consecutive_lectures=?, unavailable_slots=?, assigned_divisions=?, notes=?
        WHERE id=?
    """, (
        faculty_id or f"FAC-{initials}",
        name, initials, email,
        data.get('phone', '').strip(),
        data.get('department_id', 1),
        data.get('designation', 'Assistant Professor'),
        data.get('time_slot', 'C'),
        int(data.get('max_hours_per_day', 6) or 6),
        int(data.get('max_hours_per_week', 24) or 24),
        int(data.get('max_consecutive_lectures', 3) or 3),
        data.get('unavailable_slots', ''),
        data.get('assigned_divisions', ''),
        data.get('notes', ''),
        teacher_id
    ))

    # Rebuild assignments
    c.execute("DELETE FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,))
    for assign in data.get('assignments', []):
        sub_id = assign.get('subject_id')
        th = int(assign.get('theory_hours', 0) or 0)
        pt = int(assign.get('practical_hours', 0) or 0)
        if sub_id and (th > 0 or pt > 0):
            c.execute("""
                INSERT INTO teacher_subjects (teacher_id, subject_id,
                    academic_year_id, theory_hours, practical_hours, lab_room, is_demo)
                VALUES (?,?,?,?,?,?,0)
            """, (
                teacher_id, sub_id,
                assign.get('academic_year_id'),
                th, pt,
                assign.get('lab_room', '')
            ))

    conn.commit()
    conn.close()

def check_teacher_assignments(teacher_id):
    """
    Check if a teacher has active assignments or assigned timetable lectures.
    Used for safe deletion warning.
    """
    conn = get_db()
    c = conn.cursor()
    t = c.execute("SELECT initials, name FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
    if not t:
        conn.close()
        return {'exists': False}

    assigns = c.execute("""
        SELECT s.name as subject_name, ts.theory_hours, ts.practical_hours
        FROM teacher_subjects ts
        JOIN subjects s ON ts.subject_id = s.id
        WHERE ts.teacher_id = ?
    """, (teacher_id,)).fetchall()

    conn.close()
    return {
        'exists': True,
        'initials': t['initials'],
        'name': t['name'],
        'assigned_subjects_count': len(assigns),
        'subjects': [dict_from_row(a) for a in assigns]
    }

def delete_teacher(teacher_id, force=False):
    """
    Safely delete or soft-delete a teacher.
    If force=True, removes subject assignments and marks inactive.
    """
    conn = get_db()
    c = conn.cursor()
    if force:
        c.execute("DELETE FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,))
        c.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))
    else:
        c.execute("UPDATE teachers SET is_active = 0 WHERE id = ?", (teacher_id,))
    conn.commit()
    conn.close()


# ═════════════════════════════════════════════════════════
# TIME SLOTS & WORKING DAYS
# ═════════════════════════════════════════════════════════
def get_time_slots():
    conn = get_db()
    rows = conn.execute("SELECT * FROM time_slots ORDER BY slot_number").fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def update_time_slot(slot_id, data):
    conn = get_db()
    conn.execute("""
        UPDATE time_slots SET start_time=?, end_time=?, slot_type=?, is_active=?
        WHERE id=?
    """, (data['start_time'], data['end_time'], data.get('slot_type', 'regular'),
          1 if data.get('is_active', True) else 0, slot_id))
    conn.commit()
    conn.close()

def get_working_days():
    conn = get_db()
    rows = conn.execute("SELECT * FROM working_days ORDER BY day_number").fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def update_working_day(day_id, is_working):
    conn = get_db()
    conn.execute("UPDATE working_days SET is_working = ? WHERE id = ?", (1 if is_working else 0, day_id))
    conn.commit()
    conn.close()


# ═════════════════════════════════════════════════════════
# HOLIDAYS & ACADEMIC CALENDAR
# ═════════════════════════════════════════════════════════
def get_holidays():
    conn = get_db()
    rows = conn.execute("SELECT * FROM holidays ORDER BY date").fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def add_holiday(data):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO holidays (name, date, holiday_type, description, is_demo) VALUES (?,?,?,?,0)",
              (data['name'].strip(), data['date'].strip(), data.get('holiday_type', 'public'), data.get('description', '').strip()))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def delete_holiday(holiday_id):
    conn = get_db()
    conn.execute("DELETE FROM holidays WHERE id = ?", (holiday_id,))
    conn.commit()
    conn.close()


# ═════════════════════════════════════════════════════════
# TIMETABLE PERSISTENCE & VERSION HISTORY
# ═════════════════════════════════════════════════════════
def get_saved_timetables():
    conn = get_db()
    rows = conn.execute("""
        SELECT id, name, academic_year_code, conflicts_count, is_published, is_demo, generated_at
        FROM timetables ORDER BY generated_at DESC
    """).fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def get_timetable(tt_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM timetables WHERE id = ?", (tt_id,)).fetchone()
    conn.close()
    if row:
        d = dict_from_row(row)
        try:
            d['timetable_data'] = json.loads(d['timetable_data'])
        except Exception:
            pass
        return d
    return None

def get_latest_timetable():
    conn = get_db()
    row = conn.execute("SELECT * FROM timetables ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if row:
        d = dict_from_row(row)
        try:
            d['timetable_data'] = json.loads(d['timetable_data'])
        except Exception:
            pass
        return d
    return None

def save_timetable(name, year_code, data, conflicts=0, is_published=0, is_demo=0):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO timetables (name, academic_year_code, timetable_data, conflicts_count, is_published, is_demo)
        VALUES (?,?,?,?,?,?)
    """, (name, year_code, json.dumps(data), conflicts, is_published, is_demo))
    tt_id = c.lastrowid
    conn.commit()
    conn.close()
    return tt_id

def delete_timetable(tt_id):
    conn = get_db()
    conn.execute("DELETE FROM timetables WHERE id = ?", (tt_id,))
    conn.commit()
    conn.close()

def save_timetable_version(name, year_code, data, conflicts=0, status='Draft', change_summary='', created_by='Academic Administrator', is_demo=0):
    conn = get_db()
    c = conn.cursor()
    row = c.execute("SELECT COALESCE(MAX(version_number), 0) + 1 FROM timetable_versions WHERE academic_year_code = ?", (year_code,)).fetchone()
    v_num = row[0] if row else 1

    c.execute("""
        INSERT INTO timetable_versions (version_number, name, academic_year_code, status, change_summary, created_by, timetable_data, conflicts_count, is_demo)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (v_num, name, year_code, status, change_summary, created_by, json.dumps(data), conflicts, is_demo))
    v_id = c.lastrowid
    conn.commit()
    conn.close()
    return v_id, v_num

def get_timetable_versions(academic_year_code=None):
    conn = get_db()
    if academic_year_code and academic_year_code != 'ALL':
        rows = conn.execute("""
            SELECT id, version_number, name, academic_year_code, status, change_summary, created_by, conflicts_count, created_at, is_demo
            FROM timetable_versions WHERE academic_year_code = ?
            ORDER BY id DESC
        """, (academic_year_code,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, version_number, name, academic_year_code, status, change_summary, created_by, conflicts_count, created_at, is_demo
            FROM timetable_versions
            ORDER BY id DESC
        """).fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def get_timetable_version(version_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM timetable_versions WHERE id = ?", (version_id,)).fetchone()
    conn.close()
    if row:
        d = dict_from_row(row)
        try:
            d['timetable_data'] = json.loads(d['timetable_data'])
        except Exception:
            pass
        return d
    return None

def publish_timetable_version(version_id):
    conn = get_db()
    conn.execute("UPDATE timetable_versions SET status = 'Published' WHERE id = ?", (version_id,))
    conn.commit()
    conn.close()


# ═════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═════════════════════════════════════════════════════════
def get_notifications(limit=30, unread_only=False):
    conn = get_db()
    if unread_only:
        rows = conn.execute("SELECT * FROM notifications WHERE is_read = 0 ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def add_notification(title, message, category='system', link='', is_demo=0):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO notifications (title, message, category, link, is_demo) VALUES (?,?,?,?,?)",
              (title, message, category, link, is_demo))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def mark_notification_read(notif_id):
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))
    conn.commit()
    conn.close()

def mark_all_notifications_read():
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read = 1")
    conn.commit()
    conn.close()


# ═════════════════════════════════════════════════════════
# SETTINGS
# ═════════════════════════════════════════════════════════
def get_settings():
    conn = get_db()
    rows = conn.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}

def update_setting(key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def update_settings_bulk(data):
    conn = get_db()
    for k, v in data.items():
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))
    conn.commit()
    conn.close()


# ═════════════════════════════════════════════════════════
# DASHBOARD STATS
# ═════════════════════════════════════════════════════════
def get_dashboard_stats():
    conn = get_db()
    stats = {}
    stats['total_teachers'] = conn.execute("SELECT COUNT(*) FROM teachers WHERE is_active=1").fetchone()[0]
    stats['total_subjects'] = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
    stats['total_classrooms'] = conn.execute("SELECT COUNT(*) FROM classrooms WHERE is_available=1").fetchone()[0]
    stats['total_timetables'] = conn.execute("SELECT COUNT(*) FROM timetables").fetchone()[0]
    stats['total_versions'] = conn.execute("SELECT COUNT(*) FROM timetable_versions").fetchone()[0]
    stats['total_departments'] = conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
    stats['total_divisions'] = conn.execute("SELECT COUNT(*) FROM divisions").fetchone()[0]
    stats['total_holidays'] = conn.execute("SELECT COUNT(*) FROM holidays").fetchone()[0]
    stats['unread_notifications'] = conn.execute("SELECT COUNT(*) FROM notifications WHERE is_read=0").fetchone()[0]

    # Hours breakdown
    stats['total_theory_hours'] = conn.execute(
        "SELECT COALESCE(SUM(theory_hours), 0) FROM teacher_subjects").fetchone()[0]
    stats['total_practical_hours'] = conn.execute(
        "SELECT COALESCE(SUM(practical_hours), 0) FROM teacher_subjects").fetchone()[0]

    # Per-year subject counts
    for code in ['SE', 'TE', 'BE']:
        stats[f'{code.lower()}_subjects'] = conn.execute("""
            SELECT COUNT(*) FROM subjects s
            JOIN academic_years ay ON s.academic_year_id = ay.id
            WHERE ay.code = ?
        """, (code,)).fetchone()[0]

    # Recent timetables
    recent = conn.execute("""
        SELECT name, academic_year_code, generated_at, conflicts_count, is_published
        FROM timetables ORDER BY generated_at DESC LIMIT 5
    """).fetchall()
    stats['recent_timetables'] = [dict_from_row(r) for r in recent]

    # Teacher workload distribution
    workload = conn.execute("""
        SELECT t.id, t.initials, t.name, t.designation,
            COALESCE(SUM(ts.theory_hours), 0) as theory,
            COALESCE(SUM(ts.practical_hours), 0) as practical,
            (COALESCE(SUM(ts.theory_hours), 0) + COALESCE(SUM(ts.practical_hours), 0)) as total,
            t.max_hours_per_week as max_weekly
        FROM teachers t
        LEFT JOIN teacher_subjects ts ON t.id = ts.teacher_id
        WHERE t.is_active = 1
        GROUP BY t.id
        ORDER BY total DESC
        LIMIT 16
    """).fetchall()
    stats['teacher_workload'] = [dict_from_row(w) for w in workload]

    # Upcoming holidays
    now_date = datetime.now().strftime('%Y-%m-%d')
    up_holidays = conn.execute("""
        SELECT name, date, holiday_type, description
        FROM holidays WHERE date >= ? ORDER BY date ASC LIMIT 5
    """, (now_date,)).fetchall()
    if not up_holidays:
        up_holidays = conn.execute("SELECT name, date, holiday_type, description FROM holidays ORDER BY date ASC LIMIT 5").fetchall()
    stats['upcoming_holidays'] = [dict_from_row(h) for h in up_holidays]

    conn.close()
    return stats


# ═════════════════════════════════════════════════════════
# SCHEDULER DATA EXTRACTORS
# ═════════════════════════════════════════════════════════
def get_scheduling_context():
    """
    Extract complete normalized real-world entity records for the CSP scheduling engine.
    Works for any number of user-created faculty, divisions, subjects, rooms, and settings.
    """
    conn = get_db()

    # Active academic years & divisions
    years_rows = conn.execute("SELECT * FROM academic_years ORDER BY year_number").fetchall()
    years = [dict_from_row(r) for r in years_rows]

    divs_rows = conn.execute("SELECT * FROM divisions ORDER BY name").fetchall()
    divisions = [dict_from_row(r) for r in divs_rows]

    # Rooms
    rooms_rows = conn.execute("SELECT * FROM classrooms WHERE is_available = 1 ORDER BY room_type DESC, capacity DESC").fetchall()
    classrooms = [dict_from_row(r) for r in rooms_rows]

    # Subjects
    sub_rows = conn.execute("""
        SELECT s.*, ay.code as year_code
        FROM subjects s
        LEFT JOIN academic_years ay ON s.academic_year_id = ay.id
    """).fetchall()
    subjects = [dict_from_row(r) for r in sub_rows]

    # Teachers and their assignments
    t_rows = conn.execute("SELECT * FROM teachers WHERE is_active = 1").fetchall()
    teachers = [dict_from_row(r) for r in t_rows]
    for t in teachers:
        assigns = conn.execute("""
            SELECT ts.*, s.code as subject_code, s.name as subject_name, ay.code as year_code
            FROM teacher_subjects ts
            JOIN subjects s ON ts.subject_id = s.id
            LEFT JOIN academic_years ay ON ts.academic_year_id = ay.id
            WHERE ts.teacher_id = ?
        """, (t['id'],)).fetchall()
        t['assignments'] = [dict_from_row(a) for a in assigns]

    # Working days & slots
    w_rows = conn.execute("SELECT * FROM working_days WHERE is_working = 1 ORDER BY day_number").fetchall()
    working_days = [r['day_name'] for r in w_rows] or ["MON", "TUE", "WED", "THU", "FRI", "SAT"]

    s_rows = conn.execute("SELECT * FROM time_slots WHERE is_active = 1 ORDER BY slot_number").fetchall()
    time_slots = [dict_from_row(r) for r in s_rows]

    # Settings
    settings = {r['key']: r['value'] for r in conn.execute("SELECT * FROM settings").fetchall()}

    conn.close()

    return {
        'academic_years': years,
        'divisions': divisions,
        'classrooms': classrooms,
        'subjects': subjects,
        'teachers': teachers,
        'working_days': working_days,
        'time_slots': time_slots,
        'settings': settings
    }


def get_teachers_legacy_format():
    """Return teachers in the legacy format needed for backward compatibility."""
    conn = get_db()
    teachers = conn.execute("""
        SELECT t.* FROM teachers t WHERE t.is_active = 1
    """).fetchall()

    result = []
    for t in teachers:
        teacher_data = {
            'name': t['initials'],
            'timeSlot': t['time_slot'],
            'seSub': '', 'seTh': 0, 'sePt': 0, 'seLab': '',
            'teSub': '', 'teTh': 0, 'tePt': 0, 'teLab': '',
            'beSub': '', 'beTh': 0, 'bePt': 0, 'beLab': '',
        }

        assigns = conn.execute("""
            SELECT ts.*, s.code as subject_code, ay.code as year_code
            FROM teacher_subjects ts
            JOIN subjects s ON ts.subject_id = s.id
            LEFT JOIN academic_years ay ON ts.academic_year_id = ay.id
            WHERE ts.teacher_id = ?
        """, (t['id'],)).fetchall()

        for a in assigns:
            yc = a['year_code']
            if yc == 'SE':
                teacher_data['seSub'] = a['subject_code']
                teacher_data['seTh'] = a['theory_hours']
                teacher_data['sePt'] = a['practical_hours']
                teacher_data['seLab'] = a['lab_room']
            elif yc == 'TE':
                teacher_data['teSub'] = a['subject_code']
                teacher_data['teTh'] = a['theory_hours']
                teacher_data['tePt'] = a['practical_hours']
                teacher_data['teLab'] = a['lab_room']
            elif yc == 'BE':
                teacher_data['beSub'] = a['subject_code']
                teacher_data['beTh'] = a['theory_hours']
                teacher_data['bePt'] = a['practical_hours']
                teacher_data['beLab'] = a['lab_room']

        result.append(teacher_data)

    conn.close()
    return result


def bulk_import_teachers(teachers_list):
    """Import teachers from the legacy format."""
    conn = get_db()
    c = conn.cursor()
    imported = 0

    years = {}
    for row in c.execute("SELECT id, code FROM academic_years"):
        years[row['code']] = row['id']

    for t in teachers_list:
        name = t.get('name', '').strip()
        if not name:
            continue
        existing = c.execute("SELECT id FROM teachers WHERE initials = ?", (name,)).fetchone()
        if existing:
            teacher_id = existing['id']
            c.execute("DELETE FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,))
        else:
            c.execute("""
                INSERT INTO teachers (name, initials, time_slot, is_demo)
                VALUES (?, ?, ?, 0)
            """, (f"Prof. {name}", name, t.get('timeSlot', 'C')))
            teacher_id = c.lastrowid

        for year_code, sub_key, th_key, pt_key, lab_key in [
            ('SE', 'seSub', 'seTh', 'sePt', 'seLab'),
            ('TE', 'teSub', 'teTh', 'tePt', 'teLab'),
            ('BE', 'beSub', 'beTh', 'bePt', 'beLab'),
        ]:
            sub_name = t.get(sub_key, '').strip()
            th = int(t.get(th_key, 0) or 0)
            pt = int(t.get(pt_key, 0) or 0)
            lab = t.get(lab_key, '').strip()

            if sub_name and (th > 0 or pt > 0):
                sub_row = c.execute("SELECT id FROM subjects WHERE code = ? AND academic_year_id = ?",
                                    (sub_name, years.get(year_code))).fetchone()
                if sub_row:
                    sub_id = sub_row['id']
                else:
                    c.execute("""
                        INSERT INTO subjects (name, code, subject_type,
                            theory_hours_per_week, practical_hours_per_week,
                            academic_year_id, preferred_room, is_demo)
                        VALUES (?,?,?,?,?,?,?,0)
                    """, (sub_name, sub_name,
                          'practical' if th == 0 and pt > 0 else 'theory',
                          th, pt, years.get(year_code), lab))
                    sub_id = c.lastrowid

                c.execute("""
                    INSERT INTO teacher_subjects (teacher_id, subject_id,
                        academic_year_id, theory_hours, practical_hours, lab_room, is_demo)
                    VALUES (?,?,?,?,?,?,0)
                """, (teacher_id, sub_id, years.get(year_code), th, pt, lab))

        imported += 1

    conn.commit()
    conn.close()
    return imported
