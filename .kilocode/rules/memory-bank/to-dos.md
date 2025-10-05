# To-Do List

This list captures ongoing tasks, planned enhancements, and maintenance activities for the OpenAlgo platform, based on the initial review of the design documentation.

## High Priority
- [ ] **Review Production Deployment Scripts:** Verify that the `install.sh` and `ubuntu-ip.sh` scripts are up-to-date with the latest dependencies and security best practices outlined in `12_deployment_architecture.md`.
- [ ] **Implement Health Check Endpoint:** Develop the `/health` endpoint as designed in `12_deployment_architecture.md` to monitor database connectivity and broker connections.
- [ ] **Configure Prometheus Exporter:** Integrate the `prometheus_flask_exporter` to expose key application metrics (e.g., orders placed, active strategies) for monitoring.

## Medium Priority
- [ ] **Develop Sandbox MTM Updates:** Implement the "Enhanced MTM" feature for the Sandbox Mode to auto-update P&L every 5 seconds, as planned in `14_sandbox_architecture.md`.
- [ ] **Implement Telegram Real-time Alerts:** Begin development of the real-time price, order, and P&L alerts for the Telegram bot, as outlined in `13_telegram_bot_integration.md`.
- [ ] **Enhance API Security:** Begin implementation of OAuth2/SAML integration for enterprise SSO support as planned in `06_authentication_platform.md`.

## Low Priority
- [ ] **Investigate Smart Order Routing:** Research and design the "Smart Order Routing" feature to automatically select the best broker for a trade, as mentioned in `03_broker_integration.md`.
- [ ] **Design Strategy Marketplace:** Create a detailed design document for the "Strategy Marketplace" feature, including version control and template library, as planned in `11_python_strategy_hosting.md`.
- [ ] **Explore Time-series Database:** Evaluate time-series databases (e.g., InfluxDB, TimescaleDB) for storing tick data, a future enhancement noted in `04_database_layer.md`.