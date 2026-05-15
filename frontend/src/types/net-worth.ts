export interface NetWorthCurrencyEntry {
  cash: string;
  assets: string;
  total: string;
}

export type NetWorthByAccount = Record<string, Record<string, string>>;

export interface NetWorthResponse {
  byCurrency: Record<string, NetWorthCurrencyEntry>;
  byAccount: NetWorthByAccount;
  displayCurrency: string | null;
  convertedTotal: string | null;
}
