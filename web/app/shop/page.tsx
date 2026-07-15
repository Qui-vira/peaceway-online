"use client";

import { useEffect, useState, useCallback } from "react";
import { ShoppingCart, Search } from "lucide-react";
import Link from "next/link";
import { listCatalog, listCategories, type Product } from "@/lib/api/catalog";
import { addToCart, getCart, type CartItem } from "@/lib/cart";
import { AppShell } from "@/components/app/app-shell";
import { Spinner, EmptyState, SectionLabel } from "@/components/app/ui";
import { ProductCard } from "@/components/app/product-card";

type State = { kind: "loading" } | { kind: "ready"; products: Product[] };

const FOCUS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0b0c09]";

export default function ShopPage() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("All");
  const [cart, setCart] = useState<CartItem[]>([]);
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());
  const [categories, setCategories] = useState<string[]>(["All"]);

  useEffect(() => {
    setCart(getCart());
    listCategories()
      .then((cats) => setCategories(["All", ...cats]))
      .catch(() => setCategories(["All"]));
  }, []);

  const load = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const products = await listCatalog({
        q: q || undefined,
        category: category !== "All" ? category : undefined,
      });
      setState({ kind: "ready", products });
    } catch {
      setState({ kind: "ready", products: [] });
    }
  }, [q, category]);

  useEffect(() => {
    const t = setTimeout(load, 350);
    return () => clearTimeout(t);
  }, [load]);

  function handleAdd(p: Product) {
    if (!p.selling_price || !p.is_in_stock) return;
    const updated = addToCart({
      product_id: p.id,
      product_name: p.name,
      selling_price: Number(p.selling_price),
    });
    setCart(updated);
    setAddedIds((prev) => new Set([...prev, p.id]));
    setTimeout(() => {
      setAddedIds((prev) => {
        const next = new Set(prev);
        next.delete(p.id);
        return next;
      });
    }, 1500);
  }

  const cartCount = cart.reduce((s, c) => s + c.quantity, 0);

  return (
    <AppShell back={{ title: "Shop", fallbackHref: "/app" }}>
      <div className="mx-auto w-full max-w-6xl px-5 pb-10 md:px-8">
        {/* Search + mobile cart (desktop cart lives in the top nav) */}
        <div className="flex items-center gap-3 pt-5">
          <div className={`flex flex-1 items-center gap-3 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 focus-within:border-emerald-500/40 focus-within:ring-2 focus-within:ring-emerald-400/40`}>
            <Search className="h-4 w-4 shrink-0 text-[#b1bdb0]" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search medicines..."
              aria-label="Search medicines"
              className="min-w-0 flex-1 bg-transparent text-base text-white outline-none placeholder-[#b1bdb0] md:text-sm"
            />
          </div>
          {cartCount > 0 && (
            <Link
              href="/cart"
              aria-label={`Cart, ${cartCount} item${cartCount === 1 ? "" : "s"}`}
              className={`relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 transition hover:border-emerald-500/40 md:hidden ${FOCUS}`}
            >
              <ShoppingCart className="h-5 w-5 text-white/70" />
              <span className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-emerald-500 px-1 text-[10px] font-bold text-black">
                {cartCount}
              </span>
            </Link>
          )}
        </div>

        {/* Categories */}
        <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              aria-pressed={category === c}
              className={`inline-flex min-h-[38px] shrink-0 items-center rounded-full border px-4 text-[13px] font-medium transition ${
                category === c
                  ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-400"
                  : "border-white/10 bg-white/[0.04] text-white/55 hover:border-white/20 hover:text-white/80"
              } ${FOCUS}`}
            >
              {c}
            </button>
          ))}
        </div>

        {state.kind === "loading" && <Spinner />}

        {state.kind === "ready" && state.products.length === 0 && (
          <EmptyState
            icon={<Search className="h-6 w-6" />}
            title="No medicines found"
            message="Try a different search term or browse a different category."
          />
        )}

        {state.kind === "ready" && state.products.length > 0 && (
          <div className="mt-5">
            <SectionLabel>
              {state.products.length} product{state.products.length !== 1 ? "s" : ""}
            </SectionLabel>
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 md:gap-4 lg:grid-cols-4 xl:grid-cols-5">
              {state.products.map((p) => (
                <ProductCard key={p.id} product={p} added={addedIds.has(p.id)} onAdd={handleAdd} />
              ))}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
