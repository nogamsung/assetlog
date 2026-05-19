# Changelog

## [0.14.0](https://github.com/nogamsung/assetlog/compare/v0.13.1...v0.14.0) (2026-05-19)


### Features

* **history:** back-fill historical prices so the portfolio chart spans imports ([#152](https://github.com/nogamsung/assetlog/issues/152)) ([75e622c](https://github.com/nogamsung/assetlog/commit/75e622c2030cfedc62509541372d8e20fd0db797))
* **history:** group holdings by asset class + add history page ([#178](https://github.com/nogamsung/assetlog/issues/178)) ([9e21526](https://github.com/nogamsung/assetlog/commit/9e21526e7169c235315d48255e33c242e1e4396e))
* **history:** monthly calendar view with per-day transaction sheet ([#179](https://github.com/nogamsung/assetlog/issues/179)) ([4f69a71](https://github.com/nogamsung/assetlog/commit/4f69a717bb52ca790c86bf4f43759d7a0b57fca3))
* **holdings:** show 1d/7d/30d price change percentages ([#180](https://github.com/nogamsung/assetlog/issues/180)) ([14d23b6](https://github.com/nogamsung/assetlog/commit/14d23b657cc7ffabf2dbc1da73a2db5fa8b9072d))
* **import:** add K-Bank parser, multi-file upload, source rename ([#169](https://github.com/nogamsung/assetlog/issues/169)) ([5bff298](https://github.com/nogamsung/assetlog/commit/5bff298ad60d70a362ffea8c1f305bdc993c3c54))
* **income:** surface dividend history on asset detail + interest page ([#145](https://github.com/nogamsung/assetlog/issues/145)) ([6237f78](https://github.com/nogamsung/assetlog/commit/6237f786a1abf1ab912ef909f26ffb5b7b9fb38b))
* net-worth UI, crypto name resolver (Upbit), BTC index label ([#161](https://github.com/nogamsung/assetlog/issues/161)) ([dbb2dbb](https://github.com/nogamsung/assetlog/commit/dbb2dbb39f002398a698c79b86f726d47c39322f))
* per-account cash balance, indices grid, BTC label cleanup ([#165](https://github.com/nogamsung/assetlog/issues/165)) ([7d7b5ef](https://github.com/nogamsung/assetlog/commit/7d7b5ef7ba0e02f8c7430cc243142564ebacb33b))
* **ui:** add Shinhan option to file-import source selector ([#151](https://github.com/nogamsung/assetlog/issues/151)) ([7a7b84e](https://github.com/nogamsung/assetlog/commit/7a7b84e283a9d3b82190319f0dbec30177cf2399))
* **ui:** format quantities/prices, drop realized in list, stronger toggles ([#170](https://github.com/nogamsung/assetlog/issues/170)) ([b63e1fe](https://github.com/nogamsung/assetlog/commit/b63e1fe7936237311eb1179ec75e09d0db8bf110))
* **upbit+portfolio:** Upbit cash flow + cash in allocation + clearer total ([#166](https://github.com/nogamsung/assetlog/issues/166)) ([5eaf112](https://github.com/nogamsung/assetlog/commit/5eaf1127b5ebd42dda95376289e733a58e40d59c))
* **upbit:** PDF import, daily price-point upsert, drop API sync UI ([#175](https://github.com/nogamsung/assetlog/issues/175)) ([d0213fd](https://github.com/nogamsung/assetlog/commit/d0213fdcf6b9e6ade88a5d1e479078e4882fd32b))
* **upbit:** re-enable PDF import with coord-based row parser ([#177](https://github.com/nogamsung/assetlog/issues/177)) ([5de286c](https://github.com/nogamsung/assetlog/commit/5de286ca5397ebe6b573f9571f8aebc5c175d095))


### Bug Fixes

* **dashboard:** correct Toss FX cash + history avg + PnL + allocation FX ([#182](https://github.com/nogamsung/assetlog/issues/182)) ([3a49d39](https://github.com/nogamsung/assetlog/commit/3a49d398225819cb1bf3d2caa8997399197425bc))
* **interest:** label shinhan source as 신한투자증권 ([#171](https://github.com/nogamsung/assetlog/issues/171)) ([d0215d8](https://github.com/nogamsung/assetlog/commit/d0215d836e159f95c1e3561d950cf6272ebc4099))


### Chores

* **ui:** portfolio history refresh button + consistent dashboard polish ([#163](https://github.com/nogamsung/assetlog/issues/163)) ([62c815a](https://github.com/nogamsung/assetlog/commit/62c815a201f0d3baf36f42967995ccba79143cd0))
* **ui:** redirect / → /dashboard, tighter alignment + tactile buttons ([#148](https://github.com/nogamsung/assetlog/issues/148)) ([4c0b4fc](https://github.com/nogamsung/assetlog/commit/4c0b4fcd81b25a3f348f7c3f59c4d34dce4d46c7))

## [0.13.1](https://github.com/nogamsung/assetlog/compare/v0.13.0...v0.13.1) (2026-05-12)


### Bug Fixes

* **#93:** preserve import result panel + Dividend enum/timezone ([#129](https://github.com/nogamsung/assetlog/issues/129)) ([f3bb012](https://github.com/nogamsung/assetlog/commit/f3bb012517ce3466b3fa3e360fb13fb0d70df781))

## [0.13.0](https://github.com/nogamsung/assetlog/compare/v0.12.0...v0.13.0) (2026-05-12)


### Features

* **frontend:** file-based transaction import UI ([#93](https://github.com/nogamsung/assetlog/issues/93)) ([#124](https://github.com/nogamsung/assetlog/issues/124)) ([5b5a8af](https://github.com/nogamsung/assetlog/commit/5b5a8aff7fa268ed3c270d5a2e6258c3495fd567))
* **frontend:** KST + 24-hour time display unified ([#122](https://github.com/nogamsung/assetlog/issues/122)) ([80d010f](https://github.com/nogamsung/assetlog/commit/80d010f487422dfd65cff919c75b41f5a82c0e19))
* **frontend:** Upbit sync trigger UI in settings ([#93](https://github.com/nogamsung/assetlog/issues/93)) ([#125](https://github.com/nogamsung/assetlog/issues/125)) ([eefaed8](https://github.com/nogamsung/assetlog/commit/eefaed8f37695f0b736ecdc4895f5a506739cdcd))


### Documentation

* README updates for [#93](https://github.com/nogamsung/assetlog/issues/93) (file import + Upbit sync UI + KST display) ([#127](https://github.com/nogamsung/assetlog/issues/127)) ([96a6947](https://github.com/nogamsung/assetlog/commit/96a6947fbc4e6c7faed0614ed318ec5f11dfe522))

## [0.12.0](https://github.com/nogamsung/assetlog/compare/v0.11.0...v0.12.0) (2026-05-11)


### Features

* **fullstack:** split P&L into price vs FX components ([#63](https://github.com/nogamsung/assetlog/issues/63)) ([#98](https://github.com/nogamsung/assetlog/issues/98)) ([c712a28](https://github.com/nogamsung/assetlog/commit/c712a2842b0342a22e21c915976f25e01a79254d))


### Bug Fixes

* **ci:** bake NEXT_PUBLIC_API_URL into frontend image at build time ([#113](https://github.com/nogamsung/assetlog/issues/113)) ([d16c0c2](https://github.com/nogamsung/assetlog/commit/d16c0c22280d06b3603998c571f3a0a33fe3a8a9))

## [0.11.0](https://github.com/nogamsung/assetlog/compare/v0.10.0...v0.11.0) (2026-04-29)


### Features

* add market indices strip on dashboard ([#60](https://github.com/nogamsung/assetlog/issues/60)) ([bfe8e09](https://github.com/nogamsung/assetlog/commit/bfe8e095d28a29bcf5fca19130facfcbb07abe18))


### Chores

* add docker deploy scripts for backend/frontend ([#59](https://github.com/nogamsung/assetlog/issues/59)) ([111fa23](https://github.com/nogamsung/assetlog/commit/111fa231870d007eb0b76706d54bd88debf566f6))

## [0.10.0](https://github.com/nogamsung/assetlog/compare/v0.9.0...v0.10.0) (2026-04-28)


### Features

* bulk transactions (multi-symbol CSV + manual grid) ([#47](https://github.com/nogamsung/assetlog/issues/47)) ([825f0eb](https://github.com/nogamsung/assetlog/commit/825f0ebf08ed9d4c268afd4241d20249246eca06))
* cash holdings (multi-currency balance + portfolio integration) ([#50](https://github.com/nogamsung/assetlog/issues/50)) ([d5ab6d7](https://github.com/nogamsung/assetlog/commit/d5ab6d70b0f2abc6399c23f0149780f79fb0440a))
* **frontend:** Toss-style UI/UX + 모바일 최적화 + 숫자 포맷 정리 ([#51](https://github.com/nogamsung/assetlog/issues/51)) ([996a5e4](https://github.com/nogamsung/assetlog/commit/996a5e4113f26106bc012a13e73a521e380fdaa8))


### Bug Fixes

* **frontend:** asset 삭제 시 UI 즉시 반영 (portfolio holdings 캐시 invalidation) ([#49](https://github.com/nogamsung/assetlog/issues/49)) ([37592c1](https://github.com/nogamsung/assetlog/commit/37592c16472f5eac038a0d67b1564b05709b2d17))


### Refactor

* drop users table for single-owner mode ([#44](https://github.com/nogamsung/assetlog/issues/44)) ([cb20296](https://github.com/nogamsung/assetlog/commit/cb20296b2c433fdbdb47e22de50958761212dc4b))
* **frontend:** move bulk-import entry from asset detail to /assets ([#48](https://github.com/nogamsung/assetlog/issues/48)) ([94fdc16](https://github.com/nogamsung/assetlog/commit/94fdc16860af603bd5f4f5becadb906820df0b0d))


### Chores

* add release-please + GHCR Docker publish pipeline ([#53](https://github.com/nogamsung/assetlog/issues/53)) ([031abeb](https://github.com/nogamsung/assetlog/commit/031abebfda4d21dce96f1b7a0855b1914e74f765))
* **frontend:** a11y + NaN guard + Pretendard self-host ([#52](https://github.com/nogamsung/assetlog/issues/52)) ([e36c526](https://github.com/nogamsung/assetlog/commit/e36c526276b3d8d820069c13d432210a19104198))
