import type { Zone } from "@/lib/api/customers";

/**
 * Delivery pricing, in one place.
 *
 * `/cart` and `/checkout` each used to declare `const DELIVERY_FEE = 500`, and
 * `app/api/v1/orders.py` declared a third copy. Meanwhile `/profile` showed the
 * customer the real per-area prices from `delivery_zones` - ₦700 to ₦3,500 -
 * so the app asked where you lived, held the correct price, and then quoted a
 * flat ₦500 that matched no zone it actually serves. Not a rounding error: a
 * Lekki delivery was under-quoted by ₦3,000.
 *
 * The price now has one source, `delivery_zones`, and both sides of the wire
 * resolve it the same way. The backend mirror of this logic is
 * `resolve_delivery_fee` in `app/api/v1/orders.py`; the two must agree, so
 * checkout sends the area it priced rather than letting the server re-derive it.
 */

/**
 * Used when an order names no area, or names one outside the served zones.
 *
 * Deliberately the most expensive real zone rather than a cheap round number:
 * under-quoting a delivery costs a refund, a phone call, and a customer who
 * concludes the pharmacy is not real. Over-quoting costs a conversation. Mirrors
 * `FALLBACK_DELIVERY_FEE` in `app/api/v1/orders.py`.
 */
export const FALLBACK_DELIVERY_FEE = 2500;

/**
 * Fee for *area*, matched case-insensitively against the zone list.
 *
 * Case-insensitive because the area arrives from a free-text-ish profile field,
 * not a foreign key. A zone with a null fee (the offline fallback list) is
 * treated as unpriced, not as free.
 */
export function feeForArea(zones: Zone[], area: string | null | undefined): number {
  if (!area) return FALLBACK_DELIVERY_FEE;
  const match = zones.find(
    (z) => z.name.trim().toLowerCase() === area.trim().toLowerCase()
  );
  return match?.fee ?? FALLBACK_DELIVERY_FEE;
}

export function formatNaira(n: number): string {
  return `₦${n.toLocaleString("en-NG")}`;
}
