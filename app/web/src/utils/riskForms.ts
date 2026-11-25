import type { CloseTradePayload, OpenTradePayload } from "../types/common";

type FormResult<T> = { payload: T; error: null } | { payload: null; error: string };

export function buildOpenPayload({ coin, type, entry, stop, target }: { coin: string; type: string; entry: string; stop: string; target: string }): FormResult<OpenTradePayload> {
  const entryNum = Number(entry);
  const stopNum = Number(stop);
  const targetNum = target ? Number(target) : null;
  if (!coin.trim() || !Number.isFinite(entryNum) || !Number.isFinite(stopNum)) {
    return { payload: null, error: "Enter coin, entry, and stop." };
  }
  return {
    payload: {
      coin: coin.trim(),
      type,
      entry: entryNum,
      stop: stopNum,
      target: targetNum !== null && Number.isFinite(targetNum) ? targetNum : null,
    },
    error: null,
  };
}

export function buildClosePayload({ coin, r, fill }: { coin: string; r: string; fill: string }): FormResult<CloseTradePayload> {
  const rNum = Number(r);
  if (!coin.trim() || !Number.isFinite(rNum)) {
    return { payload: null, error: "Enter coin and realized R." };
  }
  const fillNum = fill ? Number(fill) : undefined;
  return {
    payload: { coin: coin.trim(), r: rNum, fill_price: Number.isFinite(fillNum) ? fillNum : undefined },
    error: null,
  };
}
