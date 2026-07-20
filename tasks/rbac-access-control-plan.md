# PeaceWay — Access Control / RBAC Hardening Plan

Status: **Phase 1 built + proven on a branch DB (not yet applied to production).**
All decisions below are confirmed by the product owner.

## Confirmed decisions
- **Roles:** ADD only, delete/rename/reassign nothing. Add `marketing_strategist`,
  `content_creator`, `ads_specialist` (staff) and `dispatch_partner` (external).
  Keep all 8 existing staff roles incl. BOTH pharmacist tiers; keep `supplier`.
- **Permission matrix:** keep the existing code→DB seeding pattern (`app/core/rbac.py`
  is source, seeded into `roles`/`permissions`/`role_permissions`). Do NOT move to a
  DB-only matrix.
- **External roles:** `supplier` + new `dispatch_partner` via the partner-portal
  pattern (never merged into staff auth). `dispatcher` stays internal. Both dispatch
  roles get the masked delivery view.
- **Clinical safety:** keep `WILDCARD_EXCLUDES` on `approve_prescription`; extend the
  same exclude to every new terminal clinical permission added.
- **Enforcement:** hybrid, **triggers now**. REVOKE-from-app-role + clinical RLS move
  to the superuser-removal ticket (see below).
- **Dispatch staging:** block at `PICKED_UP`, not `RIDER_ASSIGNED`. Rider view surfaces
  `awaiting_pharmacist_verification` so nobody travels to a package that can't leave.
- **handling_flag:** stamped on `orders` on every line change, FROZEN at dispatch
  (regulatory: what the rider was told, not what current data implies).
- **amount_to_collect:** `total − sum(APPROVED payments)`, floored at 0. `total`
  includes the delivery fee; refunds do not net (no refund model exists yet).
- **Variant A** ships live; B needs a recorded pharmacist approval; C behind a flag.

## Dropped / moved out of this workstream
- **Gate 7 (discount-above-cap approval):** no discount feature exists. Building a
  discount model just to constrain it inverts the sequence. → recorded as an
  **acceptance criterion on the future discount-feature ticket**; the `approvals`
  table is already in place for it.
- **Gate 4 (clinical read via break_glass) + REVOKE hardening:** inert until the
  **superuser-removal ticket**, promoted to the **next ticket after Phase 1** (not
  background). Today the only barrier between clinical data and any role is Python in
  `has_permission` — one injection reaches everything. `break_glass_access` (+15-min
  expiry) is built and ready so the control ships the moment RLS can bite.

---

## Phase 1 — Non-negotiable DB gates ✅ BUILT & PROVEN (awaiting prod apply)
Migration [b3f1a2c9d7e4](../alembic/versions/b3f1a2c9d7e4_add_phase1_access_control_gates.py)
· DDL source of truth [app/core/gate_ddl.py](../app/core/gate_ddl.py) · models
[app/models/compliance.py](../app/models/compliance.py) · tests
[tests/test_gate_phase1_pg.py](../tests/test_gate_phase1_pg.py).

- [x] New tables: `prescription_verifications`, `dispensing_records`,
      `break_glass_access`, `approvals`, `community_members`.
- [x] `orders.handling_flag`; `audit_logs` extended (`actor_id`, `reason`,
      `before_value`, `after_value`, `ip`) — `audit_logs` is the authoritative log.
- [x] **Gate 1** trigger: POM order can't reach `DISPATCHED` / `PICKED_UP`+ without a
      current APPROVED verification by a real pharmacist (latest-row-wins).
- [x] **Line-binding** trigger: any `order_items` change supersedes a current approval
      → forces re-verify. Also stamps/freezes `handling_flag`.
- [x] **Gates 2 & 3** append-only triggers on `prescription_verifications`,
      `dispensing_records`, `audit_logs` (block owner + superuser).
- [x] **Gate 6** masked `dispatch_delivery_masked` view (no product fields).
- [x] Proof: 12/12 PG acceptance tests green via real `alembic upgrade head`;
      166/166 SQLite suite unaffected; migration up/down/up round-trips.
- [ ] **Apply to production** (awaiting go-ahead).

## Next ticket — Superuser removal (promoted; blocks Gate 4)
- [ ] Non-superuser app DB role + per-request `SET LOCAL app.current_actor`.
- [ ] REVOKE UPDATE/DELETE on the 3 append-only tables (defense-in-depth atop triggers).
- [ ] Clinical-field RLS keyed on `current_setting`; `break_glass_access` read path +
      audit; all-other-roles zero clinical read. Acceptance tests 4, 10.

## Phase 2 — Roles + shared permission service
- [ ] `app/core/rbac.py`: add the 3 new staff roles + their permission sets and any new
      permission keys; extend `WILDCARD_EXCLUDES` for new terminal clinical perms; seed.
- [ ] Single permission service used by web + bot; masked views + field masks
      (sales: no cost/margin/clinical; pharmacist: no revenue/margin/ad spend;
      marketing/ads: aggregate only). Acceptance tests 4, 7(n/a→discount ticket), 8.

## Phase 3 — External dispatch portal + Join button
- [ ] `dispatch_partner` external portal (partner-portal pattern), individual rider
      logins, masked view, assignment FK on `rider_assignments`, RLS terminal-status
      expiry (Gate 5), one-time proof-of-delivery code + geostamp. Tests 5, 6, 11.
- [ ] Supplier three-way match + out-of-band bank-detail change + owner approval.
- [ ] Join button (web + bot), Telegram deep link `?start=<surface>`, writes
      `community_members`; owner dashboard member vs non-member repeat rate. Variant A
      live; B/C behind flag (B gated on pharmacist approval). Test 12. (Invite link
      pending — comes after the gates pass.)

## Phase 4 — Docs
- [ ] README: permission model + how to add a role. Full acceptance suite green.

---
## Review
- Gate 1 line-binding gap (verify → mutate line → dispatch) found in review and closed
  with the `order_items` supersede trigger; confirmed T1h early-exit path behaves as
  intended (supersede row written, dispatch of OTC-only allowed via `has_pom=false`).
