"""Slotify — Automated test suite.

Tests cover faculty/subject/room/division CRUD, demo data load/erase,
timetable generation, conflict detection, manual edits, locking, exports,
and impossible-scheduling scenarios.
"""

import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module
import database
import scheduler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(tmp_db_path):
    """Create a Flask test client backed by a temp SQLite DB."""
    app_module.database.DB_PATH = tmp_db_path
    database.DB_PATH = tmp_db_path
    database.init_db()
    return app_module.app.test_client()


def _post(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def _put(client, path, payload):
    return client.put(path, data=json.dumps(payload), content_type="application/json")


def _retry(fn, times=5, delay=0.1):
    import time
    last_exc = None
    for _ in range(times):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            time.sleep(delay)
    raise last_exc


# ---------------------------------------------------------------------------
# Faculty CRUD
# ---------------------------------------------------------------------------

def test_create_and_get_faculty(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    r = _post(client, "/api/teachers", {
        "name": "Dr. Priya Sharma",
        "initials": "PS",
        "email": "p.sharma@slotify.edu",
        "designation": "Professor",
        "time_slot": "A",
        "max_hours_per_day": 6,
        "max_hours_per_week": 20,
    })
    assert r.status_code == 200, r.get_data(as_text=True)
    fid = r.get_json()["id"]

    r = client.get(f"/api/teachers/{fid}")
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["name"] == "Dr. Priya Sharma"
    assert data["initials"] == "PS"

    r = client.get("/api/teachers")
    assert r.status_code == 200
    assert any(t["initials"] == "PS" for t in r.get_json()["data"])


def test_create_duplicate_initials_rejected(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    _post(client, "/api/teachers", {"name": "Alice", "initials": "AA"})
    r = _post(client, "/api/teachers", {"name": "Bob", "initials": "AA"})
    assert r.status_code == 400


def test_create_invalid_email_rejected(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    r = _post(client, "/api/teachers", {"name": "Alice", "initials": "AA", "email": "not-an-email"})
    assert r.status_code == 400


def test_update_faculty(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    r = _post(client, "/api/teachers", {"name": "Alice", "initials": "AA"})
    fid = r.get_json()["id"]

    r = _put(client, f"/api/teachers/{fid}", {"name": "Alice Updated", "initials": "AX"})
    assert r.status_code == 200, r.get_data(as_text=True)

    r = client.get(f"/api/teachers/{fid}")
    assert r.get_json()["data"]["name"] == "Alice Updated"


def test_delete_faculty(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    r = _post(client, "/api/teachers", {"name": "Alice", "initials": "AA"})
    fid = r.get_json()["id"]

    # Soft delete (default) — teacher becomes inactive but record remains
    r = client.delete(f"/api/teachers/{fid}")
    assert r.status_code == 200

    r = client.get(f"/api/teachers/{fid}")
    data = r.get_json()["data"]
    assert data["is_active"] == 0, "Soft-deleted teacher should be inactive"

    # Force delete removes the record entirely
    r2 = _post(client, "/api/teachers", {"name": "Bob", "initials": "BB"})
    fid2 = r2.get_json()["id"]
    r = client.delete(f"/api/teachers/{fid2}?force=1")
    assert r.status_code == 200
    r = client.get(f"/api/teachers/{fid2}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Subject CRUD
# ---------------------------------------------------------------------------

def test_create_subject_and_get(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    # Need an academic year first (use unique code to avoid conflict with seeded data)
    _post(client, "/api/academic_years", {"name": "Test Year", "code": "TY", "year_number": 2})
    ay_list = client.get("/api/academic_years").get_json()["data"]
    ay_id = ay_list[0]["id"]

    def _create_subject():
        return _post(client, "/api/subjects", {
            "name": "Test Subject",
            "code": "TS101",
            "academic_year_id": ay_id,
            "theory_hours_per_week": 3,
            "practical_hours_per_week": 2,
            "required_room_type": "laboratory",
        })
    r = _retry(_create_subject)
    assert r.status_code == 200, r.get_data(as_text=True)
    sid = r.get_json()["id"]

    r = client.get(f"/api/subjects/{sid}")
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["code"] == "TS101"
    assert data["theory_hours_per_week"] == 3


def test_duplicate_subject_code_rejected(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    _post(client, "/api/academic_years", {"name": "SE", "code": "SE", "year_number": 2})
    ay_id = client.get("/api/academic_years").get_json()["data"][0]["id"]

    _post(client, "/api/subjects", {"name": "OS", "code": "OS", "academic_year_id": ay_id})
    r = _post(client, "/api/subjects", {"name": "OS2", "code": "OS", "academic_year_id": ay_id})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Room CRUD
# ---------------------------------------------------------------------------

def test_create_room_and_list(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    r = _post(client, "/api/classrooms", {
        "name": "Classroom 101",
        "room_number": "101",
        "room_type": "classroom",
        "capacity": 60,
    })
    assert r.status_code == 200, r.get_data(as_text=True)

    r = client.get("/api/classrooms")
    assert r.status_code == 200
    rooms = r.get_json()["data"]
    assert any(r["room_number"] == "101" for r in rooms)


def test_duplicate_room_number_rejected(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    _post(client, "/api/classrooms", {"name": "R1", "room_number": "101"})
    r = _post(client, "/api/classrooms", {"name": "R2", "room_number": "101"})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Division CRUD
# ---------------------------------------------------------------------------

def test_create_division(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    _post(client, "/api/academic_years", {"name": "Test Year", "code": "TY", "year_number": 2})
    ay_id = client.get("/api/academic_years").get_json()["data"][0]["id"]

    def _create():
        return _post(client, "/api/divisions", {
            "name": "Test Div X",
            "academic_year_id": ay_id,
            "strength": 60,
            "batch_count": 3,
        })
    r = _retry(_create)
    assert r.status_code == 200, r.get_data(as_text=True)

    r = client.get("/api/divisions")
    assert r.status_code == 200
    divs = r.get_json()["data"]
    assert any(d["name"] == "Test Div X" for d in divs)


# ---------------------------------------------------------------------------
# Demo data load / erase
# ---------------------------------------------------------------------------

def test_demo_load_is_idempotent(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    r1 = _post(client, "/api/demo/load", {})
    assert r1.status_code == 200
    assert r1.get_json()["status"] == "ok"

    r2 = _post(client, "/api/demo/load", {})
    assert r2.status_code == 200
    assert r2.get_json()["already_loaded"] is True

    # Faculty count should not double
    r = client.get("/api/teachers")
    teachers = r.get_json()["data"]
    demo_count = sum(1 for t in teachers if t.get("is_demo") == 1)
    assert demo_count == 16, f"Expected 16 demo faculty, got {demo_count}"


def test_demo_erase_preserves_user_records(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    # Load demo, then add a user record
    _post(client, "/api/demo/load", {})
    _post(client, "/api/teachers", {"name": "User Faculty", "initials": "UF"})

    # Erase demo
    r = _post(client, "/api/demo/erase", {})
    assert r.status_code == 200

    # User record must survive
    r = client.get("/api/teachers")
    teachers = r.get_json()["data"]
    assert any(t["initials"] == "UF" for t in teachers), "User faculty was deleted!"
    demo_count = sum(1 for t in teachers if t.get("is_demo") == 1)
    assert demo_count == 0, f"Demo records not fully erased: {demo_count} remaining"


# ---------------------------------------------------------------------------
# Timetable generation
# ---------------------------------------------------------------------------

def test_generate_with_demo_data(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    _post(client, "/api/demo/load", {})

    r = _post(client, "/api/generate", {})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body["status"] == "ok"
    assert "data" in body
    assert "se" in body["data"]
    assert "te" in body["data"]
    assert "be" in body["data"]

    # No hard errors
    hard = [c for c in body["conflicts"] if c.get("severity") == "error"]
    assert len(hard) == 0, f"Hard conflicts found: {hard}"


def test_generate_requires_faculty(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    # Erase the auto-seeded demo data so no faculty exist
    _post(client, "/api/demo/erase", {})

    r = _post(client, "/api/generate", {})
    assert r.status_code == 400, r.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def test_conflict_detection_on_manual_double_booking(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    _post(client, "/api/demo/load", {})
    _post(client, "/api/generate", {})

    # Fetch current timetable
    r = client.get("/api/timetables/current")
    tt = r.get_json()["data"]

    # Manually create a conflict: assign same teacher to two divisions in same slot
    # SE, slot 0, MON
    se_slot = tt["se"][0]["slots"][0]
    teacher = se_slot["teacher"]
    room = se_slot["room"]

    # Override TE slot with same teacher + room
    te_slot = tt["te"][0]["slots"][0]
    te_slot["teacher"] = teacher
    te_slot["room"] = room
    te_slot["text"] = f"CONFLICT({teacher})"
    te_slot["subject"] = "CONFLICT"
    te_slot["isLab"] = False

    r = _post(client, "/api/timetables/validate", {"timetable_data": tt})
    assert r.status_code == 200
    conflicts = r.get_json()["conflicts"]
    hard = [c for c in conflicts if c.get("severity") == "error"]
    assert len(hard) >= 1, "Expected at least one hard conflict (teacher overlap)"


def test_recess_protection_in_conflict_detection(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    _post(client, "/api/demo/load", {})
    _post(client, "/api/generate", {})

    r = client.get("/api/timetables/current")
    tt = r.get_json()["data"]

    # Slot index 4 is recess (1:45-2:15)
    recess_slot = tt["se"][0]["slots"][4]
    recess_slot["teacher"] = "CG"
    recess_slot["subject"] = "OS"
    recess_slot["text"] = "OS(CG)"
    recess_slot["room"] = "Classroom 301"

    r = _post(client, "/api/timetables/validate", {"timetable_data": tt})
    conflicts = r.get_json()["conflicts"]
    recess_conflicts = [c for c in conflicts if c.get("type") == "recess_violation"]
    assert len(recess_conflicts) >= 1, "Expected recess violation conflict"


# ---------------------------------------------------------------------------
# Manual edit + lock
# ---------------------------------------------------------------------------

def test_update_slot_and_lock(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    _post(client, "/api/demo/load", {})
    _post(client, "/api/generate", {})

    r = _post(client, "/api/timetables/update_slot", {
        "year": "se", "day_index": 0, "slot_index": 0,
        "subject": "OS", "teacher": "CG", "room": "Classroom 301",
    })
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body["status"] == "ok"
    slot = body["updated_slot"]
    assert slot["subject"] == "OS"
    assert slot["teacher"] == "CG"

    # Lock the slot
    r = _post(client, "/api/timetables/toggle_lock", {
        "year": "se", "day_index": 0, "slot_index": 0,
    })
    assert r.status_code == 200
    assert r.get_json()["isLocked"] is True


# ---------------------------------------------------------------------------
# Save / restore version
# ---------------------------------------------------------------------------

def test_save_and_restore_version(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    _post(client, "/api/demo/load", {})
    _post(client, "/api/generate", {})

    r = _post(client, "/api/timetables/save", {
        "name": "Test Version", "status": "Draft", "summary": "Test save",
    })
    assert r.status_code == 200
    vid = r.get_json()["version_id"]

    r = client.get(f"/api/timetables/versions")
    versions = r.get_json()["data"]
    assert any(v["id"] == vid for v in versions)

    r = _post(client, f"/api/timetables/restore/{vid}", {})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def test_export_pdf(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    _post(client, "/api/demo/load", {})
    _post(client, "/api/generate", {})

    r = client.get("/api/export/pdf/year/se")
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/pdf"
    assert r.data.startswith(b"%PDF")


def test_export_csv(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    _post(client, "/api/demo/load", {})
    _post(client, "/api/generate", {})

    r = client.get("/api/export/csv/year/se")
    assert r.status_code == 200
    assert "text/csv" in r.headers["Content-Type"]


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def test_get_and_update_settings(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    r = client.get("/api/settings")
    assert r.status_code == 200
    settings = r.get_json()["data"]
    assert "institution_name" in settings

    r = _post(client, "/api/settings", {"institution_name": "Test College"})
    assert r.status_code == 200

    r = client.get("/api/settings")
    assert r.get_json()["data"]["institution_name"] == "Test College"


# ---------------------------------------------------------------------------
# Scheduler unit tests
# ---------------------------------------------------------------------------

def test_build_empty_timetable_has_recess():
    grid = scheduler.build_empty_timetable()
    assert len(grid) == 6  # 6 days
    recess_found = False
    for row in grid:
        for slot in row["slots"]:
            if slot.get("isRecess"):
                recess_found = True
                assert slot["isLocked"] is True
                assert slot["text"] == "RECESS / LUNCH"
    assert recess_found


def test_detect_conflicts_empty():
    conflicts = scheduler.detect_conflicts(None)
    assert conflicts == []
    conflicts = scheduler.detect_conflicts({})
    assert conflicts == []


def test_generate_schedules_legacy_no_teachers():
    data, conflicts = scheduler.generate_schedules([])
    assert data is None
    assert "No faculty" in conflicts[0]


# ---------------------------------------------------------------------------
# Impossible scheduling scenario
# ---------------------------------------------------------------------------

def test_generation_reports_unassigned_when_impossible(tmp_path):
    """If workload caps are too tight, generator should report diagnostics rather than silently omit."""
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    # Load demo then artificially cap faculty weekly hours to 1 to force unassigned
    _post(client, "/api/demo/load", {})
    teachers = client.get("/api/teachers").get_json()["data"]
    for t in teachers:
        _post(client, f"/api/teachers/{t['id']}", {
            "name": t["name"],
            "initials": t["initials"],
            "email": t.get("email", ""),
            "max_hours_per_week": 1,
            "max_hours_per_day": 1,
        })

    r = _post(client, "/api/generate", {})
    assert r.status_code == 200
    body = r.get_json()
    diag = body["data"].get("unassigned_diagnostics", [])
    assert len(diag) > 0, "Expected unassigned diagnostics when constraints are impossible"


# ---------------------------------------------------------------------------
# Interactive Workflow & Demo Preload Tests (Requirements 2-10)
# ---------------------------------------------------------------------------

def test_workflow_config_and_preload(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    # Preload demo data
    r = _post(client, "/api/demo/preload", {})
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    data = body["data"]

    # Verify structured configuration for 7-step wizard
    assert "academic_setup" in data
    assert data["academic_setup"]["college_name"] == "Slotify Institute of Technology"
    assert len(data["classes"]) >= 3
    assert len(data["subjects"]) >= 16
    assert len(data["faculty"]) >= 16
    assert len(data["classrooms"]) >= 11
    assert data["preferences"]["hard_faculty_no_overlap"] is True


def test_workflow_generate_produces_verified_schedule(tmp_path):
    db = tmp_path / "test.db"
    client = _make_app(str(db))

    # Preload demo data into workflow
    _post(client, "/api/demo/preload", {})

    # Generate timetable from workflow
    payload = {
        "academic_setup": {
            "college_name": "Slotify Institute of Technology",
            "department": "Computer Science & Engineering",
            "theory_duration": 60,
            "practical_duration": 120,
            "lunch_break_time": "13:45",
            "lunch_break_duration": 30
        }
    }
    r = _post(client, "/api/workflow/generate", payload)
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert body["summary"]["hard_errors"] == 0
    assert body["summary"]["total_sessions"] > 0

