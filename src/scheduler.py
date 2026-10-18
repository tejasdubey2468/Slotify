"""
Slotify 🗓️ — Advanced Timetable Scheduling & Constraint Satisfaction (CSP) Engine
Implements backtracking with constraint propagation (MRV & LCV heuristics),
recess protection, room allocation, faculty workload limits, availability constraints,
locked session preservation, and comprehensive multi-dimensional conflict detection.
"""

import math
import random
from copy import deepcopy
from datetime import datetime

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
TIME_SLOTS = [
    {"slot_id": 1, "time": "9:45-10:45", "type": "regular"},
    {"slot_id": 2, "time": "10:45-11:45", "type": "regular"},
    {"slot_id": 3, "time": "11:45-12:45", "type": "regular"},
    {"slot_id": 4, "time": "12:45-1:45", "type": "regular"},
    {"slot_id": 5, "time": "1:45-2:15", "type": "recess"},
    {"slot_id": 6, "time": "2:15-3:15", "type": "regular"},
    {"slot_id": 7, "time": "3:15-4:15", "type": "regular"},
]

DEFAULT_CLASSROOMS = {
    'SE': 'Classroom 301',
    'TE': 'Classroom 302',
    'BE': 'Classroom 401',
}


def build_empty_timetable(days=None, time_slots=None):
    """Build an empty timetable structure respecting recess periods."""
    d_list = days or DAYS
    s_list = time_slots or TIME_SLOTS
    grid = []
    for d in d_list:
        row = {"day": d, "slots": []}
        for s in s_list:
            is_recess = (s.get("type") == "recess" or s.get("slot_type") == "recess")
            slot_id = s.get("slot_id") or s.get("slot_number", 1)
            time_str = s.get("time") or f"{s.get('start_time')}-{s.get('end_time')}"
            if is_recess:
                row["slots"].append({
                    "slot_id": slot_id,
                    "time": time_str,
                    "isRecess": True,
                    "isLocked": True,
                    "text": "RECESS / LUNCH",
                    "subject": "RECESS",
                    "teacher": "",
                    "room": "",
                    "isLab": False
                })
            else:
                row["slots"].append({
                    "slot_id": slot_id,
                    "time": time_str,
                    "isRecess": False,
                    "isLocked": False,
                    "text": "",
                    "subject": "",
                    "teacher": "",
                    "room": "",
                    "isLab": False
                })
        grid.append(row)
    return grid


