const WARM_TTL_MS = 10 * 60 * 1000;
const MAX_WAIT_MS = 90_000;
const RETRY_MS = 3_000;
const FETCH_TIMEOUT_MS = 20_000;
const FAST_OK_MS = 700;

export const WARM_SESSION_KEY = "namma-vahana-backend-warm";

export const WARM_STEPS = [
  { id: "connect", label: "Connect", detail: "Waking Render service" },
  { id: "data", label: "Load data", detail: "Violation intelligence" },
  { id: "ready", label: "Ready", detail: "Opening dashboard" },
] as const;

const STATUS_MESSAGES = [
  { after: 0, text: "Connecting…" },
  { after: 8_000, text: "Starting server…" },
  { after: 20_000, text: "Loading data…" },
  { after: 45_000, text: "Almost there…" },
] as const;

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function statusForElapsed(elapsed: number): string {
  let msg: string = STATUS_MESSAGES[0].text;
  for (const entry of STATUS_MESSAGES) {
    if (elapsed >= entry.after) msg = entry.text;
  }
  return msg;
}

export function progressForElapsed(elapsed: number, ready: boolean) {
  if (ready) return 100;
  const eased = 1 - Math.exp(-elapsed / 22_000);
  return Math.min(92, Math.round(eased * 92));
}

export function stepIndexForProgress(progress: number) {
  if (progress >= 88) return 2;
  if (progress >= 38) return 1;
  return 0;
}

async function pingHealth(): Promise<boolean> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const res = await fetch("/api/health", {
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    if (!res.ok) return false;
    const data = (await res.json()) as { ok?: boolean };
    return data.ok === true;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

export function isBackendRecentlyWarm(): boolean {
  if (typeof window === "undefined") return false;
  const cached = sessionStorage.getItem(WARM_SESSION_KEY);
  if (!cached) return false;
  return Date.now() - Number(cached) < WARM_TTL_MS;
}

export function markBackendWarm() {
  sessionStorage.setItem(WARM_SESSION_KEY, String(Date.now()));
}

/** Fast path — skip splash when local backend responds immediately. */
export async function quickPing(): Promise<{ ok: boolean; ms: number }> {
  const start = performance.now();
  const ok = await pingHealth();
  return { ok, ms: performance.now() - start };
}

export function shouldShowWarmupSplash(recentlyWarm: boolean, quick: { ok: boolean; ms: number }) {
  if (isWarmupPreview()) return true;
  if (recentlyWarm && quick.ok) return false;
  if (quick.ok && quick.ms <= FAST_OK_MS) return false;
  return true;
}

export function isWarmupPreview(): boolean {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  return params.get("warmup") === "1" || params.get("warmup") === "preview";
}

/** Demo animation for ?warmup=preview — no network calls. */
export async function simulateWarmupDemo(
  onUpdate: (update: WarmupUpdate) => void,
  durationMs = 14_000,
): Promise<void> {
  const start = Date.now();
  return new Promise((resolve) => {
    const tick = () => {
      const elapsed = Date.now() - start;
      const done = elapsed >= durationMs;
      const progress = progressForElapsed(elapsed, done);
      onUpdate({
        message: done ? "All systems online" : statusForElapsed(elapsed),
        progress,
        step: stepIndexForProgress(progress),
      });
      if (done) {
        resolve();
        return;
      }
      window.setTimeout(tick, 120);
    };
    tick();
  });
}

export type WarmupUpdate = {
  message: string;
  progress: number;
  step: number;
};

/** Retry /api/health until Render cold start completes or timeout. */
export async function warmBackend(
  onUpdate?: (update: WarmupUpdate) => void,
): Promise<boolean> {
  const start = Date.now();

  const emit = (ready = false) => {
    const elapsed = Date.now() - start;
    const progress = progressForElapsed(elapsed, ready);
    onUpdate?.({
      message: ready ? "Ready" : statusForElapsed(elapsed),
      progress,
      step: stepIndexForProgress(progress),
    });
  };

  emit(false);

  while (Date.now() - start < MAX_WAIT_MS) {
    emit(false);
    if (await pingHealth()) {
      emit(true);
      return true;
    }
    await sleep(RETRY_MS);
  }

  return false;
}
