import { z } from "zod";

// PRD §8.1 — currency: 3~4 letter uppercase (USDT/USDC 호환)
const currencyCode = z
  .string()
  .trim()
  .transform((s) => s.toUpperCase())
  .pipe(
    z
      .string()
      .regex(
        /^[A-Z]{3,4}$/,
        "통화 코드는 3~4자 영문 대문자 (예: KRW, USDT)",
      ),
  );

// balance: Decimal as string, ≥ 0, 소수점 4자리
const balanceString = z
  .string()
  .trim()
  .regex(/^\d+(\.\d{1,4})?$/, "0 이상의 숫자 (소수점 최대 4자리)");

export const cashAccountCreateSchema = z.object({
  label: z.string().trim().min(1, "라벨을 입력하세요").max(100),
  currency: currencyCode,
  balance: balanceString,
});

export const cashAccountUpdateSchema = z
  .object({
    label: z.string().trim().min(1).max(100).optional(),
    balance: balanceString.optional(),
  })
  .refine((d) => d.label !== undefined || d.balance !== undefined, {
    message: "수정할 필드를 하나 이상 입력하세요",
  });

export type CashAccountCreateInput = z.infer<typeof cashAccountCreateSchema>;
export type CashAccountUpdateInput = z.infer<typeof cashAccountUpdateSchema>;