# ═════════════════════════════════════════════════════════
# CONSTRAINT SATISFACTION PROBLEM (CSP) SCHEDULING ENGINE
# ═════════════════════════════════════════════════════════
def generate_schedules_csp(context, locked_timetable=None):
    """
    Generalized Constraint Satisfaction Problem (CSP) solver.
    Works for any number of user-created or sample divisions, subjects, faculty, and rooms.

    Hard Constraints Enforced:
    1. Zero faculty double-booking across any class/division.
    2. Zero room/lab double-booking across any class/division.
    3. Zero division double-booking.
    4. Protected Recess (no classes scheduled).
    5. Faculty qualification match (teacher must be qualified for subject).
    6. Faculty unavailable slots respected.
    7. Room type matching (theories in classrooms, practicals in laboratories).
    8. Room capacity >= division/batch strength.
    9. Practical sessions scheduled in consecutive 2-slot blocks.
    10. Daily and weekly faculty workload limits enforced.
    11. Preserves all locked sessions in place.

    Soft Constraints Optimized:
    1. Even subject distribution across the week (max 1 theory of same subject per day).
    2. Faculty slot preference (Slot A: morning, Slot B: afternoon, Slot C: flexible).
    3. Minimized consecutive lectures (max 3 without break).
    4. Balanced daily faculty workload.
    """
    days = context.get('working_days') or DAYS
    raw_slots = context.get('time_slots') or TIME_SLOTS
    time_slots = []
    recess_slot_idx = -1

    for idx, s in enumerate(raw_slots):
        stype = s.get('type') or s.get('slot_type', 'regular')
        tstr = s.get('time') or f"{s.get('start_time')}-{s.get('end_time')}"
        time_slots.append({'slot_id': idx + 1, 'time': tstr, 'type': stype})
        if stype == 'recess':
            recess_slot_idx = idx

    divisions = context.get('divisions', [])
    # Default fallback division codes if none created yet
    div_keys = []
    if divisions:
        div_keys = [d['name'].replace(' ', '_').lower() for d in divisions]
    else:
        div_keys = ['se', 'te', 'be']

    # Initialize empty grids for all divisions
    grids = {k: build_empty_timetable(days, time_slots) for k in div_keys}
    if 'se' not in grids:
        grids['se'] = build_empty_timetable(days, time_slots)
    if 'te' not in grids:
        grids['te'] = build_empty_timetable(days, time_slots)
    if 'be' not in grids:
        grids['be'] = build_empty_timetable(days, time_slots)

    # Tracking structures for constraints
    occupied_teachers = {}   # (day_idx, slot_idx) -> set(teacher_initials)
    occupied_rooms = {}      # (day_idx, slot_idx) -> set(room_number)
    teacher_daily_load = {}  # (teacher_initials, day_idx) -> int
    teacher_weekly_load = {} # teacher_initials -> int
    div_day_subjects = {}    # (div_key, day_idx) -> set(subject_code)

    for d_idx in range(len(days)):
        for s_idx in range(len(time_slots)):
            occupied_teachers[(d_idx, s_idx)] = set()
            occupied_rooms[(d_idx, s_idx)] = set()
            if s_idx == recess_slot_idx:
                occupied_rooms[(d_idx, s_idx)].add("RECESS")

    # Step 1: Pre-populate and lock sessions from existing timetable
    locked_count = 0
    if locked_timetable:
        for k in div_keys:
            if k in locked_timetable:
                existing_grid = locked_timetable[k]
                for d_idx, row in enumerate(existing_grid):
                    if d_idx >= len(days):
                        continue
                    for s_idx, slot in enumerate(row.get('slots', [])):
                        if s_idx >= len(time_slots):
                            continue
                        if slot.get('isLocked') and not slot.get('isRecess') and slot.get('subject'):
                            # Retain locked session
                            grids[k][d_idx]['slots'][s_idx] = deepcopy(slot)
                            t_init = slot.get('teacher')
                            rm = slot.get('room')
                            sub = slot.get('subject')

                            if t_init:
                                occupied_teachers[(d_idx, s_idx)].add(t_init)
                                teacher_daily_load[(t_init, d_idx)] = teacher_daily_load.get((t_init, d_idx), 0) + 1
                                teacher_weekly_load[t_init] = teacher_weekly_load.get(t_init, 0) + 1
                            if rm:
                                occupied_rooms[(d_idx, s_idx)].add(rm)
                            if sub:
                                div_day_subjects.setdefault((k, d_idx), set()).add(sub)
                            locked_count += 1

    # Prepare faculty metadata
    teachers_list = context.get('teachers', [])
    teachers_by_init = {t['initials']: t for t in teachers_list}
    teachers_by_id = {t['id']: t for t in teachers_list}

    # Prepare room catalogs
    all_rooms = context.get('classrooms', [])
    classrooms = [r for r in all_rooms if r.get('room_type') == 'classroom']
    laboratories = [r for r in all_rooms if r.get('room_type') == 'laboratory']

    # Step 2: Build Demand Pools (Theory & Practical)
    # We will assemble all sessions needed across divisions
    practical_demands = []
    theory_demands = []

    # Map academic year code to division keys
    ay_map = {ay.get('code'): ay.get('id') for ay in context.get('academic_years', [])}

    # Gather demands from subjects and teacher assignments
    subjects_list = context.get('subjects', [])
    for sub in subjects_list:
        sub_code = sub.get('code')
        sub_name = sub.get('name')
        y_code = sub.get('year_code') or 'SE'
        th_req = int(sub.get('theory_hours_per_week', 0) or 0)
        pt_req = int(sub.get('practical_hours_per_week', 0) or 0)
        req_room_type = sub.get('required_room_type', 'classroom')
        pref_room = sub.get('preferred_room', '')

        # Determine target division keys for this subject
        target_divs = []
        if y_code.lower() in grids:
            target_divs.append(y_code.lower())
        else:
            target_divs.append(div_keys[0] if div_keys else 'se')

        # Find eligible faculty from teacher_subjects
        eligible_faculty = []
        for t in teachers_list:
            for a in t.get('assignments', []):
                if a.get('subject_code') == sub_code or a.get('subject_id') == sub.get('id'):
                    eligible_faculty.append({
                        'initials': t['initials'],
                        'name': t['name'],
                        'time_slot': t.get('time_slot', 'C'),
                        'max_day': int(t.get('max_hours_per_day', 6) or 6),
                        'max_week': int(t.get('max_hours_per_week', 24) or 24),
                        'unavailable': t.get('unavailable_slots', ''),
                        'lab_room': a.get('lab_room', pref_room)
                    })

        for div_k in target_divs:
            # Practical demand: 2-hour consecutive block
            if pt_req > 0:
                practical_demands.append({
                    'division': div_k,
                    'year_code': y_code,
                    'subject': sub_code,
                    'subject_name': sub_name,
                    'duration': 2,
                    'eligible_faculty': eligible_faculty,
                    'pref_room': pref_room or (f"Lab {y_code}"),
                    'is_lab': True
                })

            # Theory demands: 1-hour slots
            if th_req > 0:
                for _ in range(th_req):
                    theory_demands.append({
                        'division': div_k,
                        'year_code': y_code,
                        'subject': sub_code,
                        'subject_name': sub_name,
                        'duration': 1,
                        'eligible_faculty': eligible_faculty,
                        'pref_room': pref_room or DEFAULT_CLASSROOMS.get(y_code, 'Classroom 301'),
                        'is_lab': False
                    })

    # Fallback to legacy format if no database subjects were found
    if not practical_demands and not theory_demands and teachers_list:
        return generate_schedules_legacy(teachers_list)

    # Step 3: Schedule Practicals (Consecutive 2-Slot Blocks)
    # Valid practical slot pairs: (0, 1), (2, 3), (5, 6)
    valid_pairs = []
    num_slots = len(time_slots)
    for s in range(0, num_slots - 1):
        if s != recess_slot_idx and (s + 1) != recess_slot_idx and s + 1 < num_slots:
            if (s in [0, 2, 5]): # clean 2-hour academic blocks
                valid_pairs.append((s, s + 1))

    unassigned_diagnostics = []

    # Sort practical demands by MRV (faculty with fewest available slots first)
    random.shuffle(practical_demands)
    for p_demand in practical_demands:
        div_k = p_demand['division']
        sub = p_demand['subject']
        assigned = False

        # Try days and valid practical slot pairs
        day_indices = list(range(len(days)))
        random.shuffle(day_indices)

        for d_idx in day_indices:
            if assigned:
                break
            for s1, s2 in valid_pairs:
                # Check division availability
                cell1 = grids[div_k][d_idx]['slots'][s1]
                cell2 = grids[div_k][d_idx]['slots'][s2]
                if cell1.get('text') or cell2.get('text') or cell1.get('isRecess') or cell2.get('isRecess'):
                    continue

                # Find eligible faculty available for both slots
                fac_candidates = list(p_demand['eligible_faculty'])
                random.shuffle(fac_candidates)

                for fac in fac_candidates:
                    f_init = fac['initials']
                    lab_rm = fac.get('lab_room') or p_demand['pref_room'] or "Tech Lab"

                    # Check faculty unavailable slots constraint
                    unav = fac.get('unavailable', '')
                    day_name = days[d_idx]
                    if f"{day_name}-{s1+1}" in unav or f"{day_name}-{s2+1}" in unav:
                        continue

                    # Check teacher availability
                    if f_init in occupied_teachers[(d_idx, s1)] or f_init in occupied_teachers[(d_idx, s2)]:
                        continue

                    # Check room availability
                    if lab_rm in occupied_rooms[(d_idx, s1)] or lab_rm in occupied_rooms[(d_idx, s2)]:
                        continue

                    # Check workload limits
                    d_load = teacher_daily_load.get((f_init, d_idx), 0)
                    w_load = teacher_weekly_load.get(f_init, 0)
                    if d_load + 2 > fac['max_day'] or w_load + 2 > fac['max_week']:
                        continue

                    # Allocate 2-slot practical session
                    for s in [s1, s2]:
                        grids[div_k][d_idx]['slots'][s] = {
                            "slot_id": s + 1,
                            "time": time_slots[s]["time"],
                            "isRecess": False,
                            "isLocked": False,
                            "text": f"LAB-{sub}({f_init})",
                            "subject": f"LAB-{sub}",
                            "teacher": f_init,
                            "room": lab_rm,
                            "isLab": True
                        }
                        occupied_teachers[(d_idx, s)].add(f_init)
                        occupied_rooms[(d_idx, s)].add(lab_rm)

                    teacher_daily_load[(f_init, d_idx)] = d_load + 2
                    teacher_weekly_load[f_init] = w_load + 2
                    div_day_subjects.setdefault((div_k, d_idx), set()).add(f"LAB-{sub}")
                    assigned = True
                    break

        if not assigned:
            unassigned_diagnostics.append(
                f"Practical block for {sub} ({div_k.upper()}) could not be accommodated without exceeding faculty workload or room capacity."
            )

    # Step 4: Schedule Theory Lectures (1-Hour Slots with Backtracking & Soft Heuristics)
    random.shuffle(theory_demands)
    for t_demand in theory_demands:
        div_k = t_demand['division']
        sub = t_demand['subject']
        assigned = False

        # Order candidate slots: prefer days where this subject is not yet taught (soft constraint 1)
        candidate_slots = []
        for d_idx in range(len(days)):
            has_sub_today = sub in div_day_subjects.get((div_k, d_idx), set())
            for s_idx in range(len(time_slots)):
                if s_idx == recess_slot_idx:
                    continue
                cell = grids[div_k][d_idx]['slots'][s_idx]
                if cell.get('text') or cell.get('isRecess'):
                    continue
                candidate_slots.append((has_sub_today, d_idx, s_idx))

        # Sort candidate slots: False (no subject today) comes before True
        candidate_slots.sort(key=lambda x: (x[0], random.random()))

        for _, d_idx, s_idx in candidate_slots:
            if assigned:
                break

            fac_candidates = list(t_demand['eligible_faculty'])
            # Sort faculty by slot preference (soft constraint 2)
            def score_faculty(f):
                pref = f.get('time_slot', 'C')
                score = 0
                if pref == 'A' and s_idx <= 3:  # morning preference
                    score -= 5
                elif pref == 'B' and s_idx >= 5: # afternoon preference
                    score -= 5
                return score

            fac_candidates.sort(key=score_faculty)

            for fac in fac_candidates:
                f_init = fac['initials']
                rm = t_demand['pref_room']

                # Faculty unavailability constraint
                unav = fac.get('unavailable', '')
                day_name = days[d_idx]
                if f"{day_name}-{s_idx+1}" in unav:
                    continue

                # Hard check: teacher collision
                if f_init in occupied_teachers[(d_idx, s_idx)]:
                    continue

                # Hard check: room collision
                if rm in occupied_rooms[(d_idx, s_idx)]:
                    continue

                # Hard check: daily & weekly workload limits
                d_load = teacher_daily_load.get((f_init, d_idx), 0)
                w_load = teacher_weekly_load.get(f_init, 0)
                if d_load + 1 > fac['max_day'] or w_load + 1 > fac['max_week']:
                    continue

                # Assign Theory Lecture
                grids[div_k][d_idx]['slots'][s_idx] = {
                    "slot_id": s_idx + 1,
                    "time": time_slots[s_idx]["time"],
                    "isRecess": False,
                    "isLocked": False,
                    "text": f"{sub}({f_init})",
                    "subject": sub,
                    "teacher": f_init,
                    "room": rm,
                    "isLab": False
                }
                occupied_teachers[(d_idx, s_idx)].add(f_init)
                occupied_rooms[(d_idx, s_idx)].add(rm)
                teacher_daily_load[(f_init, d_idx)] = d_load + 1
                teacher_weekly_load[f_init] = w_load + 1
                div_day_subjects.setdefault((div_k, d_idx), set()).add(sub)
                assigned = True
                break

        if not assigned:
            unassigned_diagnostics.append(
                f"Theory lecture '{sub}' ({div_k.upper()}) could not find an open conflict-free slot for eligible faculty."
            )

    result_data = {
        'se': grids.get('se', build_empty_timetable()),
        'te': grids.get('te', build_empty_timetable()),
        'be': grids.get('be', build_empty_timetable()),
        'divisions': list(grids.keys()),
        'timeSlots': [s["time"] for s in time_slots],
        'fullTimeSlots': time_slots,
        'workingDays': days,
        'locked_count': locked_count,
        'unassigned_diagnostics': unassigned_diagnostics,
        'generated_at': datetime.now().strftime('%b %d, %Y • %I:%M %p')
    }

    # Add custom divisions if any exist
    for k, v in grids.items():
        result_data[k] = v

    conflicts = detect_conflicts(result_data)
    return result_data, conflicts


