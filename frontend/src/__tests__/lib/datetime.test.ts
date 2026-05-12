import {
  formatDateTimeKST,
  formatDateKST,
  formatTimeKST,
  formatChartTickKST,
} from "@/lib/datetime";

describe("formatDateTimeKST", () => {
  it("UTC midnight -> KST 09:00", () => {
    expect(formatDateTimeKST("2026-05-12T00:00:00Z")).toBe("2026-05-12 09:00");
  });

  it("UTC 05:00 -> KST 14:00", () => {
    expect(formatDateTimeKST("2026-05-12T05:00:00Z")).toBe("2026-05-12 14:00");
  });

  it("24h: no AM/PM prefix", () => {
    const result = formatDateTimeKST("2026-05-12T05:00:00Z");
    expect(result).not.toMatch(/AM|PM/);
    expect(result).toBe("2026-05-12 14:00");
  });

  it("Date object input", () => {
    expect(formatDateTimeKST(new Date("2026-05-12T05:00:00Z"))).toBe("2026-05-12 14:00");
  });

  it("ISO string and Date object produce same result", () => {
    const iso = "2026-03-01T15:30:00Z";
    expect(formatDateTimeKST(iso)).toBe(formatDateTimeKST(new Date(iso)));
  });

  it("empty string -> fallback", () => {
    expect(formatDateTimeKST("")).toBe("—");
  });

  it("invalid date string -> fallback", () => {
    expect(formatDateTimeKST("not-a-date")).toBe("—");
  });
});

describe("formatDateKST", () => {
  it("UTC 15:00 on Jan 31 -> KST Feb 01", () => {
    expect(formatDateKST("2026-01-31T15:00:00Z")).toBe("2026-02-01");
  });

  it("returns date only (no time)", () => {
    expect(formatDateKST("2026-05-12T05:00:00Z")).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(formatDateKST("2026-05-12T05:00:00Z")).toBe("2026-05-12");
  });

  it("Date object input", () => {
    expect(formatDateKST(new Date("2026-05-12T00:00:00Z"))).toBe("2026-05-12");
  });

  it("empty string -> fallback", () => {
    expect(formatDateKST("")).toBe("—");
  });
});

describe("formatTimeKST", () => {
  it("UTC 05:00 -> KST 14:00", () => {
    expect(formatTimeKST("2026-05-12T05:00:00Z")).toBe("14:00");
  });

  it("24h format (no AM/PM)", () => {
    expect(formatTimeKST("2026-05-12T05:00:00Z")).not.toMatch(/AM|PM/);
  });

  it("Date object input", () => {
    expect(formatTimeKST(new Date("2026-05-12T05:00:00Z"))).toBe("14:00");
  });

  it("empty string -> fallback", () => {
    expect(formatTimeKST("")).toBe("—");
  });
});

describe("formatChartTickKST", () => {
  const d = new Date("2026-04-24T06:30:00Z"); // KST = 2026-04-24 15:30

  it("HH:mm pattern returns KST 24h time", () => {
    expect(formatChartTickKST(d, "HH:mm")).toBe("15:30");
  });

  it("M/d pattern returns month/day", () => {
    expect(formatChartTickKST(d, "M/d")).toBe("4/24");
  });

  it("yy/MM pattern returns 2-digit year / 2-digit month", () => {
    expect(formatChartTickKST(d, "yy/MM")).toBe("26/04");
  });

  it("yyyy/MM pattern returns 4-digit year / 2-digit month", () => {
    expect(formatChartTickKST(d, "yyyy/MM")).toBe("2026/04");
  });
});
