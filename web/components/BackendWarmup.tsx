"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { LogoMark } from "@/components/brand/Logo";
import { BRAND } from "@/lib/brand";
import { prefetchHeroBundle } from "@/lib/hero-cache";
import {
  WARM_SESSION_KEY,
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
  const [gateOpen, setGateOpen] = useState(false);
  const [visible, setVisible] = useState(false);
  const [exiting, setExiting] = useState(false);
  const [message, setMessage] = useState("Connecting…");
  const [progress, setProgress] = useState(0);
  const [showContinue, setShowContinue] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const openGate = async () => {
      await new Promise((r) => setTimeout(r, minSplashMs()));
      if (!cancelled) setGateOpen(true);
    };

    const finish = async (ok: boolean) => {
      if (cancelled) return;
      if (ok) markBackendWarm();
      setProgress(100);
      setMessage("Ready");
      setExiting(true);
      await openGate();
      window.setTimeout(() => {
        if (!cancelled) setVisible(false);
      }, 350);
    };

    const run = async () => {
      if (isWarmupPreview()) {
        sessionStorage.removeItem(WARM_SESSION_KEY);
        setVisible(true);
        await simulateWarmupDemo((update) => {
          if (cancelled) return;
          setMessage(update.message);
          setProgress(update.progress);
        });
        if (!cancelled) {
          await openGate();
          setVisible(false);
        }
        return;
      }

      const recent = isBackendRecentlyWarm();
      if (!recent) setVisible(true);

      const quick = await quickPing();
      if (cancelled) return;

      if (!shouldShowWarmupSplash(recent, quick)) {
        if (quick.ok) {
          const ready = await prefetchHeroBundle();
          if (ready) markBackendWarm();
        }
        if (!cancelled) setGateOpen(true);
        return;
      }

      setVisible(true);

      if (quick.ok) {
        setMessage("Loading data…");
        setProgress(72);
        const ready = await prefetchHeroBundle();
        await finish(ready);
        return;
      }

      const continueTimer = window.setTimeout(() => setShowContinue(true), 60_000);

      const ok = await warmBackend((update) => {
        if (cancelled) return;
        setMessage(update.message);
        setProgress(update.progress);
      });

      window.clearTimeout(continueTimer);
      if (ok) {
        await finish(true);
      } else {
        await openGate();
        setVisible(false);
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      {gateOpen ? children : null}
      <AnimatePresence>
        {visible ? (
          <motion.div
            key="warmup"
            className="warmup-minimal fixed inset-0 z-[100] flex flex-col items-center justify-center px-6"
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
                  className="mt-8 text-sm text-ink-faint underline-offset-4 transition hover:text-ink hover:underline"
                  onClick={() => {
                    setExiting(true);
                    setGateOpen(true);
                    window.setTimeout(() => setVisible(false), 350);
                  }}
                >
                  Continue
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