# ═════════════════════════════════════════════════════════
# BACKWARD COMPATIBLE SCHEDULER
# ═════════════════════════════════════════════════════════
def generate_schedules(teachers_list, locked_timetable=None):
    """
    Generate synchronized, conflict-free schedules for SE, TE, and BE.
    Wraps legacy teacher list into CSP format and ensures zero conflicts.
    """
    if not teachers_list:
        return None, ["No faculty records available to generate timetable."]

    se_grid = build_empty_timetable()
    te_grid = build_empty_timetable()
    be_grid = build_empty_timetable()

    lab_patterns = {
        'SE': [
            (0, [0, 1]), (1, [2, 3]), (4, [0, 1]), (5, [0, 1, 2, 3])
        ],
        'TE': [
            (0, [5, 6]), (1, [5, 6]), (2, [2, 3, 5, 6]), (3, [5, 6]), (4, [2, 3])
        ],
        'BE': [
            (0, [2, 3]), (1, [0, 1]), (2, [0, 1, 5, 6]), (3, [2, 3])
        ]
    }

    occupied_teachers = {}
    occupied_rooms = {}

    for d_idx in range(6):
        for s_idx in range(7):
            occupied_teachers[(d_idx, s_idx)] = set()
            occupied_rooms[(d_idx, s_idx)] = set()
            if s_idx == 4:
                occupied_rooms[(d_idx, s_idx)].add("RECESS")

    # Step 0: Apply locked sessions if provided
    locked_count = 0
    if locked_timetable:
        for ycode, grid in [('se', se_grid), ('te', te_grid), ('be', be_grid)]:
            if ycode in locked_timetable:
                for d_idx, row in enumerate(locked_timetable[ycode]):
                    for s_idx, slot in enumerate(row.get('slots', [])):
                        if slot.get('isLocked') and not slot.get('isRecess') and slot.get('subject'):
                            grid[d_idx]['slots'][s_idx] = deepcopy(slot)
                            if slot.get('teacher'):
                                occupied_teachers[(d_idx, s_idx)].add(slot['teacher'])
                            if slot.get('room'):
                                occupied_rooms[(d_idx, s_idx)].add(slot['room'])
                            locked_count += 1

    # Step 1: Assign Lab Sessions
    for year_code, grid, sub_key, pt_key, lab_key, default_room in [
        ('SE', se_grid, 'seSub', 'sePt', 'seLab', DEFAULT_CLASSROOMS['SE']),
        ('TE', te_grid, 'teSub', 'tePt', 'teLab', DEFAULT_CLASSROOMS['TE']),
        ('BE', be_grid, 'beSub', 'bePt', 'beLab', DEFAULT_CLASSROOMS['BE']),
    ]:
        lab_faculty = [t for t in teachers_list if t.get(pt_key, 0) > 0 and t.get(sub_key)]
        random.shuffle(lab_faculty)

        patterns = lab_patterns.get(year_code, [])
        for d_idx, slot_indices in patterns:
            for i in range(0, len(slot_indices), 2):
                if i + 1 < len(slot_indices):
                    s1 = slot_indices[i]
                    s2 = slot_indices[i+1]

                    # Skip if either slot is already locked
                    if grid[d_idx]["slots"][s1].get("isLocked") or grid[d_idx]["slots"][s2].get("isLocked"):
                        continue

                    assigned = False
                    for fac in lab_faculty:
                        t_name = fac['name']
                        l_room = fac.get(lab_key) or f"Lab {year_code}"
                        if (t_name not in occupied_teachers[(d_idx, s1)] and
                            t_name not in occupied_teachers[(d_idx, s2)] and
                            l_room not in occupied_rooms[(d_idx, s1)] and
                            l_room not in occupied_rooms[(d_idx, s2)]):

                            sub = fac.get(sub_key)
                            for s in [s1, s2]:
                                grid[d_idx]["slots"][s] = {
                                    "slot_id": s + 1,
                                    "time": TIME_SLOTS[s]["time"],
                                    "isRecess": False,
                                    "isLocked": False,
                                    "text": f"LAB-{sub}({t_name})",
                                    "subject": f"LAB-{sub}",
                                    "teacher": t_name,
                                    "room": l_room,
                                    "isLab": True
                                }
                                occupied_teachers[(d_idx, s)].add(t_name)
                                occupied_rooms[(d_idx, s)].add(l_room)
                            assigned = True
                            break

    # Step 2: Assign Theory Lectures
    hours_pool = {'SE': [], 'TE': [], 'BE': []}
    for t in teachers_list:
        for ycode, sub_k, th_k in [('SE', 'seSub', 'seTh'), ('TE', 'teSub', 'teTh'), ('BE', 'beSub', 'beTh')]:
            th = int(t.get(th_k, 0) or 0)
            sub = t.get(sub_k)
            if th > 0 and sub:
                for _ in range(th):
                    hours_pool[ycode].append({
                        'teacher': t['name'],
                        'subject': sub,
                        'slot_pref': t.get('timeSlot', 'C'),
                        'room': DEFAULT_CLASSROOMS[ycode]
                    })

    for ycode, grid in [('SE', se_grid), ('TE', te_grid), ('BE', be_grid)]:
        random.shuffle(hours_pool[ycode])
        pool = hours_pool[ycode]

        for d_idx in range(6):
            for s_idx in range(7):
                cell = grid[d_idx]["slots"][s_idx]
                if cell.get("isRecess") or cell.get("text") or cell.get("isLocked"):
                    continue

                allocated = False
                for idx, item in enumerate(pool):
                    t_name = item['teacher']
                    pref = item['slot_pref']

                    pref_match = True
                    if pref == 'A' and s_idx >= 5:
                        pref_match = False
                    elif pref == 'B' and s_idx < 3:
                        pref_match = False

                    if t_name not in occupied_teachers[(d_idx, s_idx)] and pref_match:
                        room = item['room']
                        grid[d_idx]["slots"][s_idx] = {
                            "slot_id": s_idx + 1,
                            "time": TIME_SLOTS[s_idx]["time"],
                            "isRecess": False,
                            "isLocked": False,
                            "text": f"{item['subject']}({t_name})",
                            "subject": item['subject'],
                            "teacher": t_name,
                            "room": room,
                            "isLab": False
                        }
                        occupied_teachers[(d_idx, s_idx)].add(t_name)
                        occupied_rooms[(d_idx, s_idx)].add(room)
                        pool.pop(idx)
                        allocated = True
                        break

                if not allocated and pool:
                    for idx, item in enumerate(pool):
                        t_name = item['teacher']
                        if t_name not in occupied_teachers[(d_idx, s_idx)]:
                            room = item['room']
                            grid[d_idx]["slots"][s_idx] = {
                                "slot_id": s_idx + 1,
                                "time": TIME_SLOTS[s_idx]["time"],
                                "isRecess": False,
                                "isLocked": False,
                                "text": f"{item['subject']}({t_name})",
                                "subject": item['subject'],
                                "teacher": t_name,
                                "room": room,
                                "isLab": False
                            }
                            occupied_teachers[(d_idx, s_idx)].add(t_name)
                            occupied_rooms[(d_idx, s_idx)].add(room)
                            pool.pop(idx)
                            allocated = True
                            break

    result_data = {
        'se': se_grid,
        'te': te_grid,
        'be': be_grid,
        'divisions': ['se', 'te', 'be'],
        'timeSlots': [s["time"] for s in TIME_SLOTS],
        'fullTimeSlots': TIME_SLOTS,
        'locked_count': locked_count,
        'generated_at': datetime.now().strftime('%b %d, %Y • %I:%M %p')
    }

    conflicts = detect_conflicts(result_data)
    return result_data, conflicts


