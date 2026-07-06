"use client";

import { useEffect, useState, useCallback } from "react";
import { ShoppingCart, Search } from "lucide-react";
import Link from "next/link";
import { listCatalog, listCategories, type Product } from "@/lib/api/catalog";
import { addToCart, getCart, type CartItem } from "@/lib/cart";
import { AppShell } from "@/components/app/app-shell";
import { Spinner, EmptyState, SectionLabel } from "@/components/app/ui";
import { DrugIcon } from "@/components/app/drug-icons";

type State =
  | { kind: "loading" }
  | { kind: "ready"; products: Product[] };

function fmt(price: string | null) {
  if (!price) return "—";
  return `₦${Number(price).toLocaleString("en-NG")}`;
}

export default function ShopPage() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("All");
  const [cart, setCart] = useState<CartItem[]>([]);
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());
  const [categories, setCategories] = useState<string[]>(["All"]);

  useEffect(() => {
    setCart(getCart());
    listCategories().then((cats) => setCategories(["All", ...cats])).catch(() => setCategories(["All"]));
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
      <div className="pb-8">
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-6 pb-4">
          <h1 className="font-syne text-[22px] font-bold text-white">Shop</h1>
          {cartCount > 0 && (
            <Link
              href="/cart"
              className="relative flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 transition hover:border-emerald-500/40"
            >
              <ShoppingCart className="h-5 w-5 text-white/70" />
              <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-[10px] font-bold text-black">
                {cartCount}
              </span>
            </Link>
          )}
        </div>

        {/* Search */}
        <div className="mx-5 mb-4 flex items-center gap-3 rounded-xl border border-white/10 bg-white/4 px-4 py-3">
          <Search className="h-4 w-4 shrink-0 text-white/30" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search medicines..."
            className="flex-1 bg-transparent text-sm text-white placeholder-white/30 outline-none"
          />
        </div>

        {/* Categories */}
        <div className="mb-5 flex gap-2 overflow-x-auto px-5 pb-1">
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={`shrink-0 rounded-full border px-3.5 py-1.5 text-[12px] font-medium transition ${
                category === c
                  ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-400"
                  : "border-white/10 bg-white/4 text-white/50 hover:border-white/20"
              }`}
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
          <div className="px-5">
            <SectionLabel>{state.products.length} product{state.products.length !== 1 ? "s" : ""}</SectionLabel>
            <div className="mt-3 grid grid-cols-2 gap-3">
              {state.products.map((p) => (
                <div
                  key={p.id}
                  className="flex flex-col rounded-2xl border border-white/8 bg-white/4 overflow-hidden"
                >
                  <Link href={`/shop/${p.id}`}>
                    <div className="flex h-[72px] items-center justify-center border-b border-white/6 bg-emerald-500/6">
                      <DrugIcon form={p.dosage_form ?? undefined} size={36} />
                    </div>
                  </Link>
                  <div className="flex flex-1 flex-col gap-1.5 p-3">
                    <Link href={`/shop/${p.id}`}>
                      <p className="line-clamp-2 text-[13px] font-semibold leading-snug text-white">
                        {p.name}
                      </p>
                      {p.strength && (
                        <p className="text-[11px] text-white/40">{p.strength}</p>
                      )}
                    </Link>
                    <p className="text-[13px] font-bold text-emerald-400">
                      {fmt(p.selling_price)}
                    </p>
                    {!p.is_in_stock ? (
                      <span className="text-[11px] text-white/30">Out of stock</span>
                    ) : (
                      <button
                        onClick={() => handleAdd(p)}
                        className={`mt-auto w-full rounded-xl py-2 text-[12px] font-semibold transition ${
                          addedIds.has(p.id)
                            ? "bg-emerald-500/20 text-emerald-400"
                            : "bg-emerald-500 text-black hover:bg-emerald-400"
                        }`}
                      >
                        {addedIds.has(p.id) ? "Added ✓" : "+ Add"}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
