# Handoff

## 1. Goal
Extend the Telegram bot with a staff checklist and meeting tracker (per the spec agreed with the owner), reusing the permission service, role gating, and the audit_logs append-only pattern. This is the current thread. It follows a completed run of DB-layer access-control hardening (Gates 1 to 6, superuser removal, clinical RLS, dispatch portal) that is already live in prod.

## 2. Current state
- Prod alembic head: `a2f9d1c7b4e6`. App runs as non-superuser `peaceway_app`; migrations run privileged via `MIGRATION_DATABASE_URL`. RLS is live on clinical tables and `rider_assignments`.
- PR #17 (staff-checklist-schema) is OPEN, not merged. It is the schema slice only: migration `b6d3f8a2c1e5` (4 tables + append-only trigger + own-completion CHECK), the `pa` role, and the `/chatid` command. Branch-tested, NOT applied to prod. Held for owner approval of the migration.
- Behaviour + orientation are BUILT and SHIPPED as **PR #18** (`feat/staff-checklist-behaviour`, base `feat/staff-checklist-schema`): https://github.com/Qui-vira/peaceway-online/pull/18 — committed `c3794de2`, pushed. OPEN, NOT merged, NOT deployed (stacked on #17; migrations held for owner approval). Full suite 224 passed incl. the Postgres migration + append-only trigger tests. See §7–§8.
  - Merge/deploy path when approved: merge #17 then #18 → main (Railway); `railway run python scripts/seed_checklist.py` + `railway run python scripts/seed_orientation.py`; then `/chatid` → set `STAFF_GROUP_CHAT_ID` on worker + web.
- `STAFF_GROUP_CHAT_ID` is NOT set on prod. Needed only for group posts. Owner will create the group, add the bot, run `/chatid` after #17 merges, and send the value.
- Owner-approved decisions this session: `pa` role = view_checklist_status + complete_own_checklist only; append-only instances with supersedes_id; timezone Africa/Lagos config, derive due_date from Lagos local date (never `now().date()` on UTC); scan decision_text for Nigerian phone patterns and any 10+ digit run before it posts to the group (no name detection); group status is AGGREGATE only (completed X of Y, outstanding N across M people), per-person only in the owner DM and in PA private `/status`; Monday 08:00 group post keeps open-decisions block, no per-person; seed templates for every role.

## 3. Active files
- `app/models/checklist.py` (ChecklistTemplate, ChecklistInstance append-only, Meeting, MeetingDecision) + registered in `app/models/__init__.py`.
- `alembic/versions/b6d3f8a2c1e5_add_checklist_and_meeting_tracker.py`.
- `app/core/rbac.py` (PA role, 4 new perms, complete_own_checklist on all staff roles, PA menu).
- `app/bot/staff/chatid.py` + `app/bot/dispatcher.py` (router registered).
- Patterns to copy for the behaviour build: `app/scheduler/jobs.py` (APScheduler UTC in the worker `app/worker_app.py`; add cron jobs with Africa/Lagos tz), `app/models/ops.py` AuditLog + `deny_mutation` append-only trigger, `app/core/security.py` (has, get_role_keys, get_admin_id), `app/bot/staff/admins.py` and `app/bot/staff/riders.py` (handler + FSM pattern). Group target config: `staff_group_chat_id` in `app/core/config.py`. Staff DMs via `bot.send_message(admin.telegram_id, ...)`.

## 4. Changes made
- This session merged and deployed to prod, in order: #10 Phase 1 gates, #11 Gate 1 activation + write-path + backfill, #12 restricted app role + connection split (then the 1b cutover to `peaceway_app`), #13 actor context, #14 clinical RLS + break-glass, #15 dispatch portal (backend + Gate 5 RLS + rider frontend + proof-of-delivery), #16 rider management command.
- Seeded one rider in prod: Kehinde Damilare, kdammilare33@gmail.com, active.
- Open, unmerged: #17 (this thread's schema slice).

