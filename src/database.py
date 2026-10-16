"""
Slotify 🗓️ — Database Module
SQLite-based persistent storage for the college timetable management platform.
Supports multi-department, academic years, divisions, subjects, classrooms, labs,
teachers with multiple subjects, time slots, recesses, holidays, version history,
notifications, and system settings.
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'slotify.db')


def get_db():
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def dict_from_row(row):
    """Convert a sqlite3.Row to a dict."""
    if row is None:
        return None
    return dict(row)


def init_db():
    """Initialize the database with all required tables and default data."""
    conn = get_db()
    c = conn.cursor()

    # ── Departments ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            hod_name TEXT DEFAULT '',
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
            FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE
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
            building TEXT DEFAULT 'Main',
            has_projector BOOLEAN DEFAULT 1,
            has_ac BOOLEAN DEFAULT 0,
            is_available BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Teachers ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            initials TEXT NOT NULL,
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            department_id INTEGER DEFAULT 1,
            designation TEXT DEFAULT 'Assistant Professor',
            time_slot TEXT DEFAULT 'C',
            max_hours_per_day INTEGER DEFAULT 6,
            max_hours_per_week INTEGER DEFAULT 24,
            is_active BOOLEAN DEFAULT 1,
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
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    # ── Working Days ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS working_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_name TEXT NOT NULL UNIQUE,
            day_number INTEGER NOT NULL UNIQUE,
            is_working BOOLEAN DEFAULT 1
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Generated Timetables (saved as JSON snapshots) ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS timetables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            academic_year_code TEXT NOT NULL,
            timetable_data TEXT NOT NULL,
            conflicts_count INTEGER DEFAULT 0,
            is_published BOOLEAN DEFAULT 0,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Timetable Versions & Approvals ──
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

    # ── Insert default data ──
    _seed_defaults(c)

    conn.commit()
    conn.close()


def _seed_defaults(c):
    """Seed default configuration data if tables are empty."""

    # 1. Department
    c.execute("SELECT COUNT(*) FROM departments")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO departments (name, code, hod_name) VALUES (?, ?, ?)",
                  ("Computer Engineering", "CE", "Dr. Rajesh Sharma"))
        c.execute("INSERT INTO departments (name, code, hod_name) VALUES (?, ?, ?)",
                  ("Information Technology", "IT", "Dr. Sunita Kulkarni"))
        c.execute("INSERT INTO departments (name, code, hod_name) VALUES (?, ?, ?)",
                  ("AI & Data Science", "AIDS", "Dr. Manoj Patel"))

    # 2. Academic Years
    c.execute("SELECT COUNT(*) FROM academic_years")
    if c.fetchone()[0] == 0:
        for name, code, num in [
            ("SE — Second Year", "SE", 2),
            ("TE — Third Year", "TE", 3),
            ("BE — Final Year", "BE", 4)
        ]:
            c.execute("INSERT INTO academic_years (name, code, year_number) VALUES (?, ?, ?)",
                      (name, code, num))

    # 3. Divisions
    c.execute("SELECT COUNT(*) FROM divisions")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO divisions (name, academic_year_id, strength) VALUES ('Div A', 1, 65)")
        c.execute("INSERT INTO divisions (name, academic_year_id, strength) VALUES ('Div B', 1, 60)")
        c.execute("INSERT INTO divisions (name, academic_year_id, strength) VALUES ('Div A', 2, 65)")
        c.execute("INSERT INTO divisions (name, academic_year_id, strength) VALUES ('Div A', 3, 62)")

    # 4. Classrooms & Labs
    c.execute("SELECT COUNT(*) FROM classrooms")
    if c.fetchone()[0] == 0:
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
            c.execute("""
                INSERT INTO classrooms (name, room_number, room_type, capacity, floor_number, building, has_projector, has_ac)
                VALUES (?,?,?,?,?,?,?,?)
            """, r)

    # 5. Time Slots (Period 1 to 7, including official Recess)
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
            c.execute("INSERT INTO time_slots (slot_number, start_time, end_time, slot_type) VALUES (?,?,?,?)", s)

    # 6. Working Days
    c.execute("SELECT COUNT(*) FROM working_days")
    if c.fetchone()[0] == 0:
        for day, num, working in [
            ("MON", 1, 1), ("TUE", 2, 1), ("WED", 3, 1),
            ("THU", 4, 1), ("FRI", 5, 1), ("SAT", 6, 1)
        ]:
            c.execute("INSERT INTO working_days (day_name, day_number, is_working) VALUES (?,?,?)",
                      (day, num, working))

    # 7. Holidays (2026-2027 Academic Year Official Calendar)
    c.execute("SELECT COUNT(*) FROM holidays")
    if c.fetchone()[0] == 0:
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
            c.execute("INSERT INTO holidays (name, date, holiday_type, description) VALUES (?,?,?,?)", h)

    # 8. Settings
    c.execute("SELECT COUNT(*) FROM settings")
    if c.fetchone()[0] == 0:
        defaults = {
            'institution_name': 'Slotify Institute of Technology',
            'academic_session': '2026–2027',
            'semester': 'Odd Semester (Term I)',
            'max_lectures_per_day': '6',
            'allow_saturday': '1',
            'recess_start': '1:45',
            'recess_end': '2:15',
            'active_department': 'Computer Engineering'
        }
        for k, v in defaults.items():
            c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (k, v))

    # 9. Seed Default Faculty & Subjects if empty
    c.execute("SELECT COUNT(*) FROM teachers")
    if c.fetchone()[0] == 0:
        _seed_faculty_and_curriculum(c)

    # 10. Seed Initial Notifications
    c.execute("SELECT COUNT(*) FROM notifications")
    if c.fetchone()[0] == 0:
        notifs = [
            ("Welcome to Slotify 🗓️", "Smart College Timetable Management & Scheduling Platform is ready.", "system", ""),
            ("Academic Calendar Loaded", "Official 2026-2027 holiday schedule and examination dates configured.", "holiday", "#calendar"),
            ("Classrooms & Labs Verified", "5 smart lecture halls and 6 high-capacity labs mapped for allocation.", "room_change", "#classrooms"),
            ("Faculty Directory Active", "16 departmental faculty profiles linked with weekly teaching qualifications.", "system", "#faculty"),
        ]
        for n in notifs:
            c.execute("INSERT INTO notifications (title, message, category, link) VALUES (?,?,?,?)", n)


def _seed_faculty_and_curriculum(c):
    """Seed comprehensive faculty, subjects, and assignments."""
    # Lookup year IDs
    ay_map = {}
    for r in c.execute("SELECT id, code FROM academic_years"):
        ay_map[r['code']] = r['id']

    # Subjects for SE, TE, BE
    subjects_seed = [
        # SE Subjects
        ("Operating Systems", "OS", "theory", 3, 2, 0, 4, ay_map.get('SE', 1), "704"),
        ("Microprocessor Architecture", "MP", "theory", 3, 2, 0, 4, ay_map.get('SE', 1), "701"),
        ("Database Management Systems", "DBMS", "theory", 3, 2, 0, 4, ay_map.get('SE', 1), "LL"),
        ("Analysis of Algorithms", "AOA", "theory", 3, 2, 0, 4, ay_map.get('SE', 1), "702"),
        ("Python Programming Lab", "PYTHON", "practical", 2, 2, 0, 3, ay_map.get('SE', 1), "501"),
        ("Engineering Mathematics IV", "EM4", "theory", 3, 0, 0, 3, ay_map.get('SE', 1), "301"),
        
        # TE Subjects
        ("System Programming & Compiler Construction", "SPCC", "theory", 3, 2, 0, 4, ay_map.get('TE', 2), "704"),
        ("Artificial Intelligence", "AI", "theory", 3, 2, 0, 4, ay_map.get('TE', 2), "501"),
        ("Cryptography & Network Security", "CNSS", "theory", 3, 2, 0, 4, ay_map.get('TE', 2), "108"),
        ("Mobile Computing", "MC", "theory", 3, 2, 0, 4, ay_map.get('TE', 2), "704"),
        ("Internet of Things", "IOT", "theory", 3, 0, 0, 3, ay_map.get('TE', 2), "302"),
        ("Cloud Computing Lab", "CC", "practical", 0, 2, 0, 2, ay_map.get('TE', 2), "501"),

        # BE Subjects
        ("Human Machine Interaction", "HMI", "theory", 4, 2, 0, 4, ay_map.get('BE', 3), "702"),
        ("Engineering Management", "EM", "theory", 3, 0, 0, 3, ay_map.get('BE', 3), "401"),
        ("Ad-hoc Wireless Networks", "AWN", "theory", 4, 2, 0, 4, ay_map.get('BE', 3), "501"),
        ("Distributed Computing", "DC", "theory", 4, 2, 0, 4, ay_map.get('BE', 3), "701"),
    ]

    sub_id_map = {}
    for s in subjects_seed:
        c.execute("""
            INSERT INTO subjects (name, code, subject_type, theory_hours_per_week, practical_hours_per_week,
                                  tutorial_hours_per_week, credits, academic_year_id, preferred_room)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, s)
        sub_id_map[(s[1], s[7])] = c.lastrowid

    # 16 Faculty Members with realistic academic details and multi-subject mappings
    faculty_seed = [
        ("Prof. Chandan Gaikwad", "CG", "c.gaikwad@slotify.edu", "Associate Professor", "C", 6, 20, [
            ('OS', 'SE', 3, 2, '704')
        ]),
        ("Prof. Niharika More", "NM", "n.more@slotify.edu", "Assistant Professor", "A", 6, 18, [
            ('MP', 'SE', 3, 2, '701')
        ]),
        ("Dr. Ashish Gupta", "AG", "a.gupta@slotify.edu", "Professor", "C", 6, 20, [
            ('DBMS', 'SE', 3, 2, 'LL')
        ]),
        ("Prof. Deepa Raut", "DR", "d.raut@slotify.edu", "Assistant Professor", "B", 6, 18, [
            ('AOA', 'SE', 3, 2, '702')
        ]),
        ("Prof. Amit Sharma", "AS", "a.sharma@slotify.edu", "Assistant Professor", "C", 6, 18, [
            ('PYTHON', 'SE', 2, 2, '501')
        ]),
        ("Prof. Anjali Joshi", "AJ", "a.joshi@slotify.edu", "Assistant Professor", "D", 6, 16, [
            ('EM4', 'SE', 3, 0, '301')
        ]),
        ("Prof. Rajesh Jadhav", "RJ", "r.jadhav@slotify.edu", "Associate Professor", "A", 6, 20, [
            ('SPCC', 'TE', 3, 2, '704')
        ]),
        ("Dr. Nupur Varma", "NV", "n.varma@slotify.edu", "Associate Professor", "C", 6, 20, [
            ('AI', 'TE', 3, 2, '501')
        ]),
        ("Prof. Umesh Agrawal", "UA", "u.agrawal@slotify.edu", "Assistant Professor", "C", 6, 18, [
            ('CNSS', 'TE', 3, 2, '108')
        ]),
        ("Prof. Rashmi Shah", "RS", "r.shah@slotify.edu", "Assistant Professor", "C", 6, 18, [
            ('MC', 'TE', 3, 2, '704')
        ]),
        ("Dr. Devendra N. Roy", "DNR", "d.roy@slotify.edu", "Professor", "A", 6, 16, [
            ('IOT', 'TE', 3, 0, '302')
        ]),
        ("Prof. Meena N. Rao", "MNR", "m.rao@slotify.edu", "Assistant Professor", "C", 6, 16, [
            ('CC', 'TE', 0, 2, '501')
        ]),
        ("Prof. Sanjay Singh", "SS", "s.singh@slotify.edu", "Associate Professor", "A", 6, 22, [
            ('HMI', 'BE', 4, 2, '702')
        ]),
        ("Prof. Vikas Joshi", "VJ", "v.joshi@slotify.edu", "Assistant Professor", "C", 6, 18, [
            ('EM', 'BE', 3, 0, '401')
        ]),
        ("Prof. Tushar R. Patil", "TRP", "t.patil@slotify.edu", "Assistant Professor", "A", 6, 22, [
            ('AWN', 'BE', 4, 2, '501')
        ]),
        ("Prof. Sonal Sharma", "SS2", "s.sharma2@slotify.edu", "Assistant Professor", "B", 6, 22, [
            ('DC', 'BE', 4, 2, '701')
        ]),
    ]

    for fname, inits, email, desig, slot, max_d, max_w, assigns in faculty_seed:
        c.execute("""
            INSERT INTO teachers (name, initials, email, designation, time_slot, max_hours_per_day, max_hours_per_week)
            VALUES (?,?,?,?,?,?,?)
        """, (fname, inits, email, desig, slot, max_d, max_w))
        t_id = c.lastrowid

        for scode, ycode, th, pt, lab in assigns:
            s_id = sub_id_map.get((scode, ay_map.get(ycode)))
            if s_id:
                c.execute("""
                    INSERT INTO teacher_subjects (teacher_id, subject_id, academic_year_id, theory_hours, practical_hours, lab_room)
                    VALUES (?,?,?,?,?,?)
                """, (t_id, s_id, ay_map.get(ycode), th, pt, lab))


