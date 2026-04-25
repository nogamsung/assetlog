import { z } from "zod";

export const transactionTypeEnum = z.enum(["buy", "sell"]);

const decimalStringSchema = z
  .string()
  .regex(/^\d+(\.\d+)?$/, "유효한 숫자를 입력하세요")
  .refine((val) => Number(val) > 0, { message: "0보다 큰 값을 입력하세요" });

export const transactionCreateSchema = z.object({
  type: transactionTypeEnum,
  quantity: decimalStringSchema,
  price: decimalStringSchema,
  tradedAt: z
    .date()
    .refine((d) => d <= new Date(), { message: "미래 날짜는 입력할 수 없습니다" }),
  memo: z
    .string()
    .max(255, "메모는 255자 이하로 입력하세요")
    .optional()
    .nullable(),
  tag: z
    .string()
    .max(50, "태그는 50자 이하로 입력하세요")
    .optional()
    .nullable(),
});

export type TransactionCreateInput = z.infer<typeof transactionCreateSchema>;
