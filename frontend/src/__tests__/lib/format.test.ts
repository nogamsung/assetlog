import {
  formatCurrency,
  formatCompactCurrency,
  formatPercent,
  formatQuantity,
  formatRelativeTime,
  formatSignedCurrency,
  pnlColor,
} from "@/lib/format";

describe("formatCurrency — KRW", () => {
  it("KRW 통화를 한국어 형식으로 포맷한다", () => {
    const result = formatCurrency("12500000", "KRW");
    expect(result).toContain("12,500,000");
  });

  it("KRW 1500000.00 → ₩1,500,000 (no decimal)", () => {
    const result = formatCurrency("1500000.00", "KRW");
    expect(result).toBe("₩1,500,000");
  });

  it("0을 포맷한다", () => {
    const result = formatCurrency("0", "KRW");
    expect(result).toBeDefined();
  });

  it("음수를 포맷한다", () => {
    const result = formatCurrency("-1500000", "KRW");
    expect(result).toContain("1,500,000");
  });
});

describe("formatCurrency — USD trimTrailingZeros", () => {
  it("USD 통화를 포맷한다", () => {
    const result = formatCurrency("8200.12", "USD");
    expect(result).toContain("8,200");
  });

  it("USD 1234.50 → $1,234.5 (trailing zero trimmed)", () => {
    const result = formatCurrency("1234.50", "USD");
    // trim = true by default; .50 → .5
    expect(result).toMatch(/1,234\.5/);
    expect(result).not.toMatch(/1,234\.50/);
  });

  it("USD 1234.00 → $1,234 (both zeros trimmed)", () => {
    const result = formatCurrency("1234.00", "USD");
    expect(result).toMatch(/1,234/);
    expect(result).not.toMatch(/1,234\.0/);
  });

  it("USD trimTrailingZeros:false → 2 decimal places", () => {
    const result = formatCurrency("1234.00", "USD", { trimTrailingZeros: false });
    expect(result).toMatch(/1,234\.00/);
  });
});

describe("formatCurrency — USDT (Intl unsupported)", () => {
  it("USDT 1234.5000 → 1,234.5 USDT (trim trailing zeros)", () => {
    const result = formatCurrency("1234.5000", "USDT");
    expect(result).toMatch(/1,234\.5 USDT/);
  });

  it("USDT 1234.0000 → 1,234 USDT", () => {
    const result = formatCurrency("1234.0000", "USDT");
    expect(result).toMatch(/1,234 USDT/);
  });
});

describe("formatCompactCurrency", () => {
  it("120_000_000 KRW → contains 억 (ko-KR compact)", () => {
    const result = formatCompactCurrency(120000000, "KRW");
    expect(result).toContain("억");
    expect(result).toContain("1.2");
  });

  it("USD 대형 숫자 compact", () => {
    const result = formatCompactCurrency("1200000", "USD");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });
});

describe("formatPercent — trailing zero trim", () => {
  it("13.64 → 13.64%", () => {
    expect(formatPercent(13.64)).toBe("13.64%");
  });

  it("13.6400 → 13.64% (trailing zeros trimmed)", () => {
    expect(formatPercent(13.6400)).toBe("13.64%");
  });

  it("13.0 → 13% (trailing zero removed)", () => {
    expect(formatPercent(13.0)).toBe("13%");
  });

  it("0 → 0% (no sign)", () => {
    expect(formatPercent(0)).toBe("0%");
  });

  it("음수 퍼센트를 포맷한다", () => {
    expect(formatPercent(-5.5)).toBe("-5.5%");
  });

  it("digits 파라미터로 소수 자리를 조정한다", () => {
    expect(formatPercent(13.6789, 1)).toBe("13.7%");
    expect(formatPercent(13.6789, 0)).toBe("14%");
  });

  it("withSign 옵션 — 양수에 + 부호 붙음", () => {
    expect(formatPercent(3.5, 2, { withSign: true })).toBe("+3.5%");
  });

  it("withSign 옵션 — 0 은 부호 없음", () => {
    expect(formatPercent(0, 2, { withSign: true })).toBe("0%");
  });
});

describe("pnlColor", () => {
  it("양수 → text-toss-up", () => {
    expect(pnlColor("100")).toBe("text-toss-up");
    expect(pnlColor(50)).toBe("text-toss-up");
  });

  it("음수 → text-toss-down", () => {
    expect(pnlColor("-1")).toBe("text-toss-down");
    expect(pnlColor(-0.01)).toBe("text-toss-down");
  });

  it("0 → text-toss-textWeak (muted)", () => {
    expect(pnlColor("0")).toBe("text-toss-textWeak");
    expect(pnlColor(0)).toBe("text-toss-textWeak");
  });
});

describe("formatSignedCurrency", () => {
  it("양수 → +$1,234", () => {
    const result = formatSignedCurrency("1234", "USD");
    expect(result).toMatch(/^\+/);
    expect(result).toContain("1,234");
  });

  it("음수 → −$1,234 (U+2212 minus)", () => {
    const result = formatSignedCurrency("-1234", "USD");
    expect(result.startsWith("−")).toBe(true);
    expect(result).toContain("1,234");
  });

  it("0 → $0 (no sign)", () => {
    const result = formatSignedCurrency("0", "USD");
    expect(result).not.toMatch(/^[+\-−]/);
  });

  it("KRW 양수 → +₩1,500,000", () => {
    const result = formatSignedCurrency("1500000", "KRW");
    expect(result).toBe("+₩1,500,000");
  });
});

describe("formatRelativeTime", () => {
  it("null 을 '—' 로 변환한다", () => {
    expect(formatRelativeTime(null)).toBe("—");
  });

  it("방금 전(60초 미만)을 반환한다", () => {
    const now = new Date();
    const result = formatRelativeTime(now.toISOString());
    expect(result).toBe("방금 전 업데이트");
  });

  it("분 단위 상대 시간을 반환한다", () => {
    const past = new Date(Date.now() - 12 * 60 * 1000);
    const result = formatRelativeTime(past.toISOString());
    expect(result).toBe("12분 전 업데이트");
  });

  it("시간 단위 상대 시간을 반환한다", () => {
    const past = new Date(Date.now() - 3 * 60 * 60 * 1000);
    const result = formatRelativeTime(past.toISOString());
    expect(result).toBe("3시간 전 업데이트");
  });

  it("일 단위 상대 시간을 반환한다", () => {
    const past = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000);
    const result = formatRelativeTime(past.toISOString());
    expect(result).toBe("2일 전 업데이트");
  });
});

describe("formatQuantity", () => {
  it("crypto 는 8자리 소수까지 표시한다", () => {
    const result = formatQuantity("10.0000000000", "crypto");
    expect(result).toBeDefined();
    expect(typeof result).toBe("string");
  });

  it("crypto 0.12345678 → trailing zeros 없이 표시", () => {
    const result = formatQuantity("0.12345678", "crypto");
    expect(result).toContain("0.12345678");
  });

  it("kr_stock 10.0000 → 10 (trailing zeros removed)", () => {
    const result = formatQuantity("10.0000", "kr_stock");
    expect(result).toBe("10");
  });

  it("us_stock 5.0000 → 5", () => {
    const result = formatQuantity("5.0000", "us_stock");
    expect(result).toBe("5");
  });

  it("정수 수량을 정상 포맷한다", () => {
    const result = formatQuantity("100", "kr_stock");
    expect(result).toContain("100");
  });
});
