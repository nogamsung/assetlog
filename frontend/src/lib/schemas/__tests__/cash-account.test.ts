import {
  cashAccountCreateSchema,
  cashAccountUpdateSchema,
} from "@/lib/schemas/cash-account";

describe("cashAccountCreateSchema", () => {
  describe("label", () => {
    it("유효한 라벨을 통과시킨다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "토스뱅크 원화",
        currency: "KRW",
        balance: "1500000",
      });
      expect(result.success).toBe(true);
    });

    it("빈 라벨은 실패한다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "",
        currency: "KRW",
        balance: "1500000",
      });
      expect(result.success).toBe(false);
    });

    it("100자를 초과하는 라벨은 실패한다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "a".repeat(101),
        currency: "KRW",
        balance: "1500000",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("currency", () => {
    it("3자리 대문자 통화 코드는 통과한다 (KRW)", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "원화 계좌",
        currency: "KRW",
        balance: "0",
      });
      expect(result.success).toBe(true);
    });

    it("4자리 대문자 통화 코드는 통과한다 (USDT)", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "테더 계좌",
        currency: "USDT",
        balance: "100",
      });
      expect(result.success).toBe(true);
    });

    it("4자리 대문자 통화 코드는 통과한다 (USDC)", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "USDC 계좌",
        currency: "USDC",
        balance: "100",
      });
      expect(result.success).toBe(true);
    });

    it("소문자 통화 코드는 자동으로 대문자로 변환된다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "달러 계좌",
        currency: "usd",
        balance: "100",
      });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.currency).toBe("USD");
      }
    });

    it("2자리 통화 코드는 실패한다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "계좌",
        currency: "US",
        balance: "100",
      });
      expect(result.success).toBe(false);
    });

    it("5자리 통화 코드는 실패한다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "계좌",
        currency: "USDTX",
        balance: "100",
      });
      expect(result.success).toBe(false);
    });

    it("숫자 포함 통화 코드는 실패한다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "계좌",
        currency: "US1",
        balance: "100",
      });
      expect(result.success).toBe(false);
    });

    it("빈 통화 코드는 실패한다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "계좌",
        currency: "",
        balance: "100",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("balance", () => {
    it("정수 잔액은 통과한다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "계좌",
        currency: "KRW",
        balance: "1500000",
      });
      expect(result.success).toBe(true);
    });

    it("소수점 4자리 잔액은 통과한다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "계좌",
        currency: "USDT",
        balance: "100.1234",
      });
      expect(result.success).toBe(true);
    });

    it("0은 통과한다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "계좌",
        currency: "KRW",
        balance: "0",
      });
      expect(result.success).toBe(true);
    });

    it("음수 잔액은 실패한다 (앞에 -)", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "계좌",
        currency: "KRW",
        balance: "-100",
      });
      expect(result.success).toBe(false);
    });

    it("소수점 5자리 이상은 실패한다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "계좌",
        currency: "USDT",
        balance: "100.12345",
      });
      expect(result.success).toBe(false);
    });

    it("빈 잔액은 실패한다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "계좌",
        currency: "KRW",
        balance: "",
      });
      expect(result.success).toBe(false);
    });

    it("문자 포함 잔액은 실패한다", () => {
      const result = cashAccountCreateSchema.safeParse({
        label: "계좌",
        currency: "KRW",
        balance: "abc",
      });
      expect(result.success).toBe(false);
    });
  });
});

describe("cashAccountUpdateSchema", () => {
  it("label 만 있어도 통과한다", () => {
    const result = cashAccountUpdateSchema.safeParse({ label: "새 라벨" });
    expect(result.success).toBe(true);
  });

  it("balance 만 있어도 통과한다", () => {
    const result = cashAccountUpdateSchema.safeParse({ balance: "2000000" });
    expect(result.success).toBe(true);
  });

  it("둘 다 있어도 통과한다", () => {
    const result = cashAccountUpdateSchema.safeParse({
      label: "새 라벨",
      balance: "2000000",
    });
    expect(result.success).toBe(true);
  });

  it("둘 다 없으면 실패한다 (수정할 필드 없음)", () => {
    const result = cashAccountUpdateSchema.safeParse({});
    expect(result.success).toBe(false);
  });

  it("빈 label 은 실패한다", () => {
    const result = cashAccountUpdateSchema.safeParse({ label: "" });
    expect(result.success).toBe(false);
  });

  it("음수 balance 는 실패한다", () => {
    const result = cashAccountUpdateSchema.safeParse({ balance: "-100" });
    expect(result.success).toBe(false);
  });
});
