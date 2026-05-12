# Changelog

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
