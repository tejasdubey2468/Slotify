# MASTER DEVELOPMENT PROMPT — SLOTIFY 🗓️
## Smart College Timetable Management & Scheduling Platform

Act as a senior full-stack engineer, software architect, database designer, and UI/UX designer. Your task is to inspect, improve, and transform my existing College Timetable Generator project into a complete, modern, reliable, and production-oriented application named **Slotify 🗓️**.

Do not create a separate application from scratch. Work directly within the existing repository, understand its current implementation, and improve it systematically.

The goal is to build a platform that can manage complex college scheduling requirements involving multiple departments, academic years, semesters, divisions, subjects, teachers, classrooms, laboratories, practical batches, recess periods, holidays, and timetable exports.

**Important: Do not merely create an attractive frontend or static dashboard. All features must work with real application data and connect to the appropriate backend, database, and scheduling logic.**

---

# PHASE 1 — INSPECT THE EXISTING PROJECT

Before making changes:

1. Inspect the complete repository structure and identify the existing frontend, backend, scheduling engine, dependencies, configuration files, and entry points.
2. Understand how the existing timetable generation algorithm works.
3. Identify existing features that can be reused rather than rewritten.
4. Determine how teachers, subjects, classrooms, divisions, schedules, and lecture periods are currently represented.
5. Identify missing functionality, potential scheduling conflicts, hardcoded data, and architectural issues.
6. Check the current setup instructions and verify how the application runs locally.
7. Create an implementation plan based on the actual codebase.

Preserve working functionality wherever possible. Do not assume a technology stack without inspecting the project.

If a database is required and none exists, select an appropriate database and implement persistent storage using the architecture best suited to the existing project. Avoid introducing unnecessary frameworks or services.

Do not stop after writing a plan. Execute the implementation, test it, and document the completed work.

# PHASE 2 — REBRAND THE APPLICATION AS SLOTIFY

Change the application name everywhere appropriate to:

**Slotify 🗓️**

Update:
- Application title and browser tab title.
- Logo and sidebar branding.
- Login page and dashboard branding, if present.
- Page headings and application metadata.
- README and project documentation.
- Export document titles and generated report headers.
- Existing references to the old application name in user-facing content.

Create a clean, recognizable calendar-inspired visual identity. Keep the branding consistent throughout the application.

Do not change unrelated identifiers or database values unnecessarily just to rename the application.

# PHASE 3 — COMPLETE UI/UX REDESIGN

## Design direction

Use a combination of:

- Swiss Grid Minimalism.
- Modern Campus aesthetics.
- Soft pastel colors.
- Precise grid alignment.
- Rounded corners and smooth visual transitions.
- Professional academic dashboard design.

The application should look like a polished commercial SaaS product, not a basic college assignment.

### Color palette

Use these colors consistently:

- Main background: `#FAF5EB`
- Primary forest green: `#315C45`
- Main text: `#292E27`
- White and warm ivory surfaces: `#FFFFFF`
- Soft sage: `#DCEBDD`
- Mint: `#D5EEE3`
- Pale terracotta: `#F3DDD0`
- Warm peach: `#F8E5D3`
- Butter yellow: `#F5EDC9`
- Dusty blue: `#DCE7F3`
- Soft lavender: `#E9E0F2`
- Muted olive: `#E5E8CE`
- Subtle borders: warm beige and grey-green tones.

### Styling requirements

1. Use moderately rounded corners across cards, buttons, forms, dropdowns, dialogs, timetable blocks, and panels.
2. Use approximately 10–14px corner radii for timetable blocks and 12–18px for larger cards.
3. Apply thin, elegant borders and restrained shadows.
4. Use soft pastel fills for subjects and timetable sessions.
5. Keep the timetable grid precise and easy to scan.
6. Use typography such as Inter or Manrope if compatible with the existing project.
7. Use subtle transitions, hover states, and focus indicators.
8. Keep spacing, alignment, icon sizes, and component styling consistent.
9. Use forest green for primary actions and selected states.
10. Use red and amber only when communicating actual errors or warnings.
11. Make the layout responsive on desktop, tablet, and mobile.
12. Avoid excessive gradients, neon colors, glassmorphism, harsh outlines, and excessive animation.

The interface should feel soft, interesting, modern, and premium without sacrificing information density or usability.

# PHASE 4 — INTERACTIVE TIMETABLE DASHBOARD

Create or improve the main dashboard so administrators can manage the complete scheduling process from one place.

Include:

- Total faculty members.
- Total subjects.
- Total classrooms and laboratories.
- Total divisions and batches.
- Total scheduled lectures.
- Unassigned lectures.
- Scheduling conflicts.
- Upcoming holidays.
- Timetable generation status.
- Recent timetable changes.