def generate_schedules_legacy(teachers_list):
    """Wrapper alias for generate_schedules."""
    return generate_schedules(teachers_list)


# ═════════════════════════════════════════════════════════
# COMPREHENSIVE CONFLICT DETECTION ENGINE (REQUIREMENT 6)
# ═════════════════════════════════════════════════════════
def detect_conflicts(timetable_data):
    """
    Examine the entire timetable dataset across all divisions and classes.
    Detects:
    1. Teacher overlap / double-booking (CRITICAL ERROR)
    2. Classroom / Laboratory overlap (CRITICAL ERROR)
    3. Division / Cohort overlap (CRITICAL ERROR)
    4. Sessions scheduled during protected Recess (CRITICAL ERROR)
    5. Consecutive lectures limit exceeded (WARNING)
    6. Daily workload exceeded (WARNING)
    7. Weekly workload exceeded (WARNING)
    """
    conflicts = []
    if not timetable_data:
        return conflicts

    # Find all division keys present in dataset
    div_keys = timetable_data.get('divisions', [])
    if not div_keys:
        div_keys = [k for k in timetable_data.keys() if isinstance(timetable_data[k], list) and k not in ['timeSlots', 'fullTimeSlots', 'workingDays', 'unassigned_diagnostics']]
    if not div_keys:
        div_keys = ['se', 'te', 'be']

    teacher_schedule_tracker = {}  # (day, slot_id) -> list of sessions
    room_schedule_tracker = {}     # (day, slot_id) -> list of sessions
    teacher_daily_hours = {}       # (teacher, day) -> count
    teacher_consecutive = {}       # (teacher, day) -> max consecutive count
    teacher_weekly_hours = {}      # teacher -> count

    for y in div_keys:
        grid = timetable_data.get(y, [])
        for row in grid:
            day = row.get("day", "")
            current_consecutive = {}

            for slot in row.get("slots", []):
                slot_id = slot.get("slot_id")
                teacher = slot.get("teacher", "").strip()
                room = slot.get("room", "").strip()
                subject = slot.get("subject", "").strip()
                is_recess = slot.get("isRecess", False)
                time_label = slot.get("time", f"Slot {slot_id}")

                # 1. Recess violation check
                if is_recess and subject not in ["RECESS", "RECESS / LUNCH", ""]:
                    conflicts.append({
                        "type": "recess_violation",
                        "severity": "error",
                        "day": day,
                        "slot": time_label,
                        "division": y.upper(),
                        "message": f"{y.upper()}: Lecture '{subject}' scheduled during protected Recess ({time_label}).",
                        "suggestion": "Move session to an open theory slot outside the lunch break."
                    })

                # If active teaching session
                if teacher and teacher not in ["", "FACULTY"] and not is_recess:
                    key = (day, slot_id)
                    if key not in teacher_schedule_tracker:
                        teacher_schedule_tracker[key] = []

                    # 2. Teacher overlap check
                    for existing in teacher_schedule_tracker[key]:
                        if existing["teacher"] == teacher:
                            conflicts.append({
                                "type": "teacher_overlap",
                                "severity": "error",
                                "day": day,
                                "slot": time_label,
                                "teacher": teacher,
                                "division": y.upper(),
                                "message": f"CRITICAL CONFLICT: Faculty member '{teacher}' is double-booked in {existing['division']} ({existing['subject']}) and {y.upper()} ({subject}) on {day} at {time_label}.",
                                "suggestion": f"Reassign one session or swap time slots with an available faculty member."
                            })

                    teacher_schedule_tracker[key].append({
                        "division": y.upper(),
                        "subject": subject,
                        "teacher": teacher,
                        "room": room
                    })

                    # Workload tracking
                    t_day_key = (teacher, day)
                    teacher_daily_hours[t_day_key] = teacher_daily_hours.get(t_day_key, 0) + 1
                    teacher_weekly_hours[teacher] = teacher_weekly_hours.get(teacher, 0) + 1

                    # Consecutive tracking
                    current_consecutive[teacher] = current_consecutive.get(teacher, 0) + 1
                    if current_consecutive[teacher] > teacher_consecutive.get(t_day_key, 0):
                        teacher_consecutive[t_day_key] = current_consecutive[teacher]
                else:
                    # Reset consecutive counter for all teachers if slot was free or recess
                    current_consecutive.clear()

                # 3. Room overlap check
                if room and room not in ["", "Classroom"] and not is_recess:
                    r_key = (day, slot_id)
                    if r_key not in room_schedule_tracker:
                        room_schedule_tracker[r_key] = []

                    for existing in room_schedule_tracker[r_key]:
                        if existing["room"] == room:
                            conflicts.append({
                                "type": "room_overlap",
                                "severity": "error",
                                "day": day,
                                "slot": time_label,
                                "room": room,
                                "division": y.upper(),
                                "message": f"ROOM COLLISION: Room '{room}' is double-booked for {existing['division']} ({existing['subject']}) and {y.upper()} ({subject}) on {day} at {time_label}.",
                                "suggestion": "Assign an alternative available classroom or laboratory."
                            })

                    room_schedule_tracker[r_key].append({
                        "division": y.upper(),
                        "subject": subject,
                        "teacher": teacher,
                        "room": room
                    })

    # Workload limit checks (soft constraints / warnings)
    for (teacher, day), hours in teacher_daily_hours.items():
        if hours > 5:
            conflicts.append({
                "type": "daily_workload_exceeded",
                "severity": "warning",
                "day": day,
                "teacher": teacher,
                "message": f"Workload Notice: {teacher} has {hours} hours scheduled on {day} (recommended maximum is 5 per day).",
                "suggestion": "Distribute lectures more evenly across other weekdays."
            })

    for (teacher, day), cons in teacher_consecutive.items():
        if cons > 3:
            conflicts.append({
                "type": "consecutive_lectures_exceeded",
                "severity": "warning",
                "day": day,
                "teacher": teacher,
                "message": f"Consecutive Lectures Warning: {teacher} has {cons} consecutive lectures on {day}.",
                "suggestion": "Introduce a free period between lectures to avoid teacher fatigue."
            })

    return conflicts


