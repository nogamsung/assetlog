# Changelog

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
