"use client";

import { AnimatePresence, motion } from "framer-motion";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LogoMark } from "@/components/brand/Logo";
import { BRAND } from "@/lib/brand";
import { hasHeroCache, prefetchHeroBundle } from "@/lib/hero-cache";
import {
  WARM_SESSION_KEY,
  clearBackendWarm,
  isBackendRecentlyWarm,
  isWarmupPreview,
  markBackendWarm,
  minSplashMs,
  quickPing,
  shouldShowWarmupSplash,
  simulateWarmupDemo,
  warmBackend,
} from "@/lib/warmup";

export default function BackendWarmup({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname() ?? "/";
  const onLanding = pathname === "/";
  const [visible, setVisible] = useState(false);
  const [exiting, setExiting] = useState(false);
  const [message, setMessage] = useState("Connecting…");
  const [progress, setProgress] = useState(0);
  const [showContinue, setShowContinue] = useState(false);

  // Never block officer/resident routes — judges navigate there immediately.
  useEffect(() => {
    if (!onLanding) {
      setVisible(false);
      setExiting(true);
    }
  }, [onLanding]);

  useEffect(() => {
    let cancelled = false;

    const hideOverlay = async (markWarm: boolean) => {
      if (cancelled) return;
      if (markWarm && hasHeroCache()) markBackendWarm();
      else clearBackendWarm();
      setProgress(100);
      setMessage("Ready");
      setExiting(true);
      await new Promise((r) => setTimeout(r, minSplashMs()));
      window.setTimeout(() => {
        if (!cancelled) setVisible(false);
      }, 350);
    };

    const run = async () => {
      // Background warm on sub-routes; no splash.
      if (!onLanding) {
        void prefetchHeroBundle(12_000);
        return;
      }

      if (isWarmupPreview()) {
        sessionStorage.removeItem(WARM_SESSION_KEY);
        setVisible(true);
        await simulateWarmupDemo((update) => {
          if (cancelled) return;
          setMessage(update.message);
          setProgress(update.progress);
        });
        if (!cancelled) {
          setExiting(true);
          setVisible(false);
        }
        return;
      }

      const recent = isBackendRecentlyWarm();
      if (recent && hasHeroCache()) {
        void prefetchHeroBundle(8_000);
        return;
      }

      const quick = await quickPing();
      if (cancelled) return;

      if (!shouldShowWarmupSplash(recent, quick)) {
        const ready = await prefetchHeroBundle(12_000);
        if (ready) markBackendWarm();
        else clearBackendWarm();
        return;
      }

      setVisible(true);
      const continueTimer = window.setTimeout(() => setShowContinue(true), 45_000);

      if (quick.ok) {
        setMessage("Loading data…");
        setProgress(72);
        const ready = await prefetchHeroBundle();
        window.clearTimeout(continueTimer);
        await hideOverlay(ready);
        return;
      }

      const ok = await warmBackend((update) => {
        if (cancelled) return;
        setMessage(update.message);
        setProgress(update.progress);
      });

      window.clearTimeout(continueTimer);
      await hideOverlay(ok && hasHeroCache());
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [onLanding]);

  return (
    <>
      {children}
      <AnimatePresence>
        {visible ? (
          <motion.div
            key="warmup"
            className="warmup-minimal pointer-events-none fixed inset-0 z-[100] flex flex-col items-center justify-center px-6"
            initial={{ opacity: 1 }}
            animate={{ opacity: exiting ? 0 : 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            role="status"
            aria-live="polite"
            aria-busy={!exiting}
          >
            <motion.div
              className="flex w-full max-w-xs flex-col items-center text-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.05 }}
            >
              <LogoMark size={40} className="opacity-95" />

              <p className="mt-8 font-display text-lg font-semibold tracking-tight text-ink">
                {BRAND.name}
              </p>

              <AnimatePresence mode="wait">
                <motion.p
                  key={message}
                  className="mt-2 text-sm text-ink-muted"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {message}
                </motion.p>
              </AnimatePresence>

              <div className="mt-10 h-px w-full overflow-hidden bg-line">
                <motion.div
                  className="h-full bg-cobalt"
                  initial={{ width: "0%" }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                />
              </div>

              {showContinue ? (
                <button
                  type="button"
                  className="pointer-events-auto mt-8 text-sm text-ink-faint underline-offset-4 transition hover:text-ink hover:underline"
                  onClick={() => {
                    setExiting(true);
                    setVisible(false);
                  }}
                >
                  Continue anyway
                </button>
              ) : (
                <p className="mt-8 text-xs text-ink-faint">
                  First load may take a minute
                </p>
              )}
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </>
  );
}
