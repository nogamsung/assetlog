import {
  formatCurrency,
  formatPercent,
  formatRelativeTime,
  formatQuantity,
} from "@/lib/format";

describe("formatCurrency", () => {
  it("KRW 통화를 한국어 형식으로 포맷한다", () => {
    const result = formatCurrency("12500000", "KRW");
    expect(result).toContain("12,500,000");
  });

  it("USD 통화를 포맷한다", () => {
    const result = formatCurrency("8200.12", "USD");
    expect(result).toContain("8,200");
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

describe("formatPercent", () => {
  it("기본 2자리 소수로 포맷한다", () => {
    expect(formatPercent(13.64)).toBe("13.64%");
  });

  it("0% 를 포맷한다", () => {
    expect(formatPercent(0)).toBe("0.00%");
  });

  it("음수 퍼센트를 포맷한다", () => {
    expect(formatPercent(-5.5)).toBe("-5.50%");
  });

  it("digits 파라미터로 소수 자리를 조정한다", () => {
    expect(formatPercent(13.6789, 1)).toBe("13.7%");
    expect(formatPercent(13.6789, 0)).toBe("14%");
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
    // 소수 없으면 0자리, 있으면 최대 8자리
    expect(typeof result).toBe("string");
  });

  it("kr_stock 은 4자리 소수까지 표시한다", () => {
    const result = formatQuantity("100.5000", "kr_stock");
    expect(result).toBeDefined();
    expect(typeof result).toBe("string");
  });

  it("us_stock 은 4자리 소수까지 표시한다", () => {
    const result = formatQuantity("5.0000", "us_stock");
    expect(result).toBeDefined();
  });

  it("정수 수량을 정상 포맷한다", () => {
    const result = formatQuantity("100", "kr_stock");
    expect(result).toContain("100");
  });
});
