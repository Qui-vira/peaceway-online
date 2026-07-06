# Peaceway Sourcing Pilot Runbook

## Purpose

Validate the new out-of-stock rescue workflow without pretending it is already a full production network.

## Brutal truth

- If partner stock, batch standard, or pickup readiness are not actually confirmed, do not promise speed to the customer.
- If a partner cannot maintain the verification standard, they should not be used in the pilot.
- The pilot succeeds by proving control, not by creating attractive screens.

## Minimum pilot path

1. Peaceway receives an order for an item that is not in stock locally.
2. The system creates the order and marks it for sourcing instead of payment.
3. Staff assigns the request to an approved partner.
4. The partner confirms:
   - quantity
   - price
   - expiry or batch standard
   - ready-for-pickup time
5. Only after confirmation does Peaceway communicate a real ETA.
6. Staff marks the package as pack ready and confirms pickup code generation.
7. Dispatch is assigned.
8. Pickup is verified.
9. Delivery is completed under Peaceway tracking.

## Admin surfaces

- `/admin/sourcing`
- `/admin/dispatch`

## Customer truth standard

Use honest language:

- Ordered through Peaceway
- Fulfilled by approved partner
- Verified by Peaceway
- Delivered under Peaceway tracking

Do not hide partner fulfilment if hiding it would create trust risk.

## Before live pilot

1. Run the sourcing migration.
2. Create at least one real approved wholesaler record and one fallback partner record.
3. Confirm the partner knows how pickup verification will work.
4. Confirm who owns:
   - partner assignment
   - batch or expiry confirmation
   - pack verification
   - dispatch assignment
   - delivery exception handling

## Exit criteria

The pilot is credible only if all of these are true:

- An out-of-stock order can move through the full sourcing lifecycle.
- Customer messaging does not overpromise before confirmation.
- Staff can see which orders are in sourcing.
- Dispatch only sees orders after pack-ready confirmation.
- Pickup and delivery can be evidenced.