Provide useful filters for:

- Academic year.
- Semester.
- Department.
- Division.
- Faculty member.
- Classroom.
- Subject.
- Date range.

The dashboard must use actual persisted data rather than hardcoded statistics.

Provide clear navigation to the existing or newly implemented modules:

1. Overview.
2. Timetable.
3. Generate Timetable.
4. Faculty.
5. Subjects.
6. Classrooms and Labs.
7. Divisions and Batches.
8. Faculty Timetables.
9. Holidays and Academic Calendar.
10. Notifications.
11. Exports and Reports.
12. Settings.

Do not create empty pages that only look functional. Implement working views and appropriate empty states.

# PHASE 5 — ADVANCED TIMETABLE GENERATION ENGINE

Improve the existing scheduling engine so it can generate reliable schedules for realistic college requirements.

The system must support multiple departments, academic years, semesters, divisions, and practical batches.

## A. Scheduling constraints

Implement validation for the following rules:

- A teacher cannot teach two sessions simultaneously.
- A classroom cannot host two sessions simultaneously.
- A division cannot attend two sessions simultaneously.
- A practical batch cannot be assigned to multiple labs at the same time.
- A teacher must be qualified to teach the assigned subject.
- Each subject must receive its required weekly lecture and practical hours.
- Sessions must fit within configured working hours.
- Breaks and holidays must be respected.
- Teacher availability must be respected.
- Room capacity and room type must match session requirements.
- Practical sessions must support configurable durations and consecutive periods.
- Fixed lectures must remain in their assigned time slots.
- Shared faculty must be coordinated across departments.
- No lectures should be scheduled on configured non-working days or holidays unless explicitly permitted.

Distinguish between:

**Hard constraints:** Rules that must never be violated in a successfully generated timetable.

**Soft constraints:** Preferences that should be optimized where possible, such as teacher preferences, balanced daily workload, fewer gaps, and room utilization.

If the constraints cannot all be satisfied, explain why and identify the conflicting requirements instead of silently producing an invalid timetable.

## B. Optimization

Inspect the existing algorithm and improve it appropriately.

If the existing approach is insufficient for complex scheduling, evaluate Google OR-Tools CP-SAT or another suitable constraint-solving approach.

Optimize for:

- Zero hard-constraint conflicts.
- Balanced faculty workload.
- Balanced lecture distribution across the week.
- Fewer unnecessary gaps.
- Reduced classroom changes where practical.
- Appropriate room and lab utilization.
- Teacher availability and preferences.
- Correct subject-hour distribution.
- Minimal disruption to already approved schedules when regenerating.

Do not introduce a genetic algorithm or optimization library just for appearance. Choose an approach that fits the requirements and verify it through tests.

## C. Timetable generation workflow

Provide an interactive generation workflow:

1. Select academic year and semester.
2. Select department, divisions, and batches.
3. Configure working days and time slots.
4. Configure subjects, required hours, faculty, and rooms.
5. Configure recess periods and holidays.
6. Validate all input data.
7. Generate a proposed timetable.
8. Display validation results and unscheduled sessions.
9. Allow review and manual adjustments.
10. Revalidate the modified timetable.
11. Save the approved timetable.
12. Export and publish it.

Show progress, validation errors, and understandable explanations whenever generation fails.

Never report successful generation if hard constraints remain violated.

# PHASE 6 — RECESS, BREAKS, AND TIME-SLOT MANAGEMENT

Implement configurable breaks, including:

- Morning recess.
- Lunch break.
- Afternoon recess.
- Custom break periods.

Administrators must be able to configure the name, start time, end time, and applicability of each break.

Support institution-wide breaks as well as applicable department or division-specific rules.

Breaks must be visually distinguishable in the timetable, using a soft cream, muted yellow, or another subtle neutral color.

The scheduling engine must not allocate lectures during protected break periods.

Allow configurable lecture duration, practical duration, transition time where required, working-day start time, and closing time.

Ensure that timetable blocks accurately reflect their actual durations.

# PHASE 7 — CLASSROOM VISIBILITY AND ALLOCATION

Classroom information must be visible wherever it is relevant.

## A. Timetable visibility

Every scheduled lecture block should display:

- Subject name.
- Faculty name.
- Classroom or laboratory number.
- Time range.
- Session type where useful.

Ensure classroom details are visible without requiring users to open a separate detail screen.

On smaller screens, display the most important information first and make remaining details accessible.

## B. Classroom management

Create a classroom management section that stores:

- Room name or number.
- Building or location.
- Room type.
- Seating capacity.
- Available equipment.
- Availability.
- Associated department, if applicable.

Support both ordinary classrooms and specialized laboratories.

## C. Classroom assignment

Allow administrators to assign classrooms to sessions or configure preferred rooms for subjects.

A subject may have a preferred classroom or laboratory, but the system must still validate actual availability and prevent double booking.

Support room allocation based on capacity, room type, required equipment, and time-slot availability.

Create a classroom timetable view that displays all sessions scheduled in a selected room.

If a suitable classroom is unavailable, identify the issue and suggest available alternatives.

# PHASE 8 — TEACHER AND SUBJECT MANAGEMENT

## A. Multiple subjects per teacher

A single teacher must be able to teach multiple subjects.

Implement a many-to-many relationship between teachers and subjects where appropriate.

Store teacher qualifications and subject assignments so the scheduling engine can determine which teachers are eligible for each subject.

Support:

- One teacher teaching multiple subjects.
- Multiple qualified teachers teaching the same subject.
- Different faculty members for theory and practical sessions.
- Faculty assigned across different divisions or departments where permitted.

Prevent simultaneous assignments even when the teacher teaches different subjects.

Do not assume that each teacher can teach only one subject.

## B. Teacher availability

For every faculty member, support:

- Available and unavailable time slots.
- Preferred working hours.
- Maximum daily lecture count.
- Maximum weekly teaching hours.
- Minimum or preferred break intervals.
- Approved leave or absence periods.
- Subject qualifications.
- Department assignments.

Use these settings when generating timetables.

Clearly distinguish mandatory availability restrictions from optional preferences.

Provide validation when the requested teaching workload exceeds a teacher's available capacity.

# PHASE 9 — INDIVIDUAL FACULTY TIMETABLES

Create a dedicated **Faculty Timetables** section.

The page must display faculty members in a searchable, organized grid or directory.

Each faculty card or grid item should show:

- Faculty name.
- Department.
- Assigned subjects.
- Weekly teaching hours, if available.
- A small timetable summary where appropriate.

When a user clicks a faculty member, open that person's complete timetable.

The individual faculty timetable must show:

- Days of the week.
- Time slots.
- Subject names.
- Division or batch.
- Classroom or laboratory.
- Lecture and practical sessions.
- Recess and free periods.

Include filters for semester, department, and academic period as applicable.

Provide a clear way to return to the faculty directory.

Support printing and exporting an individual faculty timetable.

Use real faculty records. Do not build a grid of decorative names that are not connected to actual schedules.

# PHASE 10 — FULL ACADEMIC CALENDAR AND HOLIDAYS

Create a full-year academic calendar covering January through December for the selected year, while allowing the institution's academic year to follow a different start and end date.

Include:

- National public holidays.
- Official holidays relevant to the institution's state or region.
- Institution-specific holidays.
- College events and academic activities.
- Examination periods.
- Semester start and end dates.
- Vacation periods.
- Special working days, if applicable.

## Holiday management

Each holiday should support:

- Name.
- Date or date range.
- Holiday category.
- Description.
- Applicability to departments or the entire institution.
- Source or official reference, where applicable.
- Published or draft status.

Allow administrators to add, edit, import, and remove institution-specific calendar entries.

## Important holiday requirements

Do not invent official holiday dates.

Use an appropriate official calendar or authoritative source for the relevant country and state. Since official dates can vary by region and year, make the holiday calendar configurable.

Display the relevant year and region clearly.

Support date-specific holiday entries, including movable holidays and year-dependent dates.

When an official holiday list cannot be verified, mark those entries as requiring administrator confirmation instead of claiming they are official.

The scheduling engine must respect configured non-working dates and date-specific exceptions.

Provide calendar views for month, week, and year where appropriate.

# PHASE 11 — EXPORT TIMETABLES IN MULTIPLE FORMATS

Provide working exports for:

- PDF.
- Excel (`.xlsx`).
- CSV (`.csv`).
- Word (`.docx`).

Where practical, support printing and a print-friendly HTML view as well.

Users should be able to export:

- Complete institutional timetables.
- Department timetables.
- Academic-year timetables.
- Semester timetables.
- Division timetables.
- Individual faculty timetables.
- Classroom timetables.
- Practical batch timetables.

## Export quality

PDF and Word exports should contain properly formatted timetable grids, headings, dates, semester information, and readable text.

Excel exports should contain structured rows and columns, appropriate headers, filters where useful, and consistent formatting.

CSV exports should contain clean, machine-readable data.

Respect the selected filters when exporting.

Use appropriate page orientation and page sizing so timetable columns are not cut off.

