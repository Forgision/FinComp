# Repetitive Task Workflows

## General Workflow
- **Error Handling:** If a to-do item results in an error, the next attempt should involve splitting it into smaller, more manageable to-do items. This improves resilience and makes debugging easier.

## Review Production Deployment Scripts

**Last performed:** 2025-10-05
**Trigger:** After any significant feature implementation or dependency change.

**Description:**
This task ensures that the production deployment scripts (`start.sh` and `docker-compose.yaml`) are kept up-to-date with the latest application requirements, including new services, dependencies, build steps, and configuration changes.

**Files to Review/Modify:**
- `start.sh` - For production deployments with Gunicorn and Uvicorn workers.
- `docker-compose.yaml` - For simple Docker deployments.
- `architecture.md` - As the source of truth for deployment requirements.
- `.env` / `.sample.env` - To ensure new environment variables are included.

**Steps:**
1.  **Analyze Changes:** Review the latest feature implementation or changes to identify any impact on the deployment process.
2.  **Check for New Services:** Determine if new background services (like the WebSocket proxy) have been added and need to be managed by `systemd` or Docker.
3.  **Verify Dependencies:** Ensure any new Python (`pyproject.toml`) or frontend (`package.json`) dependencies are installed by the scripts.
4.  **Update Build Process:** If the frontend or any other part of the application requires a build step, ensure it's included.
5.  **Database Migrations:** Confirm that database initialization and migration commands (e.g., `alembic upgrade head`) are correctly executed.
6.  **Configuration:** Check if new environment variables are required and update the `.env` setup process accordingly.
7.  **Permissions and Ownership:** Verify that file and directory permissions are correctly set for any new paths.
8.  **Test the Script:** (If possible in a staging environment) Perform a dry run or a full installation to validate the changes.

**Important Notes:**
- Always run installation commands as the `appuser` user where appropriate to avoid permission issues.
- Ensure scripts are idempotent, meaning they can be run multiple times without causing errors.
- Update the `Last performed` date in this document after each review.