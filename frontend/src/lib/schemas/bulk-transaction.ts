import { z } from "zod";

const decimalStringSchema = z
  .string()
  .min(1, "값을 입력하세요")
  .regex(/^\d+(\.\d+)?$/, "유효한 숫자를 입력하세요")
  .refine((val) => Number(val) > 0, { message: "0보다 큰 값을 입력하세요" });

export const bulkRowSchema = z.object({
  symbol: z
    .string()
    .min(1, "종목 코드를 입력하세요")
    .max(50, "종목 코드는 50자 이하로 입력하세요"),
  exchange: z
    .string()
    .min(1, "거래소를 입력하세요")
    .max(50, "거래소는 50자 이하로 입력하세요"),
  type: z
    .string()
    .transform((val) => {
      const lower = val.toLowerCase();
      if (lower === "buy" || lower === "매수") return "buy" as const;
      if (lower === "sell" || lower === "매도") return "sell" as const;
      return val as "buy" | "sell";
    })
    .pipe(z.enum(["buy", "sell"], { message: "buy 또는 sell을 입력하세요" })),
  quantity: decimalStringSchema,
  price: decimalStringSchema,
  traded_at: z
    .string()
    .min(1, "거래일을 입력하세요")
    .refine(
      (val) => !Number.isNaN(Date.parse(val)),
      { message: "유효한 날짜 형식을 입력하세요" },
    )
    .refine(
      (val) => new Date(val) <= new Date(),
      { message: "미래 날짜는 입력할 수 없습니다" },
    ),
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

export type BulkRowInput = z.infer<typeof bulkRowSchema>;

export const bulkRequestSchema = z.object({
  rows: z
    .array(bulkRowSchema)
    .min(1, "최소 1행 이상 입력하세요")
    .max(500, "최대 500행까지 입력할 수 있습니다"),
});

export type BulkRequestInput = z.infer<typeof bulkRequestSchema>;

/** CSV 필수 헤더 컬럼 */
export const REQUIRED_CSV_HEADERS = [
  "symbol",
  "exchange",
  "type",
  "quantity",
  "price",
  "traded_at",
] as const;
