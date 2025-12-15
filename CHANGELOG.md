# Changelog

## [Unreleased]

### Added

- Modular broker architecture with `BaseBrokerAuth`, `BaseBrokerAccount`, and `BaseBrokerData` abstract base classes.
- Refactored Fyers broker implementation into `app/core/brokers/fyers` (Auth, Account, Data).
- Refactored Upstox broker implementation into `app/core/brokers/upstox` (Auth, Account, Data).
- Added `get_funds` method to `BaseBrokerAccount` and implemented it for Fyers and Upstox.
- Verification tests for Fyers and Upstox structure.

### Changed

- Updated `place_order_service.py`, `funds_service.py`, and `split_order_service.py` to support new modular broker structure while maintaining backward compatibility for legacy brokers.
- Migrated Fyers and Upstox authentication, order placement, and market data retrieval logic to the new architecture.