# ═══════════════════════════════════════════
#  CRUD HELPERS
# ═══════════════════════════════════════════

# ── Departments ──
def get_departments():
    conn = get_db()
    rows = conn.execute("SELECT * FROM departments ORDER BY id").fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def add_department(name, code, hod_name=''):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO departments (name, code, hod_name) VALUES (?,?,?)", (name, code, hod_name))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def delete_department(dept_id):
    conn = get_db()
    conn.execute("DELETE FROM departments WHERE id = ?", (dept_id,))
    conn.commit()
    conn.close()


# ── Academic Years ──
def get_academic_years():
    conn = get_db()
    rows = conn.execute("SELECT * FROM academic_years ORDER BY year_number").fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]


# ── Divisions ──
def get_divisions():
    conn = get_db()
    rows = conn.execute("""
        SELECT d.*, ay.code as year_code, ay.name as year_name
        FROM divisions d
        JOIN academic_years ay ON d.academic_year_id = ay.id
        ORDER BY ay.year_number, d.name
    """).fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def add_division(name, academic_year_id, strength=60):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO divisions (name, academic_year_id, strength) VALUES (?,?,?)",
              (name, academic_year_id, strength))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id


# ── Subjects ──
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

def add_subject(data):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO subjects (name, code, subject_type, theory_hours_per_week,
            practical_hours_per_week, tutorial_hours_per_week, credits,
            academic_year_id, is_elective, preferred_room)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        data['name'], data['code'], data.get('subject_type', 'theory'),
        data.get('theory_hours_per_week', 0), data.get('practical_hours_per_week', 0),
        data.get('tutorial_hours_per_week', 0), data.get('credits', 0),
        data.get('academic_year_id'), data.get('is_elective', 0),
        data.get('preferred_room', '')
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_subject(sub_id, data):
    conn = get_db()
    conn.execute("""
        UPDATE subjects SET name=?, code=?, subject_type=?,
            theory_hours_per_week=?, practical_hours_per_week=?,
            tutorial_hours_per_week=?, credits=?,
            academic_year_id=?, is_elective=?, preferred_room=?
        WHERE id=?
    """, (
        data['name'], data['code'], data.get('subject_type', 'theory'),
        data.get('theory_hours_per_week', 0), data.get('practical_hours_per_week', 0),
        data.get('tutorial_hours_per_week', 0), data.get('credits', 0),
        data.get('academic_year_id'), data.get('is_elective', 0),
        data.get('preferred_room', ''),
        sub_id
    ))
    conn.commit()
    conn.close()