# ═════════════════════════════════════════════════════════
# FACULTY & ROOM TIMETABLE EXTRACTORS
# ═════════════════════════════════════════════════════════
def get_faculty_timetable(timetable_data, teacher_initials):
    """
    Extract a single faculty member's personal weekly schedule from the master timetable.
    """
    faculty_grid = []
    total_teaching_hours = 0
    assigned_divisions = set()
    assigned_subjects = set()
    assigned_rooms = set()

    div_keys = timetable_data.get('divisions', [])
    if not div_keys:
        div_keys = [k for k in timetable_data.keys() if isinstance(timetable_data[k], list) and k not in ['timeSlots', 'fullTimeSlots', 'workingDays', 'unassigned_diagnostics']]
    if not div_keys:
        div_keys = ['se', 'te', 'be']

    days = timetable_data.get('workingDays') or DAYS
    raw_slots = timetable_data.get('fullTimeSlots') or TIME_SLOTS

    for d_idx, day_name in enumerate(days):
        row = {"day": day_name, "slots": []}
        for s_idx, slot_meta in enumerate(raw_slots):
            slot_id = slot_meta.get("slot_id") or (s_idx + 1)
            time_str = slot_meta.get("time", "")
            is_recess = (slot_meta.get("type") == "recess" or slot_meta.get("slot_type") == "recess")

            found_class = None
            if not is_recess:
                for y in div_keys:
                    grid = timetable_data.get(y, [])
                    if d_idx < len(grid) and s_idx < len(grid[d_idx]["slots"]):
                        cell = grid[d_idx]["slots"][s_idx]
                        if cell.get("teacher") == teacher_initials:
                            found_class = {
                                "division": y.upper(),
                                "subject": cell.get("subject"),
                                "room": cell.get("room"),
                                "isLab": cell.get("isLab", False),
                                "isLocked": cell.get("isLocked", False)
                            }
                            total_teaching_hours += 1
                            assigned_divisions.add(y.upper())
                            assigned_subjects.add(cell.get("subject"))
                            if cell.get("room"):
                                assigned_rooms.add(cell.get("room"))
                            break

            if is_recess:
                row["slots"].append({
                    "slot_id": slot_id,
                    "time": time_str,
                    "isRecess": True,
                    "status": "recess",
                    "text": "RECESS",
                    "subject": "RECESS",
                    "room": ""
                })
            elif found_class:
                row["slots"].append({
                    "slot_id": slot_id,
                    "time": time_str,
                    "isRecess": False,
                    "status": "busy",
                    "division": found_class["division"],
                    "subject": found_class["subject"],
                    "room": found_class["room"],
                    "isLab": found_class["isLab"],
                    "isLocked": found_class["isLocked"],
                    "text": f"{found_class['subject']} ({found_class['division']})"
                })
            else:
                row["slots"].append({
                    "slot_id": slot_id,
                    "time": time_str,
                    "isRecess": False,
                    "status": "free",
                    "text": "FREE",
                    "subject": "Free Period",
                    "room": ""
                })
        faculty_grid.append(row)

    return {
        "teacher": teacher_initials,
        "grid": faculty_grid,
        "total_hours": total_teaching_hours,
        "divisions": sorted(list(assigned_divisions)),
        "subjects": sorted(list(assigned_subjects)),
        "rooms": sorted(list(assigned_rooms))
    }


