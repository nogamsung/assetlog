# Changelog

## [1.0.1](https://github.com/nogamsung/assetlog/compare/v1.0.0...v1.0.1) (2026-05-20)


### Bug Fixes

* **toss:** net out source withholding on KRW dividends + interest ([#192](https://github.com/nogamsung/assetlog/issues/192)) ([468c2a8](https://github.com/nogamsung/assetlog/commit/468c2a8ffcf895bae4bda15e04609a6e906161c0))

## [1.0.0](https://github.com/nogamsung/assetlog/compare/v0.13.2...v1.0.0) (2026-05-19)


### ⚠ BREAKING CHANGES

* **backend:** single-user password-only auth + rate limit ([#32](https://github.com/nogamsung/assetlog/issues/32))

### Features

* add market indices strip on dashboard ([#60](https://github.com/nogamsung/assetlog/issues/60)) ([bfe8e09](https://github.com/nogamsung/assetlog/commit/bfe8e095d28a29bcf5fca19130facfcbb07abe18))
* auth UI + AssetSymbol/UserAsset API ([#4](https://github.com/nogamsung/assetlog/issues/4)) ([b923777](https://github.com/nogamsung/assetlog/commit/b923777fdb23c67e76af2e50d595e88ae5a66125))
* **backend:** add tag column + filter to transactions ([#24](https://github.com/nogamsung/assetlog/issues/24)) ([d7a16f9](https://github.com/nogamsung/assetlog/commit/d7a16f93c5e621075cd5b94cfb2af9a667ee5b2b))
* **backend:** add TWR / MWR(IRR) performance metrics ([#61](https://github.com/nogamsung/assetlog/issues/61)) ([#97](https://github.com/nogamsung/assetlog/issues/97)) ([dbe926a](https://github.com/nogamsung/assetlog/commit/dbe926ab3943e18378b8968040ffbd70b4d00980))
* **backend:** benchmark comparison vs market indices ([#62](https://github.com/nogamsung/assetlog/issues/62)) ([#103](https://github.com/nogamsung/assetlog/issues/103)) ([683b464](https://github.com/nogamsung/assetlog/commit/683b464f8a1d5ff2d862d6a1a1c20424181fbcf8))
* **backend:** brute-force hardening — DB-persisted, global limit, backoff ([#35](https://github.com/nogamsung/assetlog/issues/35)) ([70d69c9](https://github.com/nogamsung/assetlog/commit/70d69c99c07dc0a16692fce4456524a4410079dd))
* **backend:** CashAccount.interest_rate_annual field ([#76](https://github.com/nogamsung/assetlog/issues/76)) ([#108](https://github.com/nogamsung/assetlog/issues/108)) ([fbe985d](https://github.com/nogamsung/assetlog/commit/fbe985d1ce21a5c7f7dee1c305d963ba968557df))
* **backend:** dividend calendar + yield-on-cost endpoints ([#68](https://github.com/nogamsung/assetlog/issues/68)) ([#107](https://github.com/nogamsung/assetlog/issues/107)) ([c74446b](https://github.com/nogamsung/assetlog/commit/c74446b8fea528597ce335c349812b9c9586ef34))
* **backend:** external symbol search fallback via adapters ([#9](https://github.com/nogamsung/assetlog/issues/9)) ([1cef428](https://github.com/nogamsung/assetlog/commit/1cef4284266b0f2d8aa7c4331d66d9525ce89c20))
* **backend:** FX adapter chain (Frankfurter primary, Fawaz fallback) ([#45](https://github.com/nogamsung/assetlog/issues/45)) ([1fe7887](https://github.com/nogamsung/assetlog/commit/1fe78870b7c46d2181c99f148946c1625327ca4e))
* **backend:** FX rates + portfolio summary currency conversion ([#22](https://github.com/nogamsung/assetlog/issues/22)) ([3e7ab7c](https://github.com/nogamsung/assetlog/commit/3e7ab7c8e6ea5e999d341b124e0b656ebcaac038))
* **backend:** holdings currency conversion (?convert_to) ([#30](https://github.com/nogamsung/assetlog/issues/30)) ([36575f2](https://github.com/nogamsung/assetlog/commit/36575f25e0703a7b51d233466c306e432e0f50a7))
* **backend:** hourly price-refresh scheduler + 3 asset adapters ([#8](https://github.com/nogamsung/assetlog/issues/8)) ([ddd940f](https://github.com/nogamsung/assetlog/commit/ddd940f3cb49c024db66e071b83641be1d8f117c))
* **backend:** Korean capital-gains-tax estimator ([#69](https://github.com/nogamsung/assetlog/issues/69)) ([#111](https://github.com/nogamsung/assetlog/issues/111)) ([4b10c26](https://github.com/nogamsung/assetlog/commit/4b10c26bd097f3e98fb4c39b4f5dcdb423e35eaa))
* **backend:** Korean dividend-income tax estimator ([#70](https://github.com/nogamsung/assetlog/issues/70)) ([#112](https://github.com/nogamsung/assetlog/issues/112)) ([0226e33](https://github.com/nogamsung/assetlog/commit/0226e33269c2d14daafe23fe14d2ce65527a4ac6))
* **backend:** KR stock dividend tracking via pykrx ([#65](https://github.com/nogamsung/assetlog/issues/65)) ([#102](https://github.com/nogamsung/assetlog/issues/102)) ([bc2be36](https://github.com/nogamsung/assetlog/commit/bc2be36a87817970cfceb7684f8ecb76ab289cfb))
* **backend:** monthly returns heatmap endpoint ([#67](https://github.com/nogamsung/assetlog/issues/67)) ([#106](https://github.com/nogamsung/assetlog/issues/106)) ([acff7ea](https://github.com/nogamsung/assetlog/commit/acff7ea7e31771be68fd0a3dad97f4f920211648))
* **backend:** MVP scaffold — async SQLAlchemy + MySQL + uv ([#2](https://github.com/nogamsung/assetlog/issues/2)) ([790d6f9](https://github.com/nogamsung/assetlog/commit/790d6f93deecce66ba09a202fd4bc0912a06fa9d))
* **backend:** per-tag transaction flow breakdown ([#28](https://github.com/nogamsung/assetlog/issues/28)) ([137e4c6](https://github.com/nogamsung/assetlog/commit/137e4c64be8993d0edd97feb51bb0cb8227d355d))
* **backend:** portfolio value time-series API ([#12](https://github.com/nogamsung/assetlog/issues/12)) ([c85f5a6](https://github.com/nogamsung/assetlog/commit/c85f5a60b874a859a2b7ef2047901b5bcac375ea))
* **backend:** rebalance suggestion endpoint ([#72](https://github.com/nogamsung/assetlog/issues/72)) ([#110](https://github.com/nogamsung/assetlog/issues/110)) ([91a1915](https://github.com/nogamsung/assetlog/commit/91a1915abe7a5b21c082cfa0f9fccb669e6a7c4f))
* **backend:** risk metrics — annualised return / vol / Sharpe / MDD ([#66](https://github.com/nogamsung/assetlog/issues/66)) ([#105](https://github.com/nogamsung/assetlog/issues/105)) ([8ab05e0](https://github.com/nogamsung/assetlog/commit/8ab05e0e68e04c90fb8c688c06dbabfb60919a7d))
* **backend:** sample portfolio seed endpoint ([#26](https://github.com/nogamsung/assetlog/issues/26)) ([3b8fea6](https://github.com/nogamsung/assetlog/commit/3b8fea68bd7eb48c56aea378bf886a887978c948))
* **backend:** SELL transactions + realized P&L (weighted average) ([#14](https://github.com/nogamsung/assetlog/issues/14)) ([d934afe](https://github.com/nogamsung/assetlog/commit/d934afebdac65cc07965a5d0a73c02c8e8cbd79d))
* **backend:** single-user password-only auth + rate limit ([#32](https://github.com/nogamsung/assetlog/issues/32)) ([6535980](https://github.com/nogamsung/assetlog/commit/6535980b1d490633018b755f07305cc72fbf5c45))
* **backend:** target asset allocation ([#71](https://github.com/nogamsung/assetlog/issues/71)) ([#109](https://github.com/nogamsung/assetlog/issues/109)) ([e1d2a3d](https://github.com/nogamsung/assetlog/commit/e1d2a3d87e6760b8b7b3168e15f61a5673169d47))
* **backend:** Toss Securities PDF transaction import ([#93](https://github.com/nogamsung/assetlog/issues/93)) ([#123](https://github.com/nogamsung/assetlog/issues/123)) ([435cb88](https://github.com/nogamsung/assetlog/commit/435cb88f523816115df0b17c0ebb091a767a5f84))
* **backend:** transaction CSV bulk import ([#20](https://github.com/nogamsung/assetlog/issues/20)) ([1e23d63](https://github.com/nogamsung/assetlog/commit/1e23d63be2bd2dff332f63a290d5e251539c3a45))
* **backend:** transaction edit endpoint (PUT) ([#16](https://github.com/nogamsung/assetlog/issues/16)) ([0716185](https://github.com/nogamsung/assetlog/commit/07161857aa98e4474b2fe2ddd179c559cc5462ba))
* **backend:** Upbit read-only API sync ([#87](https://github.com/nogamsung/assetlog/issues/87)) ([#101](https://github.com/nogamsung/assetlog/issues/101)) ([fbe82d8](https://github.com/nogamsung/assetlog/commit/fbe82d8ac9f38fff09a4f65cd1e987b907d424a9))
* **backend:** US stock dividend tracking via yfinance ([#64](https://github.com/nogamsung/assetlog/issues/64)) ([#99](https://github.com/nogamsung/assetlog/issues/99)) ([3cd51aa](https://github.com/nogamsung/assetlog/commit/3cd51aa7605637963f3ee81302d8c2d5f7b92eb5))
* **backend:** user data export endpoint (JSON / CSV ZIP) ([#36](https://github.com/nogamsung/assetlog/issues/36)) ([bc094fd](https://github.com/nogamsung/assetlog/commit/bc094fd64de4a360a2e58d080a85e25edecdaf50))
* bulk transactions (multi-symbol CSV + manual grid) ([#47](https://github.com/nogamsung/assetlog/issues/47)) ([825f0eb](https://github.com/nogamsung/assetlog/commit/825f0ebf08ed9d4c268afd4241d20249246eca06))
* cash holdings (multi-currency balance + portfolio integration) ([#50](https://github.com/nogamsung/assetlog/issues/50)) ([d5ab6d7](https://github.com/nogamsung/assetlog/commit/d5ab6d70b0f2abc6399c23f0149780f79fb0440a))
* **fullstack:** split P&L into price vs FX components ([#63](https://github.com/nogamsung/assetlog/issues/63)) ([#98](https://github.com/nogamsung/assetlog/issues/98)) ([c712a28](https://github.com/nogamsung/assetlog/commit/c712a2842b0342a22e21c915976f25e01a79254d))
* **history:** back-fill historical prices so the portfolio chart spans imports ([#152](https://github.com/nogamsung/assetlog/issues/152)) ([75e622c](https://github.com/nogamsung/assetlog/commit/75e622c2030cfedc62509541372d8e20fd0db797))
* **history:** group holdings by asset class + add history page ([#178](https://github.com/nogamsung/assetlog/issues/178)) ([9e21526](https://github.com/nogamsung/assetlog/commit/9e21526e7169c235315d48255e33c242e1e4396e))
* **holdings:** show 1d/7d/30d price change percentages ([#180](https://github.com/nogamsung/assetlog/issues/180)) ([14d23b6](https://github.com/nogamsung/assetlog/commit/14d23b657cc7ffabf2dbc1da73a2db5fa8b9072d))
* **import:** add K-Bank parser, multi-file upload, source rename ([#169](https://github.com/nogamsung/assetlog/issues/169)) ([5bff298](https://github.com/nogamsung/assetlog/commit/5bff298ad60d70a362ffea8c1f305bdc993c3c54))
* **import:** add Shinhan Investment & Securities PDF parser ([#150](https://github.com/nogamsung/assetlog/issues/150)) ([f1bb5ec](https://github.com/nogamsung/assetlog/commit/f1bb5ecd75123c49a3589e2164426e80446eca93))
* **income:** surface dividend history on asset detail + interest page ([#145](https://github.com/nogamsung/assetlog/issues/145)) ([6237f78](https://github.com/nogamsung/assetlog/commit/6237f786a1abf1ab912ef909f26ffb5b7b9fb38b))
* net-worth UI, crypto name resolver (Upbit), BTC index label ([#161](https://github.com/nogamsung/assetlog/issues/161)) ([dbb2dbb](https://github.com/nogamsung/assetlog/commit/dbb2dbb39f002398a698c79b86f726d47c39322f))
* per-account cash balance, indices grid, BTC label cleanup ([#165](https://github.com/nogamsung/assetlog/issues/165)) ([7d7b5ef](https://github.com/nogamsung/assetlog/commit/7d7b5ef7ba0e02f8c7430cc243142564ebacb33b))
* Portfolio summary/holdings API + Dashboard UI ([#7](https://github.com/nogamsung/assetlog/issues/7)) ([79c2862](https://github.com/nogamsung/assetlog/commit/79c2862a0fb69770ba7fe2d8c33e8836bcefe12e))
* **portfolio:** track every cash flow to compute net worth ([#160](https://github.com/nogamsung/assetlog/issues/160)) ([6acc9e2](https://github.com/nogamsung/assetlog/commit/6acc9e2c9f94f68d03f38d6b538e88f22cba4023))
* **scheduler:** refresh prices every 10 minutes (was hourly) ([#173](https://github.com/nogamsung/assetlog/issues/173)) ([8733bb8](https://github.com/nogamsung/assetlog/commit/8733bb8b6499eee0981f156b51432c29ce998fbc))
* **toss/shinhan:** auto-resolve Korean security names → KRX 6-digit codes ([#153](https://github.com/nogamsung/assetlog/issues/153)) ([863a9c2](https://github.com/nogamsung/assetlog/commit/863a9c2ac19ea2c202756bbfe3deec522a9cc9e1))
* **toss:** auto-resolve unknown ISINs to tickers via OpenFIGI + DB cache ([#147](https://github.com/nogamsung/assetlog/issues/147)) ([51c2c4e](https://github.com/nogamsung/assetlog/commit/51c2c4e215db06ad0cfb5990211f6d2b986f7caa))
* Transaction (BUY) API + asset add flow UI ([#5](https://github.com/nogamsung/assetlog/issues/5)) ([2e394d3](https://github.com/nogamsung/assetlog/commit/2e394d31375922289ca1428656974b8d1d9dbc2a))
* **upbit+portfolio:** Upbit cash flow + cash in allocation + clearer total ([#166](https://github.com/nogamsung/assetlog/issues/166)) ([5eaf112](https://github.com/nogamsung/assetlog/commit/5eaf1127b5ebd42dda95376289e733a58e40d59c))
* **upbit:** 3-phase fallback when sync returns no trades ([#138](https://github.com/nogamsung/assetlog/issues/138)) ([15f70fc](https://github.com/nogamsung/assetlog/commit/15f70fcc44f276605916635097b0df0badb174b4))
* **upbit:** fetch ALL closed orders via /v1/orders/closed (no symbol filter) ([#139](https://github.com/nogamsung/assetlog/issues/139)) ([ca22c25](https://github.com/nogamsung/assetlog/commit/ca22c2598763d28dc01b7951f6023cfa294abd48))
* **upbit:** PDF import, daily price-point upsert, drop API sync UI ([#175](https://github.com/nogamsung/assetlog/issues/175)) ([d0213fd](https://github.com/nogamsung/assetlog/commit/d0213fdcf6b9e6ade88a5d1e479078e4882fd32b))
* **upbit:** re-enable PDF import with coord-based row parser ([#177](https://github.com/nogamsung/assetlog/issues/177)) ([5de286c](https://github.com/nogamsung/assetlog/commit/5de286ca5397ebe6b573f9571f8aebc5c175d095))
* **upbit:** synthesize BUY trades from current holdings (avg_buy_price) ([#140](https://github.com/nogamsung/assetlog/issues/140)) ([feac79a](https://github.com/nogamsung/assetlog/commit/feac79affef0d2539b711f884353585e109552a1))
* User auth (httpOnly cookie JWT) + frontend bootstrap ([#3](https://github.com/nogamsung/assetlog/issues/3)) ([a71346a](https://github.com/nogamsung/assetlog/commit/a71346a19911b7c1a97dd45937f0e1afc965f16f))


### Bug Fixes

* **#93:** preserve import result panel + Dividend enum/timezone ([#129](https://github.com/nogamsung/assetlog/issues/129)) ([f3bb012](https://github.com/nogamsung/assetlog/commit/f3bb012517ce3466b3fa3e360fb13fb0d70df781))
* **allocation:** normalise pie wedges to a base currency (KRW) ([#164](https://github.com/nogamsung/assetlog/issues/164)) ([1bd88ab](https://github.com/nogamsung/assetlog/commit/1bd88abc603a49917c1a4772ec8b47d6d1d0d0e7))
* **auth:** COOKIE_DOMAIN env to share session across sibling subdomains ([#115](https://github.com/nogamsung/assetlog/issues/115)) ([f75b853](https://github.com/nogamsung/assetlog/commit/f75b85381d9bdaa6ed46a891d0208ebb0ab42554))
* **cash:** ignore Upbit balance-reconciliation trades when summing cash ([#168](https://github.com/nogamsung/assetlog/issues/168)) ([f5db8c8](https://github.com/nogamsung/assetlog/commit/f5db8c88c45b42eb003b61eac02b08dc0abe2e91))
* **crypto+history:** base-only ticker default quote + drop NaN bars ([#162](https://github.com/nogamsung/assetlog/issues/162)) ([8ba4d22](https://github.com/nogamsung/assetlog/commit/8ba4d2228e6090c5454c07b298aa3baa470c10dc))
* **dashboard:** correct Toss FX cash + history avg + PnL + allocation FX ([#182](https://github.com/nogamsung/assetlog/issues/182)) ([3a49d39](https://github.com/nogamsung/assetlog/commit/3a49d398225819cb1bf3d2caa8997399197425bc))
* **history:** make /history/backfill fire-and-forget so it doesn't block imports ([#156](https://github.com/nogamsung/assetlog/issues/156)) ([356bb57](https://github.com/nogamsung/assetlog/commit/356bb5741f1e64864420c2ad84e4b660781bf5d2))
* **history:** per-bucket historical FX so KRW chart includes USD holdings ([#167](https://github.com/nogamsung/assetlog/issues/167)) ([79c8516](https://github.com/nogamsung/assetlog/commit/79c8516338e08cf1f0152caca348a4b4e457a611))
* **import:** dedupe dividends by (symbol_id, ex_date) so re-imports don't crash ([#157](https://github.com/nogamsung/assetlog/issues/157)) ([d391a0e](https://github.com/nogamsung/assetlog/commit/d391a0e012282d705bc8d1f98d3c82ec9a135bc0))
* **import:** never abort import on resolver failure ([#155](https://github.com/nogamsung/assetlog/issues/155)) ([1fa824b](https://github.com/nogamsung/assetlog/commit/1fa824b236ae78f4185cd0274d89ceb015eb42a0))
* **import:** wrap resolver cache reads + writes in SAVEPOINTs ([#158](https://github.com/nogamsung/assetlog/issues/158)) ([0cbe3fc](https://github.com/nogamsung/assetlog/commit/0cbe3fc6f113c479bbb66009516fddbf06db77d9))
* **migrations:** look up user_assets.user_id FK name at runtime ([#118](https://github.com/nogamsung/assetlog/issues/118)) ([5ea7172](https://github.com/nogamsung/assetlog/commit/5ea7172d21fea70d9510b53c3ecc5d53c3ea72ca))
* **portfolio:** BUY before SELL when traded_at ties (DB-side) ([#183](https://github.com/nogamsung/assetlog/issues/183)) ([f22c47f](https://github.com/nogamsung/assetlog/commit/f22c47f61586ee6ba4f5a0fda3f6d9dc6a17d218))
* **portfolio:** hide fully-closed positions (qty == 0) from holdings ([#144](https://github.com/nogamsung/assetlog/issues/144)) ([b1a9e4e](https://github.com/nogamsung/assetlog/commit/b1a9e4e758c6c11445c38af8b0e6d759ab09d037))
* **portfolio:** moving-weighted average cost basis so SELL flushes cost ([c1dacfe](https://github.com/nogamsung/assetlog/commit/c1dacfe5be9f1adab63eb97f0e4760affe85357c))
* **price:** KR yfinance fallback + crypto display name on import ([#154](https://github.com/nogamsung/assetlog/issues/154)) ([17f746d](https://github.com/nogamsung/assetlog/commit/17f746d53594a936ff822969946cc2b61fa7122a))
* **schema:** add dividends external_id + cash_account_transactions to bootstrap ([#93](https://github.com/nogamsung/assetlog/issues/93)) ([#131](https://github.com/nogamsung/assetlog/issues/131)) ([b103dbb](https://github.com/nogamsung/assetlog/commit/b103dbb274759c3bd1de783db99e0c46dba6ffb7))
* **schema:** add missing tables to bootstrap schema.sql ([#117](https://github.com/nogamsung/assetlog/issues/117)) ([d5eceb3](https://github.com/nogamsung/assetlog/commit/d5eceb3f9f70afcacb00b1e8dfa7f64e63b2a98b))
* **schema:** cash_account_transactions FK type + Upbit env docs ([#133](https://github.com/nogamsung/assetlog/issues/133)) ([e611e98](https://github.com/nogamsung/assetlog/commit/e611e98b46ba87638afbb427598b600fdf345ad8))
* **toss:** add 5 more US ISIN→ticker mappings from historical statements ([#146](https://github.com/nogamsung/assetlog/issues/146)) ([dc2d343](https://github.com/nogamsung/assetlog/commit/dc2d34399b66671584a740e8584074a11eab8fd9))
* **toss:** map remaining US ISINs in sample statement to tickers ([#143](https://github.com/nogamsung/assetlog/issues/143)) ([26bca36](https://github.com/nogamsung/assetlog/commit/26bca364f870102677080bb617402b96c41f0b42))
* **toss:** order same-minute BUY before SELL when round trip nets to zero ([#181](https://github.com/nogamsung/assetlog/issues/181)) ([092098f](https://github.com/nogamsung/assetlog/commit/092098f81bbb8de17494075ab1df82ce77056399))
* **toss:** preserve security name + map US ISINs to tickers ([#142](https://github.com/nogamsung/assetlog/issues/142)) ([adf3cc0](https://github.com/nogamsung/assetlog/commit/adf3cc0545842ba39752e04e1dab3976fa0dd757))
* **toss:** route 환전외화입금취소 to transfer_out, not transfer_in ([#188](https://github.com/nogamsung/assetlog/issues/188)) ([d14a9c0](https://github.com/nogamsung/assetlog/commit/d14a9c06d8534fa941de1a4b04fbacd9ff17d1a2))
* **toss:** subtract trade fees from cash so Toss balance matches reality ([#189](https://github.com/nogamsung/assetlog/issues/189)) ([db588e1](https://github.com/nogamsung/assetlog/commit/db588e1a49c28a00b03d805d28bc35a1cf5be779))
* **transaction:** BUY before SELL in remaining two cost-basis walks ([#184](https://github.com/nogamsung/assetlog/issues/184)) ([467f659](https://github.com/nogamsung/assetlog/commit/467f65988aaf701f43eff6fa753f9880ea58f241))
* **upbit:** exact balance reconciliation + price/qty quantize (no truncate) ([#141](https://github.com/nogamsung/assetlog/issues/141)) ([9420440](https://github.com/nogamsung/assetlog/commit/9420440e01b3707aede169f78f4d838c57e2ba62))
* **upbit:** expand fetch window + diagnostic logs for empty sync ([#135](https://github.com/nogamsung/assetlog/issues/135)) ([e25ec4f](https://github.com/nogamsung/assetlog/commit/e25ec4f82417134ed669508d374f2d84861ff29f))
* **upbit:** handle list-shaped 'info' from Upbit fetch_balance ([#134](https://github.com/nogamsung/assetlog/issues/134)) ([096b61d](https://github.com/nogamsung/assetlog/commit/096b61d95dee2a3fb8734352aee65a2b9c614c2d))
* **upbit:** pre-resolve markets via load_markets, drop since, log at WARNING ([#137](https://github.com/nogamsung/assetlog/issues/137)) ([8751058](https://github.com/nogamsung/assetlog/commit/875105863e07a0aba86e84246ce9b0571c011961))
* **upbit:** reconcile KRW cash to live balance + paginate cash history ([#172](https://github.com/nogamsung/assetlog/issues/172)) ([1af6a74](https://github.com/nogamsung/assetlog/commit/1af6a74d21559c55957e03c3da57aca24334eb20))
* **upbit:** use fetch_closed_orders (fetch_my_trades is unsupported on Upbit) ([#136](https://github.com/nogamsung/assetlog/issues/136)) ([07de515](https://github.com/nogamsung/assetlog/commit/07de51507ca2eb604cb35ae0766d9fa71c65426a))


### Refactor

* drop users table for single-owner mode ([#44](https://github.com/nogamsung/assetlog/issues/44)) ([cb20296](https://github.com/nogamsung/assetlog/commit/cb20296b2c433fdbdb47e22de50958761212dc4b))
* **toss:** retire hand-curated ISIN→ticker map; delegate to resolver ([#149](https://github.com/nogamsung/assetlog/issues/149)) ([65853e7](https://github.com/nogamsung/assetlog/commit/65853e729779bb926fd65d2969c8280b68e7f78e))


### Documentation

* README updates for [#93](https://github.com/nogamsung/assetlog/issues/93) (file import + Upbit sync UI + KST display) ([#127](https://github.com/nogamsung/assetlog/issues/127)) ([96a6947](https://github.com/nogamsung/assetlog/commit/96a6947fbc4e6c7faed0614ed318ec5f11dfe522))


### Chores

* add docker deploy scripts for backend/frontend ([#59](https://github.com/nogamsung/assetlog/issues/59)) ([111fa23](https://github.com/nogamsung/assetlog/commit/111fa231870d007eb0b76706d54bd88debf566f6))
* add release-please + GHCR Docker publish pipeline ([#53](https://github.com/nogamsung/assetlog/issues/53)) ([031abeb](https://github.com/nogamsung/assetlog/commit/031abebfda4d21dce96f1b7a0855b1914e74f765))
* **backend:** add schema.sql bootstrap for fresh MySQL setup ([#43](https://github.com/nogamsung/assetlog/issues/43)) ([6f4cc6b](https://github.com/nogamsung/assetlog/commit/6f4cc6b0807c87d6e120e6ee319a2d363d8ca723))
* **backend:** sync uv.lock to 0.10.0 ([#57](https://github.com/nogamsung/assetlog/issues/57)) ([1cbf252](https://github.com/nogamsung/assetlog/commit/1cbf252930d59cfeea86ce318306d6179baee4bf))
* bump version 0.1.0 → 0.9.0 ([#42](https://github.com/nogamsung/assetlog/issues/42)) ([01ea1ae](https://github.com/nogamsung/assetlog/commit/01ea1ae06de469fdaf78db9f6ad1c592755a8e34))
* **fx:** seed daily FX rates from 2022-01-01 (USD/KRW/EUR) ([#174](https://github.com/nogamsung/assetlog/issues/174)) ([6b285ec](https://github.com/nogamsung/assetlog/commit/6b285ec4aef21504bb85b8bfe7c8b32b3c97e8ea))
* install Claude Code harness + asset-tracking PRD ([#1](https://github.com/nogamsung/assetlog/issues/1)) ([2ba8f2e](https://github.com/nogamsung/assetlog/commit/2ba8f2e98c74fcdde845e9ecdaf7f9f53dcad7a0))
* local-dev env setup + alembic heads merge ([#10](https://github.com/nogamsung/assetlog/issues/10)) ([2143405](https://github.com/nogamsung/assetlog/commit/21434055986de4e91d5d7cadb4b7191fd90bd035))
* release main ([#104](https://github.com/nogamsung/assetlog/issues/104)) ([e4281d8](https://github.com/nogamsung/assetlog/commit/e4281d8fb114bd52c0402bfd715507eeb345cb1e))
* release main ([#116](https://github.com/nogamsung/assetlog/issues/116)) ([9828d5e](https://github.com/nogamsung/assetlog/commit/9828d5e0752278582d920fbabf1927fdedb7ea2a))
* release main ([#119](https://github.com/nogamsung/assetlog/issues/119)) ([108449a](https://github.com/nogamsung/assetlog/commit/108449afc1a66712dc269b3b5fbe8d8f41a09723))
* release main ([#121](https://github.com/nogamsung/assetlog/issues/121)) ([e2ee935](https://github.com/nogamsung/assetlog/commit/e2ee935b85c2575cc033395c5e00f1edc1d4580d))
* release main ([#130](https://github.com/nogamsung/assetlog/issues/130)) ([4f1b00d](https://github.com/nogamsung/assetlog/commit/4f1b00d1fffcf05a4d51c6702f4bdf8fe988d995))
* release main ([#132](https://github.com/nogamsung/assetlog/issues/132)) ([a990d56](https://github.com/nogamsung/assetlog/commit/a990d568e8565c48baa8a1fe494d14dd51f9424d))
* release main ([#54](https://github.com/nogamsung/assetlog/issues/54)) ([ab69f8d](https://github.com/nogamsung/assetlog/commit/ab69f8d369e98644e3f48651f1c23e758ad37af0))
* release main ([#58](https://github.com/nogamsung/assetlog/issues/58)) ([1eef448](https://github.com/nogamsung/assetlog/commit/1eef448f1e8acf282c0992f64aa48aeb18ff6429))
* **schema:** add isin_ticker_cache + kr_name_cache to bootstrap SQL ([#159](https://github.com/nogamsung/assetlog/issues/159)) ([ebbbe61](https://github.com/nogamsung/assetlog/commit/ebbbe618e9b183fd621ec4e9e7cbcf15b06abbac))
* tech debt cleanup — chart format extraction + alembic mypy fix ([#18](https://github.com/nogamsung/assetlog/issues/18)) ([034f1dd](https://github.com/nogamsung/assetlog/commit/034f1dd0bf647df5d6aa6614eb382669e5e2deb8))
* **toss:** cleanup migration + KODEX 레버리지 diagnostic ([#185](https://github.com/nogamsung/assetlog/issues/185)) ([d0acfb2](https://github.com/nogamsung/assetlog/commit/d0acfb23f0d6c8339bdd7659cac50a5ee515fa88))
* upgrade claude code starter to v1.36.0 ([#120](https://github.com/nogamsung/assetlog/issues/120)) ([fa50804](https://github.com/nogamsung/assetlog/commit/fa50804bc0a469ff11643c6fba2005fc72a88b4a))

## [0.13.2](https://github.com/nogamsung/assetlog/compare/v0.13.1...v0.13.2) (2026-05-12)


### Bug Fixes

* **schema:** add dividends external_id + cash_account_transactions to bootstrap ([#93](https://github.com/nogamsung/assetlog/issues/93)) ([#131](https://github.com/nogamsung/assetlog/issues/131)) ([b103dbb](https://github.com/nogamsung/assetlog/commit/b103dbb274759c3bd1de783db99e0c46dba6ffb7))

## [0.13.1](https://github.com/nogamsung/assetlog/compare/v0.13.0...v0.13.1) (2026-05-12)


### Bug Fixes

* **#93:** preserve import result panel + Dividend enum/timezone ([#129](https://github.com/nogamsung/assetlog/issues/129)) ([f3bb012](https://github.com/nogamsung/assetlog/commit/f3bb012517ce3466b3fa3e360fb13fb0d70df781))

## [0.13.0](https://github.com/nogamsung/assetlog/compare/v0.12.2...v0.13.0) (2026-05-12)


### Features

* **backend:** Toss Securities PDF transaction import ([#93](https://github.com/nogamsung/assetlog/issues/93)) ([#123](https://github.com/nogamsung/assetlog/issues/123)) ([435cb88](https://github.com/nogamsung/assetlog/commit/435cb88f523816115df0b17c0ebb091a767a5f84))


### Documentation

* README updates for [#93](https://github.com/nogamsung/assetlog/issues/93) (file import + Upbit sync UI + KST display) ([#127](https://github.com/nogamsung/assetlog/issues/127)) ([96a6947](https://github.com/nogamsung/assetlog/commit/96a6947fbc4e6c7faed0614ed318ec5f11dfe522))


### Chores

* upgrade claude code starter to v1.36.0 ([#120](https://github.com/nogamsung/assetlog/issues/120)) ([fa50804](https://github.com/nogamsung/assetlog/commit/fa50804bc0a469ff11643c6fba2005fc72a88b4a))

## [0.12.2](https://github.com/nogamsung/assetlog/compare/v0.12.1...v0.12.2) (2026-05-11)


### Bug Fixes

* **migrations:** look up user_assets.user_id FK name at runtime ([#118](https://github.com/nogamsung/assetlog/issues/118)) ([5ea7172](https://github.com/nogamsung/assetlog/commit/5ea7172d21fea70d9510b53c3ecc5d53c3ea72ca))
* **schema:** add missing tables to bootstrap schema.sql ([#117](https://github.com/nogamsung/assetlog/issues/117)) ([d5eceb3](https://github.com/nogamsung/assetlog/commit/d5eceb3f9f70afcacb00b1e8dfa7f64e63b2a98b))

## [0.12.1](https://github.com/nogamsung/assetlog/compare/v0.12.0...v0.12.1) (2026-05-11)


### Bug Fixes

* **auth:** COOKIE_DOMAIN env to share session across sibling subdomains ([#115](https://github.com/nogamsung/assetlog/issues/115)) ([f75b853](https://github.com/nogamsung/assetlog/commit/f75b85381d9bdaa6ed46a891d0208ebb0ab42554))

## [0.12.0](https://github.com/nogamsung/assetlog/compare/v0.11.0...v0.12.0) (2026-05-11)


### Features

* **backend:** add TWR / MWR(IRR) performance metrics ([#61](https://github.com/nogamsung/assetlog/issues/61)) ([#97](https://github.com/nogamsung/assetlog/issues/97)) ([dbe926a](https://github.com/nogamsung/assetlog/commit/dbe926ab3943e18378b8968040ffbd70b4d00980))
* **backend:** benchmark comparison vs market indices ([#62](https://github.com/nogamsung/assetlog/issues/62)) ([#103](https://github.com/nogamsung/assetlog/issues/103)) ([683b464](https://github.com/nogamsung/assetlog/commit/683b464f8a1d5ff2d862d6a1a1c20424181fbcf8))
* **backend:** CashAccount.interest_rate_annual field ([#76](https://github.com/nogamsung/assetlog/issues/76)) ([#108](https://github.com/nogamsung/assetlog/issues/108)) ([fbe985d](https://github.com/nogamsung/assetlog/commit/fbe985d1ce21a5c7f7dee1c305d963ba968557df))
* **backend:** dividend calendar + yield-on-cost endpoints ([#68](https://github.com/nogamsung/assetlog/issues/68)) ([#107](https://github.com/nogamsung/assetlog/issues/107)) ([c74446b](https://github.com/nogamsung/assetlog/commit/c74446b8fea528597ce335c349812b9c9586ef34))
* **backend:** Korean capital-gains-tax estimator ([#69](https://github.com/nogamsung/assetlog/issues/69)) ([#111](https://github.com/nogamsung/assetlog/issues/111)) ([4b10c26](https://github.com/nogamsung/assetlog/commit/4b10c26bd097f3e98fb4c39b4f5dcdb423e35eaa))
* **backend:** Korean dividend-income tax estimator ([#70](https://github.com/nogamsung/assetlog/issues/70)) ([#112](https://github.com/nogamsung/assetlog/issues/112)) ([0226e33](https://github.com/nogamsung/assetlog/commit/0226e33269c2d14daafe23fe14d2ce65527a4ac6))
* **backend:** KR stock dividend tracking via pykrx ([#65](https://github.com/nogamsung/assetlog/issues/65)) ([#102](https://github.com/nogamsung/assetlog/issues/102)) ([bc2be36](https://github.com/nogamsung/assetlog/commit/bc2be36a87817970cfceb7684f8ecb76ab289cfb))
* **backend:** monthly returns heatmap endpoint ([#67](https://github.com/nogamsung/assetlog/issues/67)) ([#106](https://github.com/nogamsung/assetlog/issues/106)) ([acff7ea](https://github.com/nogamsung/assetlog/commit/acff7ea7e31771be68fd0a3dad97f4f920211648))
* **backend:** rebalance suggestion endpoint ([#72](https://github.com/nogamsung/assetlog/issues/72)) ([#110](https://github.com/nogamsung/assetlog/issues/110)) ([91a1915](https://github.com/nogamsung/assetlog/commit/91a1915abe7a5b21c082cfa0f9fccb669e6a7c4f))
* **backend:** risk metrics — annualised return / vol / Sharpe / MDD ([#66](https://github.com/nogamsung/assetlog/issues/66)) ([#105](https://github.com/nogamsung/assetlog/issues/105)) ([8ab05e0](https://github.com/nogamsung/assetlog/commit/8ab05e0e68e04c90fb8c688c06dbabfb60919a7d))
* **backend:** target asset allocation ([#71](https://github.com/nogamsung/assetlog/issues/71)) ([#109](https://github.com/nogamsung/assetlog/issues/109)) ([e1d2a3d](https://github.com/nogamsung/assetlog/commit/e1d2a3d87e6760b8b7b3168e15f61a5673169d47))
* **backend:** Upbit read-only API sync ([#87](https://github.com/nogamsung/assetlog/issues/87)) ([#101](https://github.com/nogamsung/assetlog/issues/101)) ([fbe82d8](https://github.com/nogamsung/assetlog/commit/fbe82d8ac9f38fff09a4f65cd1e987b907d424a9))
* **backend:** US stock dividend tracking via yfinance ([#64](https://github.com/nogamsung/assetlog/issues/64)) ([#99](https://github.com/nogamsung/assetlog/issues/99)) ([3cd51aa](https://github.com/nogamsung/assetlog/commit/3cd51aa7605637963f3ee81302d8c2d5f7b92eb5))
* **fullstack:** split P&L into price vs FX components ([#63](https://github.com/nogamsung/assetlog/issues/63)) ([#98](https://github.com/nogamsung/assetlog/issues/98)) ([c712a28](https://github.com/nogamsung/assetlog/commit/c712a2842b0342a22e21c915976f25e01a79254d))

## [0.11.0](https://github.com/nogamsung/assetlog/compare/v0.10.0...v0.11.0) (2026-04-29)


### Features

* add market indices strip on dashboard ([#60](https://github.com/nogamsung/assetlog/issues/60)) ([bfe8e09](https://github.com/nogamsung/assetlog/commit/bfe8e095d28a29bcf5fca19130facfcbb07abe18))


### Chores

* add docker deploy scripts for backend/frontend ([#59](https://github.com/nogamsung/assetlog/issues/59)) ([111fa23](https://github.com/nogamsung/assetlog/commit/111fa231870d007eb0b76706d54bd88debf566f6))
* **backend:** sync uv.lock to 0.10.0 ([#57](https://github.com/nogamsung/assetlog/issues/57)) ([1cbf252](https://github.com/nogamsung/assetlog/commit/1cbf252930d59cfeea86ce318306d6179baee4bf))

## [0.10.0](https://github.com/nogamsung/assetlog/compare/v0.9.0...v0.10.0) (2026-04-28)


### Features

* **backend:** FX adapter chain (Frankfurter primary, Fawaz fallback) ([#45](https://github.com/nogamsung/assetlog/issues/45)) ([1fe7887](https://github.com/nogamsung/assetlog/commit/1fe78870b7c46d2181c99f148946c1625327ca4e))
* bulk transactions (multi-symbol CSV + manual grid) ([#47](https://github.com/nogamsung/assetlog/issues/47)) ([825f0eb](https://github.com/nogamsung/assetlog/commit/825f0ebf08ed9d4c268afd4241d20249246eca06))
* cash holdings (multi-currency balance + portfolio integration) ([#50](https://github.com/nogamsung/assetlog/issues/50)) ([d5ab6d7](https://github.com/nogamsung/assetlog/commit/d5ab6d70b0f2abc6399c23f0149780f79fb0440a))


### Refactor

* drop users table for single-owner mode ([#44](https://github.com/nogamsung/assetlog/issues/44)) ([cb20296](https://github.com/nogamsung/assetlog/commit/cb20296b2c433fdbdb47e22de50958761212dc4b))


### Chores

* add release-please + GHCR Docker publish pipeline ([#53](https://github.com/nogamsung/assetlog/issues/53)) ([031abeb](https://github.com/nogamsung/assetlog/commit/031abebfda4d21dce96f1b7a0855b1914e74f765))
* **backend:** add schema.sql bootstrap for fresh MySQL setup ([#43](https://github.com/nogamsung/assetlog/issues/43)) ([6f4cc6b](https://github.com/nogamsung/assetlog/commit/6f4cc6b0807c87d6e120e6ee319a2d363d8ca723))