def delete_subject(sub_id):
    conn = get_db()
    conn.execute("DELETE FROM subjects WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()


# ── Classrooms ──
def get_classrooms():
    conn = get_db()
    rows = conn.execute("SELECT * FROM classrooms ORDER BY room_type DESC, room_number").fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def add_classroom(data):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO classrooms (name, room_number, room_type, capacity,
            floor_number, building, has_projector, has_ac, is_available)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        data['name'], data['room_number'], data.get('room_type', 'classroom'),
        data.get('capacity', 60), data.get('floor_number', 0),
        data.get('building', 'Main'), data.get('has_projector', 1),
        data.get('has_ac', 0), data.get('is_available', 1)
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_classroom(room_id, data):
    conn = get_db()
    conn.execute("""
        UPDATE classrooms SET name=?, room_number=?, room_type=?, capacity=?,
            floor_number=?, building=?, has_projector=?, has_ac=?, is_available=?
        WHERE id=?
    """, (
        data['name'], data['room_number'], data.get('room_type', 'classroom'),
        data.get('capacity', 60), data.get('floor_number', 0),
        data.get('building', 'Main'), data.get('has_projector', 1),
        data.get('has_ac', 0), data.get('is_available', 1),
        room_id
    ))
    conn.commit()
    conn.close()

def delete_classroom(room_id):
    conn = get_db()
    conn.execute("DELETE FROM classrooms WHERE id = ?", (room_id,))
    conn.commit()
    conn.close()


# ── Teachers (full CRUD with multi-subject assignments) ──
def get_teachers():
    conn = get_db()
    rows = conn.execute("""
        SELECT t.*, d.name as dept_name, d.code as dept_code
        FROM teachers t
        LEFT JOIN departments d ON t.department_id = d.id
        WHERE t.is_active = 1
        ORDER BY t.name
    """).fetchall()
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
        # Calculate total allocated hours
        t['total_hours'] = sum(a['theory_hours'] + a['practical_hours'] for a in assigns)

    conn.close()
    return teachers

def get_teacher(teacher_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
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
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO teachers (name, initials, email, phone, department_id,
            designation, time_slot, max_hours_per_day, max_hours_per_week)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        data['name'], data['initials'], data.get('email', ''),
        data.get('phone', ''), data.get('department_id', 1),
        data.get('designation', 'Assistant Professor'),
        data.get('time_slot', 'C'),
        data.get('max_hours_per_day', 6), data.get('max_hours_per_week', 24)
    ))
    teacher_id = c.lastrowid

    # Add subject assignments
    for assign in data.get('assignments', []):
        if assign.get('subject_id') and (assign.get('theory_hours', 0) > 0 or assign.get('practical_hours', 0) > 0):
            c.execute("""
                INSERT INTO teacher_subjects (teacher_id, subject_id,
                    academic_year_id, theory_hours, practical_hours, lab_room)
                VALUES (?,?,?,?,?,?)
            """, (
                teacher_id, assign['subject_id'],
                assign.get('academic_year_id'),
                assign.get('theory_hours', 0), assign.get('practical_hours', 0),
                assign.get('lab_room', '')
            ))

    conn.commit()
    conn.close()
    return teacher_id

