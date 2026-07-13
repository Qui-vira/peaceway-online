"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ShoppingCart, AlertTriangle } from "lucide-react";
import { getProduct, type Product } from "@/lib/api/catalog";
import { addToCart, getCart } from "@/lib/cart";
import { AppShell } from "@/components/app/app-shell";
import { Spinner } from "@/components/app/ui";
import { DrugIcon } from "@/components/app/drug-icons";

function fmt(price: string | null) {
  if (!price) return "-";
  return `₦${Number(price).toLocaleString("en-NG")}`;
}

export default function ProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [added, setAdded] = useState(false);
  const [cartCount, setCartCount] = useState(0);

  useEffect(() => {
    setCartCount(getCart().reduce((s, c) => s + c.quantity, 0));
    if (!id) return;
    getProduct(id)
      .then((p) => setProduct(p))
      .catch(() => setProduct(null))
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

  if (loading) return <AppShell><Spinner /></AppShell>;

  if (!product) {
    return (
      <AppShell>
        <div className="flex flex-col items-center gap-4 px-5 py-20 text-center">
          <p className="text-white/60">Product not found.</p>
          <Link href="/shop" className="text-sm text-emerald-400 hover:underline">← Back to Shop</Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6 pb-8">
        {/* Sub-header */}
        <div className="flex items-center justify-between px-5 pt-8">
          <Link
            href="/shop"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5"
          >
            <ArrowLeft className="h-4 w-4 text-white/70" />
          </Link>
          {cartCount > 0 && (
            <Link
              href="/cart"
              className="relative flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5"
            >
              <ShoppingCart className="h-4 w-4 text-white/70" />
              <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[9px] font-bold text-black">
                {cartCount}
              </span>
            </Link>
          )}
        </div>

        {/* Hero */}
        <div className="flex flex-col items-center gap-4 px-5">
          <div className="flex h-28 w-28 items-center justify-center rounded-2xl border border-emerald-500/25 bg-emerald-500/10">
            <DrugIcon form={product.dosage_form ?? undefined} size={64} />
          </div>
          <div className="text-center">
            <h1 className="font-syne text-[22px] font-bold leading-tight text-white">
              {product.name}
            </h1>
            {product.strength && (
              <p className="mt-0.5 text-sm text-white/50">{product.strength}</p>
            )}
          </div>
          <p className="text-2xl font-bold text-emerald-400">{fmt(product.selling_price)}</p>
          {!product.is_in_stock && (
            <span className="rounded-full border border-red-500/25 bg-red-500/10 px-3 py-1 text-[12px] font-medium text-red-400">
              Out of stock
            </span>
          )}
        </div>

        {/* Details */}
        <div className="mx-5 rounded-2xl border border-white/8 bg-white/4 divide-y divide-white/6">
          {[
            { label: "Category", value: product.category },
            { label: "Dosage form", value: product.dosage_form },
            { label: "Generic name", value: product.generic_name },
            { label: "Brand name", value: product.brand_name },
          ]
            .filter((r) => r.value)
            .map((r) => (
              <div key={r.label} className="flex justify-between px-4 py-3">
                <span className="text-[12px] text-white/40">{r.label}</span>
                <span className="text-[13px] text-white/80">{r.value}</span>
              </div>
            ))}
        </div>

        {product.description && (
          <div className="mx-5 space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/40">
              Description
            </p>
            <p className="text-sm leading-relaxed text-white/60">{product.description}</p>
          </div>
        )}

        {product.requires_prescription && (
          <div className="mx-5 flex items-start gap-2.5 rounded-xl border border-amber-500/25 bg-amber-500/8 px-3.5 py-2.5">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
            <p className="text-[11px] leading-relaxed text-amber-300/80">
              This medicine requires a valid prescription. Our pharmacist will verify before fulfilling your order.
            </p>
          </div>
        )}

        {/* CTA */}
        <div className="px-5 space-y-2">
          {product.is_in_stock ? (
            <>
              <button
                onClick={handleAdd}
                className={`w-full rounded-xl py-3.5 text-sm font-semibold transition ${
                  added
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-emerald-500 text-black hover:bg-emerald-400"
                }`}
              >
                {added ? "Added to cart ✓" : "Add to Cart"}
              </button>
              {cartCount > 0 && (
                <Link
                  href="/cart"
                  className="block w-full rounded-xl border border-white/10 py-3 text-center text-sm text-white/50 transition hover:border-white/20"
                >
                  View Cart ({cartCount})
                </Link>
              )}
            </>
          ) : (
            <Link
              href="/request"
              className="block w-full rounded-xl border border-emerald-500/30 py-3.5 text-center text-sm font-semibold text-emerald-400 transition hover:bg-emerald-500/10"
            >
              Request this medicine instead
            </Link>
          )}
        </div>
      </div>
    </AppShell>
  );
}
