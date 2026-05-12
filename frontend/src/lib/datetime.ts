/**
 * All timestamps in this app display in KST (Asia/Seoul) with 24-hour notation.
 */

const KST = "Asia/Seoul";

function toDate(input: string | Date): Date | null {
  if (!input) return null;
  const d = input instanceof Date ? input : new Date(input);
  return isNaN(d.getTime()) ? null : d;
}

export function formatDateTimeKST(input: string | Date): string {
  const d = toDate(input);
  if (!d) return "—";
  const fmt = new Intl.DateTimeFormat("ko-KR", {
    timeZone: KST,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = fmt.formatToParts(d);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}`;
}

export function formatDateKST(input: string | Date): string {
  const d = toDate(input);
  if (!d) return "—";
  const fmt = new Intl.DateTimeFormat("ko-KR", {
    timeZone: KST,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  const parts = fmt.formatToParts(d);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

export function formatTimeKST(input: string | Date): string {
  const d = toDate(input);
  if (!d) return "—";
  const fmt = new Intl.DateTimeFormat("ko-KR", {
    timeZone: KST,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = fmt.formatToParts(d);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("hour")}:${get("minute")}`;
}

export function formatChartTickKST(date: Date, pattern: string): string {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: KST,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = fmt.formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";

  const year = get("year");
  const month = get("month");
  const day = get("day");
  const hour = get("hour");
  const minute = get("minute");
  const yy = year.slice(-2);
  const M = String(Number(month));
  const d = String(Number(day));

  return pattern
    .replace("yyyy", year)
    .replace("yy", yy)
    .replace("MM", month)
    .replace("M", M)
    .replace("dd", day)
    .replace("d", d)
    .replace("HH", hour)
    .replace("mm", minute);
}
