"use client";

import { useEffect } from "react";

export function PwaRegister(): null {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) {
      return;
    }

    // In dev, a service worker only causes harm: it caches Next's dev chunks and
    // shadows code edits with stale JS. Tear down any existing registration +
    // caches so the browser always runs the latest bundle, and never register.
    if (process.env.NODE_ENV !== "production") {
      void navigator.serviceWorker
        .getRegistrations()
        .then((regs) => Promise.all(regs.map((r) => r.unregister())));
      if (typeof caches !== "undefined") {
        void caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))));
      }
      return;
    }

    const register = async (): Promise<void> => {
      try {
        await navigator.serviceWorker.register("/sw.js");
      } catch {
        // Leave installability to the browser if registration fails.
      }
    };

    void register();
  }, []);

  return null;
}
