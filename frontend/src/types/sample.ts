export interface SampleSeedResponse {
  seeded: boolean;
  reason: string | null;
  userAssetsCreated: number;
  transactionsCreated: number;
  symbolsCreated: number;
  symbolsReused: number;
}