def update_teacher(teacher_id, data):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE teachers SET name=?, initials=?, email=?, phone=?,
            department_id=?, designation=?, time_slot=?,
            max_hours_per_day=?, max_hours_per_week=?
        WHERE id=?
    """, (
        data['name'], data['initials'], data.get('email', ''),
        data.get('phone', ''), data.get('department_id', 1),
        data.get('designation', 'Assistant Professor'),
        data.get('time_slot', 'C'),
        data.get('max_hours_per_day', 6), data.get('max_hours_per_week', 24),
        teacher_id
    ))

    # Rebuild assignments
    c.execute("DELETE FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,))
    for assign in data.get('assignments', []):
        if assign.get('subject_id') and (assign.get('theory_hours', 0) > 0 or assign.get('practical_hours', 0) > 0):
            c.execute("""
                INSERT INTO teacher_subjects (teacher_id, subject_id,
                    academic_year_id, theory_hours, practical_hours, lab_room)
                VALUES (?,?,?,?,?,?)
            """, (
                teacher_id, assign['subject_id'],
                assign.get('academic_year_id'),
                assign.get('theory_hours', 0), assign.get('practical_hours', 0),
                assign.get('lab_room', '')
            ))

    conn.commit()
    conn.close()

def delete_teacher(teacher_id):
    conn = get_db()
    conn.execute("UPDATE teachers SET is_active = 0 WHERE id = ?", (teacher_id,))
    conn.commit()
    conn.close()


# ── Time Slots ──
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
          data.get('is_active', 1), slot_id))
    conn.commit()
    conn.close()


# ── Working Days ──
def get_working_days():
    conn = get_db()
    rows = conn.execute("SELECT * FROM working_days ORDER BY day_number").fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def update_working_day(day_id, is_working):
    conn = get_db()
    conn.execute("UPDATE working_days SET is_working = ? WHERE id = ?", (is_working, day_id))
    conn.commit()
    conn.close()


# ── Holidays & Academic Calendar ──
def get_holidays():
    conn = get_db()
    rows = conn.execute("SELECT * FROM holidays ORDER BY date").fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def add_holiday(data):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO holidays (name, date, holiday_type, description) VALUES (?,?,?,?)",
                 (data['name'], data['date'], data.get('holiday_type', 'public'), data.get('description', '')))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def delete_holiday(holiday_id):
    conn = get_db()
    conn.execute("DELETE FROM holidays WHERE id = ?", (holiday_id,))
    conn.commit()
    conn.close()


# ── Timetables & Saved Snapshots ──
def get_saved_timetables():
    conn = get_db()
    rows = conn.execute("""
        SELECT id, name, academic_year_code, conflicts_count, is_published, generated_at
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

