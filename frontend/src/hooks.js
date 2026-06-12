import { useEffect, useState } from "react";
import { api } from "./utils";

const cache = new Map();

export function clearDataCache() {
  cache.clear();
}

export function useData(path, deps = []) {
  const [state, setState] = useState(() => {
    const hit = cache.get(path);
    return hit ? { loading: false, data: hit, error: "" } : { loading: true, data: null, error: "" };
  });

  useEffect(() => {
    let active = true;
    const hit = cache.get(path);
    if (hit) {
      setState({ loading: false, data: hit, error: "" });
      return;
    }
    setState((s) => ({ ...s, loading: true, error: "" }));
    api(path)
      .then((data) => {
        if (!active) return;
        cache.set(path, data);
        setState({ loading: false, data, error: "" });
      })
      .catch((err) => {
        if (!active) return;
        setState({ loading: false, data: null, error: err.message });
      });
    return () => {
      active = false;
    };
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  return state;
}
