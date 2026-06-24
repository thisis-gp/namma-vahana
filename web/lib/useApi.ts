"use client";

import { useEffect, useState } from "react";
import { peekHeroCache } from "./hero-cache";

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

// Fetch once on mount. Each section owns its request so one failed
// endpoint never blanks the whole page.
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: ReadonlyArray<unknown> = [],
  cacheKey?: string,
): ApiState<T> {
  const cached = cacheKey ? peekHeroCache<T>(cacheKey) : null;
  const [state, setState] = useState<ApiState<T>>({
    data: cached,
    loading: !cached,
    error: null,
  });

  useEffect(() => {
    let alive = true;
    if (cached) {
      // Refresh in background without blocking UI.
      fetcher()
        .then((data) => alive && setState({ data, loading: false, error: null }))
        .catch(() => alive && setState((s) => ({ ...s, loading: false })));
      return () => {
        alive = false;
      };
    }
    setState({ data: null, loading: true, error: null });
    fetcher()
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