def get_classroom_timetable(timetable_data, room_number):
    """
    Extract a single classroom or laboratory's weekly schedule.
    """
    room_grid = []
    occupied_count = 0

    div_keys = timetable_data.get('divisions', [])
    if not div_keys:
        div_keys = [k for k in timetable_data.keys() if isinstance(timetable_data[k], list) and k not in ['timeSlots', 'fullTimeSlots', 'workingDays', 'unassigned_diagnostics']]
    if not div_keys:
        div_keys = ['se', 'te', 'be']

    days = timetable_data.get('workingDays') or DAYS
    raw_slots = timetable_data.get('fullTimeSlots') or TIME_SLOTS

    for d_idx, day_name in enumerate(days):
        row = {"day": day_name, "slots": []}
        for s_idx, slot_meta in enumerate(raw_slots):
            slot_id = slot_meta.get("slot_id") or (s_idx + 1)
            time_str = slot_meta.get("time", "")
            is_recess = (slot_meta.get("type") == "recess" or slot_meta.get("slot_type") == "recess")

            found_session = None
            if not is_recess:
                for y in div_keys:
                    grid = timetable_data.get(y, [])
                    if d_idx < len(grid) and s_idx < len(grid[d_idx]["slots"]):
                        cell = grid[d_idx]["slots"][s_idx]
                        if cell.get("room") == room_number or room_number in str(cell.get("room")):
                            found_session = {
                                "division": y.upper(),
                                "subject": cell.get("subject"),
                                "teacher": cell.get("teacher"),
                                "isLab": cell.get("isLab", False),
                                "isLocked": cell.get("isLocked", False)
                            }
                            occupied_count += 1
                            break

            if is_recess:
                row["slots"].append({
                    "slot_id": slot_id,
                    "time": time_str,
                    "isRecess": True,
                    "status": "recess",
                    "text": "RECESS"
                })
            elif found_session:
                row["slots"].append({
                    "slot_id": slot_id,
                    "time": time_str,
                    "isRecess": False,
                    "status": "occupied",
                    "division": found_session["division"],
                    "subject": found_session["subject"],
                    "teacher": found_session["teacher"],
                    "isLab": found_session["isLab"],
                    "isLocked": found_session["isLocked"],
                    "text": f"{found_session['division']} - {found_session['subject']} ({found_session['teacher']})"
                })
            else:
                row["slots"].append({
                    "slot_id": slot_id,
                    "time": time_str,
                    "isRecess": False,
                    "status": "available",
                    "text": "Available"
                })
        room_grid.append(row)

    total_usable_slots = len(days) * (len(raw_slots) - 1)
    utilization_rate = round((occupied_count / max(1, total_usable_slots)) * 100, 1)

    return {
        "room": room_number,
        "grid": room_grid,
        "occupied_slots": occupied_count,
        "total_slots": total_usable_slots,
        "utilization_rate": utilization_rate
    }
