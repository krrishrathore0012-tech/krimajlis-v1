# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Contains the KRIMAJLIS global market intelligence platform — a Python Flask backend with a professional dark terminal UI.

## Applications

### KRIMAJLIS (artifacts/krimajlis)
- **Type**: Python Flask backend + Single HTML/CSS/JS frontend
- **URL**: `/` (root)
- **Port**: 9000
- **Served via**: `artifacts/krimajlis-web` artifact registration
- **Frontend**: `artifacts/krimajlis/templates/index.html` — complete terminal UI with Space Mono font
- **Engine**: `artifacts/krimajlis/krimajlis_engine.py` — KrimajlisEngine class with 25 causal relationships
- **Main**: `artifacts/krimajlis/app.py` — Flask routes + 3 background threads

### API Server (artifacts/api-server)
- **Type**: Express TypeScript API
- **URL**: `/api/*`
- **Port**: 8080

### Canvas/Mockup Sandbox (artifacts/mockup-sandbox)
- **Type**: React Vite design sandbox
- **URL**: `/__mockup`

## KRIMAJLIS Architecture

### Backend Threads (app.py)
- Thread 1: Refreshes primary nodes from yfinance every 30s
- Thread 2: Regenerates alpha feed every 15s
- Thread 3: Drifts regime state every 60s

### API Endpoints
- `GET /` — Main terminal UI
- `GET /health` — Health check
- `GET /api/regime` — 6-dimension macro regime state
- `GET /api/primary-nodes` — 12 primary market nodes with z-scores
- `GET /api/alpha-feed` — 15-25 ranked alpha signals (refreshes 15s)
- `GET /api/causal-chain/<signal_id>` — Full causal chain for signal
- `GET /api/layers` — 5 intelligence layer metrics
- `GET /api/ticker-tape` — Live ticker prices via yfinance
- `POST /api/bridge/veritas` — VERITAS integration stub
- `POST /api/bridge/garuda` — GARUDA integration stub

### Intelligence Engine (krimajlis_engine.py)
- 25 hardcoded causal relationships across 5 loophole types
- Rolling 20-period window for z-score calculation
- Conviction = z_score × historical_accuracy × regime_alignment_multiplier
- Freshness: FRESH (<30s), ACTIVE (<120s), DECAYING (older)

## Stack (TypeScript packages)
- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
