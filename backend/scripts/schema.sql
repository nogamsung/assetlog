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
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `transactions` (
  `id`             INT             NOT NULL AUTO_INCREMENT,
  `user_asset_id`  INT             NOT NULL,
  `type`           VARCHAR(16)     NOT NULL COMMENT 'buy | sell',
  `quantity`       DECIMAL(28, 10) NOT NULL,
  `price`          DECIMAL(20, 6)  NOT NULL,
  `traded_at`      DATETIME        NOT NULL,
  `memo`           VARCHAR(255)    NULL,
  `tag`            VARCHAR(50)     NULL,
  `created_at`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_transactions_user_asset_id`        (`user_asset_id`),
  KEY `ix_transactions_user_asset_traded_at` (`user_asset_id`, `traded_at`),
  KEY `ix_transactions_tag`                  (`tag`),
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

SET FOREIGN_KEY_CHECKS = 1;
