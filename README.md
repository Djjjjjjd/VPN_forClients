# VPN_forClients

Monorepo for a Telegram-first VPN platform powered by WireGuard, FastAPI, PostgreSQL, YooKassa, and SSH-managed VPN nodes.

## Repository layout

- `apps/backend` - FastAPI application for Telegram/YooKassa webhooks and internal APIs
- `apps/bot` - aiogram bot package and local polling runner for development
- `packages/domain` - pure business logic and orchestration rules
- `packages/db` - SQLAlchemy models, repositories, session management, Alembic scaffolding
- `packages/vpn` - SSH client for WireGuard node automation
- `scripts` - WireGuard node scripts and local operational commands
- `infra` - systemd and Nginx templates
- `docs` - setup and operational notes
- `tests` - unit tests for core domain flows

## Quick start

1. Copy `.env.example` to `.env`.
2. Fill Telegram, YooKassa, database, and SSH settings.
3. Install the project dependencies.
4. Run Alembic migrations.
5. Start the FastAPI backend behind Nginx.
6. Configure Telegram webhook and YooKassa webhook to point to the backend.

## Application responsibilities

The backend is responsible for:

- receiving Telegram updates through a webhook
- receiving YooKassa payment notifications
- creating or updating users, payments, subscriptions, and VPN clients
- selecting a VPN node
- provisioning and revoking WireGuard peers through SSH scripts
- storing artifact paths for generated client configs and QR codes

The VPN node is responsible for:

- generating client keys and config artifacts
- adding or removing WireGuard peers
- persisting metadata for each generated client
- returning JSON responses for backend orchestration

## Production notes

- Production Telegram delivery uses webhook mode.
- The backend never edits `wg0.conf` directly.
- The WireGuard node is controlled only through the `wg-add-client`, `wg-disable-client`, and `wg-remove-client` scripts.
- PostgreSQL is the single source of truth for users, plans, payments, subscriptions, and VPN allocations.

## Local quality checks

The repository is structured to support:

- `pytest`
- `python -m compileall`
- Alembic migrations

If dependencies are not installed yet, `python -m compileall` is the cheapest sanity check for syntax.
