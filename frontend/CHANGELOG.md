# Changelog

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
