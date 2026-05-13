import { apiClient } from "@/lib/api-client";
import type {
  CashAccount,
  CashAccountTransaction,
  CashTxKind,
} from "@/types/cash-account";
import type {
  CashAccountCreateInput,
  CashAccountUpdateInput,
} from "@/lib/schemas/cash-account";

// ── Raw shape (snake_case from backend) ──────────────────────────────────────

interface RawCashAccount {
  id: number;
  label: string;
  currency: string;
  balance: string;
  created_at: string;
  updated_at: string;
}

// ── Converter ─────────────────────────────────────────────────────────────────

function toCashAccount(raw: RawCashAccount): CashAccount {
  return {
    id: raw.id,
    label: raw.label,
    currency: raw.currency,
    balance: raw.balance,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

// ── Public API helpers ─────────────────────────────────────────────────────────

export async function getCashAccounts(): Promise<CashAccount[]> {
  const response = await apiClient.get<RawCashAccount[]>("/api/cash-accounts");
  return response.data.map(toCashAccount);
}

export async function createCashAccount(
  input: CashAccountCreateInput,
): Promise<CashAccount> {
  const response = await apiClient.post<RawCashAccount>(
    "/api/cash-accounts",
    input,
  );
  return toCashAccount(response.data);
}

export async function updateCashAccount(
  id: number,
  input: CashAccountUpdateInput,
): Promise<CashAccount> {
  const response = await apiClient.patch<RawCashAccount>(
    `/api/cash-accounts/${id}`,
    input,
  );
  return toCashAccount(response.data);
}

export async function deleteCashAccount(id: number): Promise<void> {
  await apiClient.delete(`/api/cash-accounts/${id}`);
}

interface RawCashTransaction {
  id: number;
  cash_account_id: number | null;
  kind: CashTxKind;
  amount: string;
  currency: string;
  traded_at: string;
  external_source: string | null;
}

function toCashTransaction(raw: RawCashTransaction): CashAccountTransaction {
  return {
    id: raw.id,
    cashAccountId: raw.cash_account_id,
    kind: raw.kind,
    amount: raw.amount,
    currency: raw.currency,
    tradedAt: raw.traded_at,
    externalSource: raw.external_source,
  };
}

export async function listCashTransactions(params: {
  kind?: CashTxKind;
} = {}): Promise<CashAccountTransaction[]> {
  const response = await apiClient.get<RawCashTransaction[]>(
    "/api/cash-accounts/transactions",
    { params: { kind: params.kind } },
  );
  return response.data.map(toCashTransaction);
}