Include the Slotify name and generation date in report headers or footers where appropriate.

Exports must use the actual saved timetable data, not sample or placeholder content.

# PHASE 12 — SMART CONFLICT DETECTION

Implement a dedicated conflict detection and validation system.

Detect at least:

1. Teacher overlap.
2. Classroom overlap.
3. Division overlap.
4. Practical batch overlap.
5. Unqualified teacher assignment.
6. Missing required subject hours.
7. Teacher workload violations.
8. Room capacity or equipment mismatch.
9. Sessions scheduled during recess.
10. Sessions scheduled on non-working days or holidays.
11. Unassigned lectures.
12. Invalid or incomplete session data.

Display understandable messages describing:

- The type of conflict.
- The affected teacher, subject, division, or room.
- The conflicting day and time.
- Why the assignment is invalid.
- Suggested resolution options where possible.

Provide a validation summary showing total errors, warnings, and unresolved sessions.

Revalidate after manual changes and before approving or publishing a timetable.

Warnings about soft preferences should not be confused with hard scheduling violations.

# PHASE 13 — MANUAL TIMETABLE EDITING AND REGENERATION

Allow authorized administrators to edit generated timetables.

Support the existing timetable's appropriate editing interactions, including moving sessions between valid time slots if practical.

After every edit:

- Validate all affected constraints.
- Highlight invalid assignments.
- Explain why a proposed placement is invalid.
- Allow the user to cancel or revert the change.
- Save valid changes through the backend.
- Keep the displayed timetable synchronized with saved data.

Provide regeneration options:

- Regenerate the entire timetable.
- Regenerate a selected division.
- Regenerate a selected department.
- Regenerate only unscheduled sessions.
- Preserve fixed or manually locked sessions.

Do not overwrite an approved timetable silently.

Show a preview of changes before replacing a published schedule.

If partial regeneration is not feasible without disrupting constraints, explain the limitations and provide a safe alternative.

# PHASE 14 — VERSION HISTORY AND APPROVAL

Implement timetable version history.

Store meaningful versions when an administrator generates, edits, approves, or publishes a timetable.

Each version should record:

- Version identifier.
- Academic year and semester.
- Creation date and time.
- User responsible, if authentication exists.
- Change summary.
- Publication or approval status.

Allow authorized users to compare versions and restore an earlier version.

Restoring a version must create a new recorded revision or restore event rather than silently deleting intervening history.

Validate restored schedules before publishing them.

Keep a clear distinction between draft, approved, and published timetables.

# PHASE 15 — NOTIFICATION CENTER

Implement a functional notification section.

Support notifications for:

- Timetable publication.
- Lecture rescheduling.
- Classroom changes.
- Faculty substitution.
- Cancelled lectures.
- Upcoming holidays.
- Important academic-calendar updates.

Provide:

- A notification icon with an unread count.
- A dedicated notification center.
- Read and unread states.
- Notification timestamps.
- Relevant timetable links.
- Filtering by category where appropriate.

Notify affected users when a published timetable changes.

Avoid sending duplicate notifications for the same event.

If email or push notifications require external configuration, implement a clean notification service and document the required credentials. Do not pretend external delivery is working when it has not been configured.

In-app notifications must work using persisted application data.

# PHASE 16 — STUDENT AND FACULTY ACCESS

If authentication already exists, extend it appropriately. Otherwise, introduce a suitable authentication system compatible with the existing architecture.

Provide role-based access for:

- Administrator.
- Faculty.
- Student.

Administrators can manage scheduling data and publish timetables.

Faculty members can view their own timetable and relevant notifications.

Students can view the published timetable associated with their academic year, semester, division, and batch.

Users must not be able to access unauthorized management functions by directly calling an API.

Implement appropriate authorization checks on the backend, not only by hiding frontend buttons.

Do not expose private faculty or student information unnecessarily.

# PHASE 17 — ANALYTICS AND REPORTS

Provide useful academic scheduling analytics based on saved data.

Include:

- Faculty workload distribution.
- Classroom utilization.
- Laboratory utilization.
- Subject-hour completion.
- Unassigned sessions.
- Free periods.
- Division-wise timetable coverage.
- Scheduling conflict counts.
- Teacher workload limit violations.

Use clear charts and summary cards.

Make chart data filterable by academic year, semester, department, and date range where applicable.

Ensure all analytics are derived from real data.

Avoid presenting invented metrics or misleading percentages.

# PHASE 18 — PROJECT STRUCTURE AND CODE QUALITY

Organize the repository into a clear, maintainable structure appropriate to the existing technology stack.

Separate concerns such as:

