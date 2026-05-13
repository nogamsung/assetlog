export interface CashAccount {
  id: number;
  label: string;
  currency: string; // ISO 4217 3-letter or stable coin (USDT/USDC) 4-letter
  balance: string; // Decimal as string (백엔드 직렬화 형식 그대로)
  createdAt: string; // ISO-8601
  updatedAt: string;
}

export type CashTxKind =
  | "deposit"
  | "withdraw"
  | "interest"
  | "interest_tax"
  | "transfer_in"
  | "transfer_out";

export interface CashAccountTransaction {
  id: number;
  cashAccountId: number | null;
  kind: CashTxKind;
  amount: string;
  currency: string;
  tradedAt: string;
  externalSource: string | null;
}
