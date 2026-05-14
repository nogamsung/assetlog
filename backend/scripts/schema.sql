-- ============================================================================
-- assetlog — initial database schema (MySQL 8.0+)
-- ----------------------------------------------------------------------------
-- Single-shot bootstrap for fresh environments. Equivalent to running every
-- Alembic revision under alembic/versions/ in order. After loading this file,
-- stamp Alembic to the latest head so future revisions apply incrementally:
--
--   mysql -u root -p < backend/scripts/schema.sql
--   uv run alembic stamp head
--
-- Connection target (see backend/.env.example):
--   mysql+asyncmy://assetlog:assetlog@localhost:3306/assetlog
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `assetlog`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `assetlog`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------------------------------------------------------
-- asset_symbols — global master row per (asset_type, symbol, exchange)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `asset_symbols` (
  `id`                       INT             NOT NULL AUTO_INCREMENT,
  `asset_type`               VARCHAR(16)     NOT NULL COMMENT 'crypto | kr_stock | us_stock',
  `symbol`                   VARCHAR(50)     NOT NULL,
  `exchange`                 VARCHAR(50)     NOT NULL,
  `name`                     VARCHAR(255)    NOT NULL,
  `currency`                 VARCHAR(10)     NOT NULL,
  `last_price`               DECIMAL(20, 6)  NULL,
  `last_price_refreshed_at`  DATETIME        NULL,
  `last_synced_at`           DATETIME        NULL,
  `created_at`               DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`               DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_asset_type_symbol_exchange` (`asset_type`, `symbol`, `exchange`),
  KEY `ix_asset_symbols_symbol`           (`symbol`),
  KEY `ix_asset_symbols_type_exchange`    (`asset_type`, `exchange`),
  KEY `ix_asset_symbols_last_refreshed`   (`last_price_refreshed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- user_assets — declared holding linking the single owner to an asset_symbol
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_assets` (
  `id`               INT          NOT NULL AUTO_INCREMENT,
  `asset_symbol_id`  INT          NOT NULL,
  `memo`             VARCHAR(255) NULL,
  `created_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_asset_symbol` (`asset_symbol_id`),
  KEY `ix_user_assets_asset_symbol_id` (`asset_symbol_id`),
  CONSTRAINT `fk_user_assets_asset_symbol_id`
    FOREIGN KEY (`asset_symbol_id`) REFERENCES `asset_symbols`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- transactions — individual buy/sell records linked to a user_asset
-- external_source/external_id columns identify rows imported from external
-- venues (Upbit, brokerage APIs, file imports) for idempotent re-sync.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `transactions` (
  `id`              INT             NOT NULL AUTO_INCREMENT,
  `user_asset_id`   INT             NOT NULL,
  `type`            VARCHAR(16)     NOT NULL COMMENT 'buy | sell',
  `quantity`        DECIMAL(28, 10) NOT NULL,
  `price`           DECIMAL(20, 6)  NOT NULL,
  `traded_at`       DATETIME        NOT NULL,
  `memo`            VARCHAR(255)    NULL,
  `tag`             VARCHAR(50)     NULL,
  `external_source` VARCHAR(32)     NULL,
  `external_id`     VARCHAR(64)     NULL,
  `created_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_tx_external_source_id`        (`external_source`, `external_id`),
  KEY `ix_transactions_user_asset_id`          (`user_asset_id`),
  KEY `ix_transactions_user_asset_traded_at`   (`user_asset_id`, `traded_at`),
  KEY `ix_transactions_tag`                    (`tag`),
  CONSTRAINT `fk_transactions_user_asset_id`
    FOREIGN KEY (`user_asset_id`) REFERENCES `user_assets`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- price_points — append-only historical price ticks per asset_symbol
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `price_points` (
  `id`               BIGINT         NOT NULL AUTO_INCREMENT,
  `asset_symbol_id`  INT            NOT NULL,
  `price`            DECIMAL(20, 6) NOT NULL,
  `currency`         VARCHAR(10)    NOT NULL,
  `fetched_at`       DATETIME       NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_price_points_symbol_fetched` (`asset_symbol_id`, `fetched_at`),
  CONSTRAINT `fk_price_points_asset_symbol_id`
    FOREIGN KEY (`asset_symbol_id`) REFERENCES `asset_symbols`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- fx_rates — latest cached rate per (base_currency, quote_currency) pair
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `fx_rates` (
  `id`              INT             NOT NULL AUTO_INCREMENT,
  `base_currency`   VARCHAR(10)     NOT NULL,
  `quote_currency`  VARCHAR(10)     NOT NULL,
  `rate`            DECIMAL(20, 8)  NOT NULL,
  `fetched_at`      DATETIME        NOT NULL,
  `created_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_fx_base_quote` (`base_currency`, `quote_currency`),
  KEY `ix_fx_fetched_at`        (`fetched_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- fx_rate_snapshots — append-only time series of FX rates for historical lookup
-- Used by the price/FX P&L decomposition to value BUYs at trade-date rates.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `fx_rate_snapshots` (
  `id`              INT             NOT NULL AUTO_INCREMENT,
  `base_currency`   VARCHAR(10)     NOT NULL,
  `quote_currency`  VARCHAR(10)     NOT NULL,
  `rate`            DECIMAL(20, 8)  NOT NULL,
  `recorded_at`     DATETIME        NOT NULL,
  `created_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_fx_snap_base_quote_recorded` (`base_currency`, `quote_currency`, `recorded_at`),
  KEY `ix_fx_snap_pair_recorded`              (`base_currency`, `quote_currency`, `recorded_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- login_attempts — audit log for brute-force detection / rate limiting
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `login_attempts` (
  `id`            INT          NOT NULL AUTO_INCREMENT,
  `ip`            VARCHAR(45)  NOT NULL COMMENT 'IPv4 or IPv6',
  `success`       TINYINT(1)   NOT NULL,
  `attempted_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_login_attempts_ip_attempted`        (`ip`, `attempted_at`),
  KEY `ix_login_attempts_attempted`           (`attempted_at`),
  KEY `ix_login_attempts_success_attempted`   (`success`, `attempted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- cash_accounts — single-owner cash balance per (label, currency)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `cash_accounts` (
  `id`                    INT             NOT NULL AUTO_INCREMENT,
  `label`                 VARCHAR(100)    NOT NULL,
  `currency`              VARCHAR(4)      NOT NULL,
  `balance`               DECIMAL(20, 4)  NOT NULL,
  `interest_rate_annual`  DECIMAL(6, 4)   NULL COMMENT 'Annualised interest as fraction (0.0350 = 3.5%)',
  `created_at`            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_cash_accounts_currency` (`currency`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- dividends — cash dividend distributions per asset_symbol
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `dividends` (
  `id`                INT             NOT NULL AUTO_INCREMENT,
  `asset_symbol_id`   INT             NOT NULL,
  `ex_date`           DATE            NOT NULL,
  `amount`            DECIMAL(20, 8)  NOT NULL,
  `currency`          VARCHAR(10)     NOT NULL,
  `source`            VARCHAR(16)     NOT NULL COMMENT 'yfinance | pykrx | manual | toss_securities',
  `external_source`   VARCHAR(32)     NULL,
  `external_id`       VARCHAR(64)     NULL,
  `created_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_dividend_symbol_ex_date` (`asset_symbol_id`, `ex_date`),
  UNIQUE KEY `uq_dividend_external`       (`external_source`, `external_id`),
  KEY `ix_dividend_ex_date`               (`ex_date`),
  CONSTRAINT `fk_dividends_asset_symbol_id`
    FOREIGN KEY (`asset_symbol_id`) REFERENCES `asset_symbols`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- cash_account_transactions — append-only ledger of cash-flow events
-- (interest, deposit, withdraw, ...) imported from broker statements.
-- Dedupe by (external_source, external_id) when populated by file imports.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `cash_account_transactions` (
  `id`                INT             NOT NULL AUTO_INCREMENT,
  `cash_account_id`   INT             NULL,
  `kind`              VARCHAR(32)     NOT NULL COMMENT 'deposit | withdraw | interest | interest_tax | transfer_in | transfer_out',
  `amount`            DECIMAL(20, 8)  NOT NULL,
  `currency`          VARCHAR(8)      NOT NULL,
  `traded_at`         DATETIME(6)     NOT NULL,
  `external_source`   VARCHAR(32)     NULL,
  `external_id`       VARCHAR(64)     NULL,
  `created_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_cash_tx_external`                  (`external_source`, `external_id`),
  KEY `ix_cash_tx_traded_at`                        (`traded_at`),
  KEY `ix_cash_account_transactions_cash_account_id` (`cash_account_id`),
  CONSTRAINT `fk_cash_tx_cash_account_id`
    FOREIGN KEY (`cash_account_id`) REFERENCES `cash_accounts`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- target_allocations — desired weight per asset_type bucket
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `target_allocations` (
  `id`           INT             NOT NULL AUTO_INCREMENT,
  `asset_type`   VARCHAR(32)     NOT NULL COMMENT 'AssetType value or "cash"',
  `target_pct`   DECIMAL(6, 4)   NOT NULL COMMENT 'Fraction 0–1 (0.6000 = 60%)',
  `created_at`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_target_allocation_asset_type` (`asset_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- isin_ticker_cache — persistent ISIN → exchange ticker cache
-- Populated by IsinResolver (static map → DB cache → OpenFIGI). NULL ticker
-- is allowed to remember a negative lookup so we don't re-hit the upstream
-- API for unknown ISINs.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `isin_ticker_cache` (
  `isin`         VARCHAR(12)     NOT NULL,
  `ticker`       VARCHAR(20)     NULL,
  `source`       VARCHAR(16)     NOT NULL DEFAULT 'openfigi',
  `looked_up_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`isin`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- kr_name_cache — Korean security name → KRX 6-digit code cache
-- Populated by KrNameResolver (DB cache → Naver Finance autocomplete). NULL
-- code keeps a negative lookup so the upstream API isn't hit repeatedly.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `kr_name_cache` (
  `name`         VARCHAR(128)    NOT NULL,
  `code`         VARCHAR(6)      NULL,
  `source`       VARCHAR(16)     NOT NULL DEFAULT 'naver',
  `looked_up_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- alembic_version — stamped at latest head so future revisions apply
-- incrementally without re-running the bootstrap.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `alembic_version` (
  `version_num` VARCHAR(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `alembic_version` (`version_num`)
  VALUES ('d7f1c9a3e8b4')
  ON DUPLICATE KEY UPDATE `version_num` = VALUES(`version_num`);

SET FOREIGN_KEY_CHECKS = 1;
