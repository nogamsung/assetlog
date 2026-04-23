import { z } from "zod";

export const assetTypeEnum = z.enum(["crypto", "kr_stock", "us_stock"]);

export const userAssetCreateSchema = z.object({
  assetSymbolId: z.number().int().positive("유효한 심볼을 선택하세요"),
  memo: z.string().max(255, "메모는 255자 이하로 입력하세요").optional().nullable(),
});

export const symbolCreateSchema = z.object({
  assetType: assetTypeEnum,
  symbol: z
    .string()
    .min(1, "심볼을 입력하세요")
    .max(50, "심볼은 50자 이하로 입력하세요"),
  exchange: z.string().min(1, "거래소를 입력하세요"),
  name: z.string().min(1, "이름을 입력하세요"),
  currency: z
    .string()
    .min(3, "통화 코드는 3자 이상이어야 합니다")
    .max(10, "통화 코드는 10자 이하로 입력하세요"),
});

export type UserAssetCreateInput = z.infer<typeof userAssetCreateSchema>;
export type SymbolCreateInput = z.infer<typeof symbolCreateSchema>;
