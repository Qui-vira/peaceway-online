# Handoff

## 1. Goal
Extend the Telegram bot with a staff checklist and meeting tracker (per the spec agreed with the owner), reusing the permission service, role gating, and the audit_logs append-only pattern. This is the current thread. It follows a completed run of DB-layer access-control hardening (Gates 1 to 6, superuser removal, clinical RLS, dispatch portal) that is already live in prod.

## 2. Current state — SHIPPED TO PROD (2026-07-21)
- Prod alembic head: **`c7e4d9b1a3f2`** (confirmed from the DB). App runs as non-superuser `peaceway_app`; migrations run privileged via `MIGRATION_DATABASE_URL`. RLS live on clinical tables and `rider_assignments`.
- **#17 MERGED** (`a5aa4aef`, squash) — schema slice: migration `b6d3f8a2c1e5` (4 tables + append-only trigger + own-completion CHECK), `pa` role, `/chatid`.
- **#18 MERGED** (`92384ad7`, squash) — behaviour + orientation + daily nudge. Note: #18 was rebased onto the squashed `main` before merge (the stacked-squash otherwise re-applied the schema commit → conflict). See §7–§8 for contents.
- **Web** auto-deployed, ran both migrations to head `c7e4d9b1a3f2`, booted clean. **Worker** deployed via `railway up --service worker` (it does NOT auto-deploy — see §5) — new cron jobs confirmed registered (`checklist_jobs_started`, in-container module has nudge/morning/sunday jobs), `/health` ok.
- **Seeded prod** (idempotent, via `railway connect Postgres` piping SQL): **12 orientation topics + 20 checklist templates** (verified counts; 2nd run inserted 0).
- **`STAFF_GROUP_CHAT_ID` still NOT set** — the ONE remaining item. Group posts (Monday 08:00 prep) skip cleanly until then; everything else (checklists, nudge, orientation, per-person DMs) works now. Owner runs `/chatid` in the staff group → send the value → set on web + worker via `railway variables`.
- `STAFF_NUDGE_HOUR` unset → defaults to 18 (Lagos). Fine as-is.
- Owner-approved rules (all implemented): `pa` = view_checklist_status + complete_own_checklist + set_meeting_example; append-only instances with supersedes_id; Africa/Lagos due_date; decision_text scanned for NG phone / 10+ digit run before posting; group status AGGREGATE only; Monday 08:00 group prep = open-decisions block; orientation topic computed from rotation (never manual), inactive topics skipped-with-audit; owner-only topic swap logged with reason; nudge private-only, one-per-person-per-day, silent on completion.

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
- New tables whose rows are inserted by a trigger or raw SQL need a DB-level `gen_random_uuid()` default on id (the model's Python uuid4 default does not apply). Done on `checklist_instances.id` and `orientation_topics.id` (NOT on `checklist_templates.id` — seed SQL supplies `gen_random_uuid()` explicitly).
- **The `worker` service does NOT auto-deploy on push — only `web` does.** After merging, `web` redeployed but `worker` stayed on old code (new cron jobs missing from the live scheduler — a silent failure). Deploy it manually: `railway up --service worker` (`.railwayignore` already trims to the lean Python backend). Verify: `railway ssh --service worker "/opt/venv/bin/python -c 'import app.scheduler.jobs as j; print(hasattr(j,\"checklist_nudge\"))'"` and the `checklist_jobs_started` log. `railway redeploy` only restarts the OLD image.
- Stacked squash-merge gotcha: after squash-merging the base PR, the stacked branch still carries the original (un-squashed) base commit, so retargeting it to `main` conflicts. Fix: `git rebase --onto origin/main <old-base-tip> <branch>`, force-push, then merge.
- `railway domain` only CREATES (bare invocation generates another); no CLI/API delete with the CLI's session token (403/1010) — remove a service domain from the Railway dashboard.

## 7. Behaviour build (this session) — done on `feat/staff-checklist-behaviour`
New: `app/core/timeutil.py` (Lagos date/now), `app/services/checklist.py` (templates_due, generate_instances idempotent, latest_states, complete_item append-only+audit+own-only guard, aggregate_status, per_person_status, open/overdue/closed decisions), `app/services/checklist_messages.py` (group-safe builders — counts/names only), `app/services/decision_scan.py` (NG phone + 10+ digit scan), `app/bot/staff/checklist.py` (/checklist, /status group-vs-private, /meeting, /decision FSM with scan→rephrase), `scripts/seed_checklist.py` (19 starter templates incl. PA's 3 meeting-prep), `tests/test_checklist.py` (21), `tests/test_checklist_pg.py` (2, trigger).
Modified: `app/scheduler/jobs.py` (3 cron jobs, Africa/Lagos: morning 06:00, Mon 08:00 prep, Mon 18:00 owner summary — verified they register), `app/bot/staff/states.py` (ChecklistFlow, DecisionFlow), `app/bot/dispatcher.py` (router), `app/services/checklist.py`.
Status: MERGED (#18) + DEPLOYED + SEEDED in prod. `/status` regular-staffer branch shows own count only (team aggregate gated behind view_checklist_status). Group posts skip when STAFF_GROUP_CHAT_ID unset (still unset — see §2/§6).

## 8. Orientation topics + daily nudge (same branch, from Marketing-Team-Plan docx)
New migration `c7e4d9b1a3f2` (down_revision b6d3f8a2c1e5): `orientation_topics` table + `meetings.topic_id/example_text/swapped_from_topic_id/swapped_by`. Verified on real PG via `upgrade head`.
New: `app/services/orientation.py` (ANCHOR_MONDAY=2026-07-27; week_index; computed_topic — skips inactive + returns them so caller audits; ensure_week_meeting; set_example; swap_topic; add_topic/set_topic_active), `app/bot/staff/orientation.py` (/orientation view + PA example FSM + owner swap FSM + /orientationtopics manage), `scripts/seed_orientation.py` (12 topics from §10.5), `tests/test_orientation.py` (9).
Modified: `app/models/checklist.py` (OrientationTopic + Meeting cols) + `__init__`, `app/core/rbac.py` (3 perms: manage_orientation_topics/swap_meeting_topic = owner via wildcard, set_meeting_example added to PA; PA menu +Orientation), `app/core/config.py` (`staff_nudge_hour: int = 18`), `app/scheduler/jobs.py` (2 jobs: `checklist_nudge` weekdays @staff_nudge_hour — DMs only staff with pending, one-per-day via checklist_nudge_sent audit, never group; `checklist_sunday_prep` Sun 18:00 — computes next week's topic, ensures meeting, DMs PA to fill example), `app/services/checklist.py` (admins_with_pending, nudged_admin_ids), `app/bot/staff/states.py` (OrientationFlow), `app/bot/dispatcher.py` (router), `scripts/seed_checklist.py` (CM twice-daily = 2 rows morning/evening).
Rules honoured: topic computed from rotation (never manual), inactive topics skipped-with-audit (never silent), swaps audited with reason, nudge private-only + one-per-person-per-day + silence on completion. Suite: 224 passed (incl. PG). Rotation dry-run wks 0–13 confirmed. Twelve topics are in `scripts/seed_orientation.py`.

## 6. Next steps
1. **Only open item: set `STAFF_GROUP_CHAT_ID`.** Owner adds the bot to the staff group, runs `/chatid` there, sends the id → set it on BOTH `web` and `worker` via `railway variables --set STAFF_GROUP_CHAT_ID=<id> --service <svc>` (the worker restart is fine). Until then, only the Monday 08:00 group prep is dormant; everything else is live.
2. First real cron fires: morning generate+DM at 06:00 Lagos (05:00 UTC); nudge weekdays 18:00 Lagos (17:00 UTC); Sunday prep Sun 18:00 Lagos. Spot-check the worker logs after the first morning run for `checklist_morning_sent` / any send failures, and confirm staff received DMs.
3. Optional polish (not required): a "close decision" flow (sets `MeetingDecision.status='closed'` + `closed_at`) so the Monday owner summary's "decisions closed this week" populates; currently only overdue/open decisions surface.

Everything in the original build spec (checklists, /status, /meeting, /decision, Monday jobs, orientation rotation, nudge, seeds, tests) is implemented, tested (224 green incl. PG), merged (#17+#18), and deployed.
