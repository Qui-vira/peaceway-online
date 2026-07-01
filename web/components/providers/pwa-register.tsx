"use client";

import { useEffect } from "react";

export function PwaRegister(): null {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) {
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
