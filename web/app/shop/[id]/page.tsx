"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, Check } from "lucide-react";
import { isNotFound } from "@/lib/api";
import { getProduct, type Product } from "@/lib/api/catalog";
import { addToCart, getCart } from "@/lib/cart";
import { AppShell } from "@/components/app/app-shell";
import { LoadFailed, Spinner } from "@/components/app/ui";
import { DrugIcon } from "@/components/app/drug-icons";
import { TactileButton, TactileLink } from "@/components/app/tactile-button";

const FOCUS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0b0c09]";

function fmt(price: string | null) {
  if (!price) return "-";
  return `₦${Number(price).toLocaleString("en-NG")}`;
}

export default function ProductDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  // Distinct from `product === null`, which renders "not found".
  const [failed, setFailed] = useState(false);
  const [added, setAdded] = useState(false);
  const [cartCount, setCartCount] = useState(0);

  useEffect(() => {
    setCartCount(getCart().reduce((s, c) => s + c.quantity, 0));
    if (!id) return;
    getProduct(id)
      .then((p) => setProduct(p))
      .catch((e) => {
        // Only a 404 means this medicine does not exist. Anything else and we
        // simply could not look - saying "not found" would be a claim about
        // the catalogue we have no basis for.
        if (isNotFound(e)) setProduct(null);
        else setFailed(true);
      })
      .finally(() => setLoading(false));
  }, [id]);

  function handleAdd() {
    if (!product?.selling_price || !product.is_in_stock) return;
    const updated = addToCart({
      product_id: product.id,
      product_name: product.name,
      selling_price: Number(product.selling_price),
    });
    setCartCount(updated.reduce((s, c) => s + c.quantity, 0));
    setAdded(true);
    setTimeout(() => setAdded(false), 1500);
  }

  if (loading)
    return (
      <AppShell back={{ fallbackHref: "/shop" }}>
        <Spinner />
      </AppShell>
    );

  if (failed) {
    return (
      <AppShell back={{ title: "Product", fallbackHref: "/shop" }}>
        <div className="px-5 pt-6">
          <LoadFailed what="this medicine" onRetry={() => window.location.reload()} />
        </div>
      </AppShell>
    );
  }

  if (!product) {
    return (
      <AppShell back={{ title: "Product", fallbackHref: "/shop" }}>
        <div className="flex flex-col items-center gap-4 px-5 py-20 text-center">
          <p className="text-[#b1bdb0]">Product not found.</p>
          <Link href="/shop" className={`rounded text-sm text-emerald-400 hover:underline ${FOCUS}`}>
            ← Back to Shop
          </Link>
        </div>
      </AppShell>
    );
  }

  const detailRows = [
    { label: "Category", value: product.category },
    { label: "Dosage form", value: product.dosage_form },
    { label: "Generic name", value: product.generic_name },
    { label: "Brand name", value: product.brand_name },
  ].filter((r) => r.value);

  return (
    <AppShell back={{ title: product.name, fallbackHref: "/shop" }}>
      <div className="mx-auto w-full max-w-5xl px-5 pb-10 pt-2 md:px-8 md:pt-6">
        <div className="grid gap-8 md:grid-cols-[minmax(0,360px)_minmax(0,1fr)] md:gap-10">
          {/* Media panel (sticky on desktop) */}
          <div className="flex flex-col items-center gap-4 md:sticky md:top-24 md:self-start">
            <div className="relative flex aspect-square w-full max-w-[220px] items-center justify-center rounded-3xl border border-emerald-500/25 bg-emerald-500/10 shadow-[0_0_44px_-6px_rgba(26,163,90,0.5)] md:max-w-none">
              <div
                aria-hidden
                className="pointer-events-none absolute inset-0 rounded-3xl"
                style={{ background: "radial-gradient(circle at 50% 40%, rgba(52,217,138,0.18), transparent 70%)" }}
              />
              <DrugIcon form={product.dosage_form ?? undefined} size={88} />
            </div>
          </div>

          {/* Info + CTA */}
          <div className="space-y-6">
            <div>
              <h1 className="font-syne text-[26px] font-bold leading-tight text-white md:text-[32px]">
                {product.name}
              </h1>
              {product.strength && <p className="mt-1 text-sm text-white/50">{product.strength}</p>}
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <p className="text-2xl font-bold text-emerald-400">{fmt(product.selling_price)}</p>
                {!product.is_in_stock && (
                  <span className="rounded-full border border-red-500/25 bg-red-500/10 px-3 py-1 text-[12px] font-medium text-red-400">
                    Out of stock
                  </span>
                )}
              </div>
            </div>

            {product.requires_prescription && (
              <div className="flex items-start gap-2.5 rounded-xl border border-amber-500/25 bg-amber-500/[0.08] px-3.5 py-2.5">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                <p className="text-[12px] leading-relaxed text-amber-300/80">
                  This medicine requires a valid prescription. Our pharmacist will verify before
                  fulfilling your order.
                </p>
              </div>
            )}

            {/* CTA */}
            <div className="space-y-2">
              {product.is_in_stock ? (
                <>
                  {added ? (
                    <div className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-2xl bg-emerald-500/20 text-sm font-bold text-emerald-400 sm:w-auto sm:min-w-[240px]">
                      <Check className="h-4 w-4" /> Added to cart
                    </div>
                  ) : (
                    <TactileButton onClick={handleAdd} className="w-full sm:w-auto sm:min-w-[240px]">
                      Add to Cart
                    </TactileButton>
                  )}
                  {cartCount > 0 && (
                    <TactileLink
                      variant="secondary"
                      href="/cart"
                      className="w-full sm:w-auto sm:min-w-[240px]"
                    >
                      View Cart ({cartCount})
                    </TactileLink>
                  )}
                </>
              ) : (
                <Link
                  href="/request"
                  className={`inline-flex min-h-[48px] w-full items-center justify-center rounded-xl border border-emerald-500/30 px-6 text-sm font-semibold text-emerald-400 transition hover:bg-emerald-500/10 sm:w-auto sm:min-w-[240px] ${FOCUS}`}
                >
                  Request this medicine instead
                </Link>
              )}
            </div>

            {/* Details */}
            {detailRows.length > 0 && (
              <div className="divide-y divide-white/6 rounded-2xl border border-white/8 bg-white/[0.04]">
                {detailRows.map((r) => (
                  <div key={r.label} className="flex justify-between gap-4 px-4 py-3">
                    <span className="text-[12px] text-[#b1bdb0]">{r.label}</span>
                    <span className="text-right text-[13px] text-white/80">{r.value}</span>
                  </div>
                ))}
              </div>
            )}

            {product.description && (
              <div className="space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#b1bdb0]">
                  Description
                </p>
                <p className="text-sm leading-relaxed text-white/60">{product.description}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
