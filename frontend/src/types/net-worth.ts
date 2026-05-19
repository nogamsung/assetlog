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
  /** True if at least one currency was dropped from convertedTotal due to missing FX. */
  convertedPartial: boolean;
  /** Currencies that could not be converted into displayCurrency. */
  missingFxCurrencies: string[];
}
