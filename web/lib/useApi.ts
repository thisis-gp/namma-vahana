"use client";

import { useEffect, useState } from "react";
import { peekHeroCache } from "./hero-cache";

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

const RETRY_ATTEMPTS = 5;
const RETRY_DELAY_MS = 2_000;

async function fetchWithRetry<T>(fetcher: () => Promise<T>): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt < RETRY_ATTEMPTS; attempt++) {
    try {
      return await fetcher();
    } catch (error) {
      lastError = error;
      if (attempt < RETRY_ATTEMPTS - 1) {
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
      }
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Request failed");
}

// Fetch once on mount. Each section owns its request so one failed
// endpoint never blanks the whole page.
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: ReadonlyArray<unknown> = [],
  cacheKey?: string,
): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>(() => {
    const cached = cacheKey ? peekHeroCache<T>(cacheKey) : null;
    return {
      data: cached,
      loading: !cached,
      error: null,
    };
  });

  useEffect(() => {
    let alive = true;

    const cached = cacheKey ? peekHeroCache<T>(cacheKey) : null;
    if (cached) {
      setState({ data: cached, loading: false, error: null });
      fetchWithRetry(fetcher)
        .then((data) => alive && setState({ data, loading: false, error: null }))
        .catch(
          (e: unknown) =>
            alive &&
            setState((s) => ({
              ...s,
              loading: false,
              error: e instanceof Error ? e.message : "Request failed",
            })),
        );
      return () => {
        alive = false;
      };
    }

    setState({ data: null, loading: true, error: null });
    fetchWithRetry(fetcher)
      .then((data) => alive && setState({ data, loading: false, error: null }))
      .catch(
        (e: unknown) =>
          alive &&
          setState({
            data: null,
            loading: false,
            error: e instanceof Error ? e.message : "Request failed",
          }),
      );

    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
