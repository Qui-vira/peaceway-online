import { compliance, siteConfig } from "@/lib/constants";

/**
 * Statutory homepage disclosures for an Electronic Pharmaceutical Service
 * Provider.
 *
 * The Electronic Pharmacy Regulations 2026 require an EPSP to display, on its
 * homepage: the authorised PCN logo, the online pharmacy licence number, the
 * EPSP registration number, and a declaration about prescription-only medicines.
 *
 * This component renders all four, and is deliberately built so that the
 * unfinished parts read as unfinished:
 *
 *   - Numbers come from `compliance` in lib/constants.ts and are `null` until
 *     issued. A null renders "Application in progress", not a dash and not a
 *     fabricated number. Someone reading this page should be able to tell the
 *     difference between "licensed, here is the number" and "not yet licensed",
 *     because that difference is the entire point of the disclosure.
 *   - The PCN logo is not rendered at all until `pcnLogoApproved` is true.
 *     Showing a regulator's mark before the licence is granted claims an
 *     approval that does not exist; an empty slot is the honest state.
 *
 * Server component: this is static regulatory text and must be in the HTML for
 * a crawler, a regulator, or a customer with JavaScript disabled.
 */
export function RegulatoryNotice(): JSX.Element {
  return (
    <section
      aria-labelledby="regulatory-heading"
      className="border-t border-white/8 bg-[#0b0c09] px-5 py-10 md:px-8"
    >
      <div className="mx-auto max-w-6xl space-y-6">
        <h2
          id="regulatory-heading"
          className="text-2xs font-semibold uppercase tracking-[0.18em] text-[#b1bdb0]"
        >
          Regulatory information
        </h2>

        <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
          <RegulatoryItem
            label="Operating pharmacy"
            value={siteConfig.address}
          />
          <RegulatoryItem
            label="Online pharmacy licence number"
            value={compliance.pharmacyLicenceNumber}
          />
          <RegulatoryItem
            label="EPSP registration number"
            value={compliance.epspRegistrationNumber}
          />
          {/* `notPublished` because the pharmacy has a Superintendent
              Pharmacist - only the name has yet to be entered here. Labelling
              it "Application in progress" would assert the opposite. */}
          <RegulatoryItem
            label={siteConfig.superintendentPharmacistLabel}
            value={compliance.superintendentPharmacistName}
            notPublished
          />
          <RegulatoryItem
            label="Superintendent Pharmacist PCN number"
            value={compliance.superintendentPharmacistPcnNumber}
            notPublished
          />
        </dl>

        {/* The prescription declaration is the one disclosure that is fully
            true today, so it is stated plainly rather than hedged. */}
        <p className="max-w-3xl text-xs-plus leading-relaxed text-[#dcdddb]">
          {compliance.prescriptionDeclaration}
        </p>

        {compliance.pcnLogoApproved ? (
          // TODO: drop the authorised PCN logo asset in here once the licence is
          // issued and the PCN has approved its display. Keep the alt text
          // factual - it identifies the regulator, it is not a trust badge.
          <p className="text-2xs text-[#868f85]">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/branding/pcn-authorised-logo.png"
              alt="Pharmacists Council of Nigeria"
              width={96}
              height={96}
            />
          </p>
        ) : (
          <p className="text-2xs leading-relaxed text-[#868f85]">
            The Pharmacists Council of Nigeria logo is displayed here once the
            online pharmacy licence is issued and its use is authorised.
          </p>
        )}
      </div>
    </section>
  );
}

/**
 * One disclosure row. A missing value is labelled, never blank and never
 * invented - see the component docblock for why that distinction matters.
 */
function RegulatoryItem({
  label,
  value,
  notPublished = false
}: {
  label: string;
  value: string | null;
  /** The fact exists, it is just not entered here yet. See the call sites. */
  notPublished?: boolean;
}): JSX.Element {
  const pending = value === null;
  const pendingText = notPublished
    ? compliance.notPublishedLabel
    : compliance.pendingLabel;
  return (
    <div>
      <dt className="text-2xs uppercase tracking-wide text-[#868f85]">{label}</dt>
      <dd
        className={
          pending
            ? "mt-0.5 text-xs-plus italic text-[#868f85]"
            : "mt-0.5 text-xs-plus text-[#dcdddb]"
        }
      >
        {pending ? pendingText : value}
      </dd>
    </div>
  );
}
