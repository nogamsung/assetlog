export const COMMON_CURRENCIES = [
  { code: "KRW", label: "KRW — 한국 원" },
  { code: "USD", label: "USD — 미국 달러" },
  { code: "JPY", label: "JPY — 일본 엔" },
  { code: "EUR", label: "EUR — 유로" },
  { code: "GBP", label: "GBP — 영국 파운드" },
  { code: "CNY", label: "CNY — 중국 위안" },
  { code: "HKD", label: "HKD — 홍콩 달러" },
  { code: "SGD", label: "SGD — 싱가포르 달러" },
  { code: "AUD", label: "AUD — 호주 달러" },
  { code: "CAD", label: "CAD — 캐나다 달러" },
  { code: "CHF", label: "CHF — 스위스 프랑" },
  { code: "USDT", label: "USDT — 테더" },
  { code: "USDC", label: "USDC — USD 코인" },
] as const;

export type CommonCurrencyCode = (typeof COMMON_CURRENCIES)[number]["code"];
