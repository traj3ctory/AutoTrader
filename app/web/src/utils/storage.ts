export function readStoredString({ key, fallback }: { key: string; fallback: string }): string {
  try {
    return window.localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

export function readStoredNumber({ key, fallback }: { key: string; fallback: number }): number {
  try {
    const raw = Number(window.localStorage.getItem(key));
    return Number.isFinite(raw) && raw > 0 ? raw : fallback;
  } catch {
    return fallback;
  }
}

export function writeStoredNumber({ key, value }: { key: string; value: number }): void {
  try {
    if (Number.isFinite(value) && value >= 0) {
      window.localStorage.setItem(key, String(value));
    }
  } catch {
    // ignore storage errors
  }
}

export function writeStoredString({ key, value }: { key: string; value: string }): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // ignore storage errors
  }
}
