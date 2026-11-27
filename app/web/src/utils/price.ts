import { PRICE_MIN_DECIMALS, PRICE_SIG_FIGS } from "../constants/analyzer";

/**
 * @function priceDecimals
 * @description Decimal places that keep cheap coin prices readable, matching the server rule.
 */
function priceDecimals(value: number): number {
  if (!value) return PRICE_MIN_DECIMALS;
  return Math.max(PRICE_MIN_DECIMALS, PRICE_SIG_FIGS - 1 - Math.floor(Math.log10(Math.abs(value))));
}

export function chartPriceFormat({ price }: { price: number }) {
  const precision = priceDecimals(price);
  return { type: "price" as const, precision, minMove: Number((10 ** -precision).toFixed(precision)) };
}