- Frontend pages and reusable UI components.
- API clients and service functions.
- Backend routes or controllers.
- Business services.
- Scheduling engine.
- Constraint validation.
- Database models and migrations.
- Authentication and authorization.
- Export generation.
- Academic calendar and holiday services.
- Notifications.
- Tests.
- Configuration and documentation.

Use clear file names, consistent naming conventions, and reusable components.

Do not put the entire application in one large file.

Avoid circular dependencies, duplicated scheduling rules, repeated validation logic, and unnecessary abstraction.

Move files only when needed and update all affected imports, paths, configuration references, and build scripts.

Do not delete files simply because they appear unused without verifying their purpose.

Keep secrets, passwords, API keys, and environment-specific configuration out of source control.

Provide an appropriate `.env.example` when the application requires environment variables.

Add or update the README with accurate installation, configuration, database setup, development, testing, and deployment instructions.

Do not document features as completed unless they are actually implemented.

# PHASE 19 — TESTING AND PRODUCTION READINESS

Test the application systematically.

## Scheduling tests

Verify that:

- A teacher never has overlapping sessions.
- A classroom never has overlapping sessions.
- A division never has overlapping sessions.
- Teachers can teach multiple subjects without incorrect restrictions.
- Required lecture and practical hours are respected.
- Breaks are protected.
- Holidays are respected.
- Room capacities and types are validated.
- Teacher availability is enforced.
- Impossible scheduling requirements are reported correctly.
- Manual edits trigger revalidation.
- Regeneration preserves applicable fixed sessions.
- Exported timetables match the saved timetable.

## Application tests

Test:

- Authentication and authorization.
- Database persistence after restarting the application.
- CRUD operations for teachers, subjects, rooms, and divisions.
- Import validation and error handling.
- All export formats.
- Faculty timetable filtering.
- Holiday management.
- Notifications and unread states.
- Version history and restoration.
- Responsive layouts.
- Error handling and empty states.

Run the project's existing test suite and build commands.

Fix regressions introduced by the implementation. Do not claim that tests passed unless they were actually run successfully.

# PHASE 20 — IMPLEMENTATION STRATEGY

Execute the work in manageable stages:

**Stage 1:** Repository inspection, architecture review, and project restructuring.

**Stage 2:** UI redesign, Slotify branding, navigation, and interactive dashboard.

**Stage 3:** Persistent data management for teachers, subjects, rooms, divisions, and time slots.

**Stage 4:** Scheduling constraints, conflict detection, optimization, and generation workflow.

**Stage 5:** Recess management, faculty availability, and classroom allocation.

**Stage 6:** Faculty timetable directory, individual schedules, and academic calendar.

**Stage 7:** PDF, Excel, CSV, and Word exports.

**Stage 8:** Notifications, authentication, permissions, analytics, and version history.

**Stage 9:** Automated tests, integration checks, bug fixes, and documentation.

Adapt this order if the existing architecture requires dependencies to be implemented differently.

Prioritize a fully working core scheduling workflow over superficial completion of every screen.

If the full scope cannot be completed in one pass, implement complete, tested vertical slices and maintain a clear list of remaining tasks. Never replace unfinished backend behavior with mock data just to make a page look finished.

# FINAL ACCEPTANCE CRITERIA

The project is ready for review when:

1. The existing application has been transformed into Slotify.
2. The UI consistently uses the requested soft campus-inspired Swiss-grid theme.
3. Administrators can manage the relevant scheduling data.
4. Teachers can be associated with multiple qualified subjects.
5. Classroom assignments are visible and validated.
6. Recess and holiday periods are respected by the scheduling engine.
7. Faculty timetables are accessible through a searchable faculty directory.
8. Timetable generation validates hard constraints and explains unsatisfied requirements.
9. Administrators can review, edit, validate, and save schedules.
10. Timetables can be exported to PDF, Excel, CSV, and Word.
11. Notifications and version history operate on persisted data.
12. The project structure is clean and maintainable.
13. Critical workflows have been tested.
14. Installation and deployment requirements are documented accurately.

## FINAL INSTRUCTION

Begin by inspecting the actual repository and understanding the current code.

Then implement the features directly in the existing project, making changes carefully and testing each stage.

Do not merely return recommendations, create static mockups, or provide code snippets without integrating them.

Preserve existing working functionality, avoid unnecessary rewrites, and prioritize correctness, maintainability, data integrity, and a consistent user experience.

At the end, provide a concise implementation report covering:
- Features implemented.
- Important files created or modified.
- Database changes and migrations.
- Tests and build commands executed.
- Any external configuration still required.
- Features that remain incomplete.
- Exact commands to run the updated application locally.
