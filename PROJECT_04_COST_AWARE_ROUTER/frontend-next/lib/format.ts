export function toFiniteNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

export function formatCost(value: unknown): string {
  const numeric = toFiniteNumber(value, 0);
  if (numeric === 0) return "$0.000000";
  const abs = Math.abs(numeric);
  if (abs >= 1) return `$${numeric.toFixed(4)}`;
  if (abs >= 0.01) return `$${numeric.toFixed(6)}`;
  if (abs >= 0.0001) return `$${numeric.toFixed(8)}`;
  return `$${numeric.toFixed(10)}`;
}

export function formatSavings(value: unknown): string {
  return formatCost(value);
}

export function formatPercent(value: unknown): string {
  const numeric = toFiniteNumber(value, 0);
  if (!Number.isFinite(numeric)) return "0.00%";
  return `${numeric.toFixed(2)}%`;
}