def save_timetable(name, year_code, data, conflicts=0, is_published=0):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO timetables (name, academic_year_code, timetable_data, conflicts_count, is_published)
        VALUES (?,?,?,?,?)
    """, (name, year_code, json.dumps(data), conflicts, is_published))
    tt_id = c.lastrowid
    conn.commit()
    conn.close()
    return tt_id

def delete_timetable(tt_id):
    conn = get_db()
    conn.execute("DELETE FROM timetables WHERE id = ?", (tt_id,))
    conn.commit()
    conn.close()


# ── Timetable Versions & Approvals ──
def save_timetable_version(name, year_code, data, conflicts=0, status='Draft', change_summary='', created_by='Academic Administrator'):
    conn = get_db()
    c = conn.cursor()
    # Get current max version number
    row = c.execute("SELECT COALESCE(MAX(version_number), 0) + 1 FROM timetable_versions WHERE academic_year_code = ?", (year_code,)).fetchone()
    v_num = row[0] if row else 1

    c.execute("""
        INSERT INTO timetable_versions (version_number, name, academic_year_code, status, change_summary, created_by, timetable_data, conflicts_count)
        VALUES (?,?,?,?,?,?,?,?)
    """, (v_num, name, year_code, status, change_summary, created_by, json.dumps(data), conflicts))
    v_id = c.lastrowid
    conn.commit()
    conn.close()
    return v_id, v_num

def get_timetable_versions(academic_year_code=None):
    conn = get_db()
    if academic_year_code and academic_year_code != 'ALL':
        rows = conn.execute("""
            SELECT id, version_number, name, academic_year_code, status, change_summary, created_by, conflicts_count, created_at
            FROM timetable_versions WHERE academic_year_code = ?
            ORDER BY id DESC
        """, (academic_year_code,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, version_number, name, academic_year_code, status, change_summary, created_by, conflicts_count, created_at
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


# ── Notifications ──
def get_notifications(limit=30, unread_only=False):
    conn = get_db()
    if unread_only:
        rows = conn.execute("SELECT * FROM notifications WHERE is_read = 0 ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def add_notification(title, message, category='system', link=''):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO notifications (title, message, category, link) VALUES (?,?,?,?)",
              (title, message, category, link))
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


# ── Settings ──
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


# ── Dashboard Stats ──
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

    # Upcoming holidays (next 5)
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


# ── Bulk import teachers (legacy format support) ──
def bulk_import_teachers(teachers_list):
    """Import teachers from the legacy frontend format."""
    conn = get_db()
    c = conn.cursor()
    imported = 0

    # Get academic year IDs
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
                INSERT INTO teachers (name, initials, time_slot)
                VALUES (?, ?, ?)
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
                            academic_year_id, preferred_room)
                        VALUES (?,?,?,?,?,?,?)
                    """, (sub_name, sub_name,
                          'practical' if th == 0 and pt > 0 else 'theory',
                          th, pt, years.get(year_code), lab))
                    sub_id = c.lastrowid

                c.execute("""
                    INSERT INTO teacher_subjects (teacher_id, subject_id,
                        academic_year_id, theory_hours, practical_hours, lab_room)
                    VALUES (?,?,?,?,?,?)
                """, (teacher_id, sub_id, years.get(year_code), th, pt, lab))

        imported += 1

    conn.commit()
    conn.close()
    return imported


def get_teachers_legacy_format():
    """Return teachers in the legacy list format needed by the generation algorithm."""
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


def reset_to_sample_data():
    """Wipe and re-seed the entire database with fresh sample data."""
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
    init_db()
    return True
