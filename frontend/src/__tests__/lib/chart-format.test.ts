import {
  formatCompactNumber,
  formatCurrencyValue,
  formatTimestamp,
  formatTooltipLabel,
} from "@/lib/chart-format";

describe("formatTimestamp", () => {
  const d = new Date("2026-04-24T15:30:00+09:00");

  it("1D 기간은 HH:mm 포맷으로 반환한다", () => {
    expect(formatTimestamp(d, "1D")).toMatch(/^\d{2}:\d{2}$/);
  });

  it("1W 와 1M 기간은 M/d 포맷으로 반환한다", () => {
    expect(formatTimestamp(d, "1W")).toMatch(/^\d{1,2}\/\d{1,2}$/);
    expect(formatTimestamp(d, "1M")).toMatch(/^\d{1,2}\/\d{1,2}$/);
  });

  it("1Y 기간은 yy/MM 포맷으로 반환한다", () => {
    expect(formatTimestamp(d, "1Y")).toBe("26/04");
  });

  it("ALL 기간은 yyyy/MM 포맷으로 반환한다", () => {
    expect(formatTimestamp(d, "ALL")).toBe("2026/04");
  });
});

describe("formatCompactNumber", () => {
  it("큰 숫자는 문자열을 반환한다", () => {
    expect(typeof formatCompactNumber(12_300_000)).toBe("string");
    expect(formatCompactNumber(12_300_000).length).toBeGreaterThan(0);
  });

  it("숫자 0 도 처리한다", () => {
    expect(formatCompactNumber(0)).toBe("0");
  });
});

describe("formatCurrencyValue", () => {
  it("숫자 입력을 통화 문자열로 포맷한다", () => {
    const result = formatCurrencyValue(12500, "KRW");
    expect(result).toMatch(/12,500/);
  });

  it("문자열 입력도 숫자로 변환해 포맷한다", () => {
    const result = formatCurrencyValue("9800", "KRW");
    expect(result).toMatch(/9,800/);
  });

  it("USD 통화도 처리한다", () => {
    const result = formatCurrencyValue(1234, "USD");
    expect(result).toMatch(/1,234/);
  });
});

describe("formatTooltipLabel", () => {
  it("Date 객체를 한국어 날짜 문자열로 포맷한다", () => {
    const d = new Date("2026-04-24T15:30:00+09:00");
    expect(formatTooltipLabel(d)).toBe("2026년 4월 24일 15:30");
  });

  it("ISO 문자열도 Date 로 파싱해 포맷한다", () => {
    const result = formatTooltipLabel("2026-04-24T00:00:00+09:00");
    expect(result).toMatch(/^2026년 4월 24일/);
  });
});
