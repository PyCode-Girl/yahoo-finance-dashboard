const EMPTY = "—";

function isMissing(value) {
  return value === null || value === undefined || Number.isNaN(Number(value));
}

// 4.79T, 451.44B, 12.30M (used for market cap)
export function formatCompact(value) {
  if (isMissing(value)) return EMPTY;
  const n = Number(value);
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${(n / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  return n.toLocaleString("en-US");
}

// 51,014,085 (used for volume and employees)
export function formatNumber(value) {
  if (isMissing(value)) return EMPTY;
  return Number(value).toLocaleString("en-US");
}

// 1,234.56
export function formatPrice(value) {
  if (isMissing(value)) return EMPTY;
  return Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// +1.23 or -1.23
export function formatChange(value) {
  if (isMissing(value)) return EMPTY;
  const n = Number(value);
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}`;
}

// +1.23% or -1.23%
export function formatPercent(value) {
  if (isMissing(value)) return EMPTY;
  const n = Number(value);
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
}

// "12 Oct 2026, 4:30 PM"
export function formatDateTime(value) {
  if (!value) return EMPTY;
  // The backend sends UTC times without a "Z", so add it before parsing.
  const text = String(value);
  const date = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(text) ? text : `${text}Z`);
  if (Number.isNaN(date.getTime())) return EMPTY;
  return date.toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// Which colour class to use: green for gains, red for losses
export function changeClass(value) {
  if (isMissing(value) || Number(value) === 0) return "neutral";
  return Number(value) > 0 ? "gain" : "loss";
}