## 5. Failed attempts / gotchas
- Prod DB is internal (`postgres.railway.internal`), not reachable from a laptop.
- Cannot run the async seed scripts via `railway ssh` (the ssh shell is missing libstdc++ that greenlet needs). For one-off prod data, use `railway connect Postgres` and pipe SQL. To run app code in-container use `/opt/venv/bin/python` (base nix python lacks the app deps; `python -m alembic` fails, no __main__).
- The browser screenshot tool hangs on the site's fixed film-grain overlay in the shared layout. Verify UI with get_page_text and read_console_messages instead.
- Alembic runs multi-statement DDL through asyncpg, which rejects multiple statements per execute. Split trigger/function/view DDL into one statement per `op.execute` (see `app/core/gate_ddl.py`).
- New tables whose rows are inserted by a trigger or raw SQL need a DB-level `gen_random_uuid()` default on id (the model's Python uuid4 default does not apply). Already done on `checklist_instances.id`.

## 7. Behaviour build (this session) — done on `feat/staff-checklist-behaviour`
New: `app/core/timeutil.py` (Lagos date/now), `app/services/checklist.py` (templates_due, generate_instances idempotent, latest_states, complete_item append-only+audit+own-only guard, aggregate_status, per_person_status, open/overdue/closed decisions), `app/services/checklist_messages.py` (group-safe builders — counts/names only), `app/services/decision_scan.py` (NG phone + 10+ digit scan), `app/bot/staff/checklist.py` (/checklist, /status group-vs-private, /meeting, /decision FSM with scan→rephrase), `scripts/seed_checklist.py` (19 starter templates incl. PA's 3 meeting-prep), `tests/test_checklist.py` (21), `tests/test_checklist_pg.py` (2, trigger).
Modified: `app/scheduler/jobs.py` (3 cron jobs, Africa/Lagos: morning 06:00, Mon 08:00 prep, Mon 18:00 owner summary — verified they register), `app/bot/staff/states.py` (ChecklistFlow, DecisionFlow), `app/bot/dispatcher.py` (router), `app/services/checklist.py`.
NOT done: uncommitted, not pushed, no stacked PR opened, `scripts/seed_checklist.py` not run in prod. `/status` regular-staffer branch shows own count only (team aggregate gated behind view_checklist_status). Group posts skip when STAFF_GROUP_CHAT_ID unset.

## 8. Orientation topics + daily nudge (same branch, from Marketing-Team-Plan docx)
New migration `c7e4d9b1a3f2` (down_revision b6d3f8a2c1e5): `orientation_topics` table + `meetings.topic_id/example_text/swapped_from_topic_id/swapped_by`. Verified on real PG via `upgrade head`.
New: `app/services/orientation.py` (ANCHOR_MONDAY=2026-07-27; week_index; computed_topic — skips inactive + returns them so caller audits; ensure_week_meeting; set_example; swap_topic; add_topic/set_topic_active), `app/bot/staff/orientation.py` (/orientation view + PA example FSM + owner swap FSM + /orientationtopics manage), `scripts/seed_orientation.py` (12 topics from §10.5), `tests/test_orientation.py` (9).
Modified: `app/models/checklist.py` (OrientationTopic + Meeting cols) + `__init__`, `app/core/rbac.py` (3 perms: manage_orientation_topics/swap_meeting_topic = owner via wildcard, set_meeting_example added to PA; PA menu +Orientation), `app/core/config.py` (`staff_nudge_hour: int = 18`), `app/scheduler/jobs.py` (2 jobs: `checklist_nudge` weekdays @staff_nudge_hour — DMs only staff with pending, one-per-day via checklist_nudge_sent audit, never group; `checklist_sunday_prep` Sun 18:00 — computes next week's topic, ensures meeting, DMs PA to fill example), `app/services/checklist.py` (admins_with_pending, nudged_admin_ids), `app/bot/staff/states.py` (OrientationFlow), `app/bot/dispatcher.py` (router), `scripts/seed_checklist.py` (CM twice-daily = 2 rows morning/evening).
Rules honoured: topic computed from rotation (never manual), inactive topics skipped-with-audit (never silent), swaps audited with reason, nudge private-only + one-per-person-per-day + silence on completion. Suite: 224 passed (incl. PG). Rotation dry-run wks 0–13 confirmed. Twelve topics are in `scripts/seed_orientation.py`.

## 6. Next steps
1. On owner approval, merge #17 (applies migration `b6d3f8a2c1e5`, ships `/chatid`, seeds `pa` role). Verify on prod: revision, tables, append-only trigger, `/health`.
2. Get `STAFF_GROUP_CHAT_ID` from the owner (via `/chatid`) and set it on the worker + web services.
3. Build the behaviour PR: morning generator (Lagos due_date, idempotent one pending row per assignment), DM per-item buttons writing a completion/skip + an audit_logs row (own-only, DB CHECK already enforces), `/checklist`, `/status` (aggregate in group, per-person in private for PA/owner via view_checklist_status), `/meeting`, `/decision` (System Owner, with the digit/phone scan returning a rephrase prompt), Monday 08:00 group prep (open decisions with owner + days outstanding), Monday 18:00 owner DM (per-person completion, skips with reasons, decisions closed/overdue), and a `scripts/seed_checklist.py` seeding the PA's three meeting-prep items plus starter items per role. Add a group message-builder module that only accepts names/counts/decision text so no customer field can appear, with a test asserting the output. Register cron jobs in `start_scheduler()`.
4. Tests to add (from the spec): completion writes the row + audit; completing another person's item rejected; PA marking another's item rejected; group message contains no customer field; update/delete on a completion row rejected; Monday prep lists a decision overdue by 7+ days.
