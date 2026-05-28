# DEPENDENCIES

Scope: SaaS only.

## Backend

File: `saas-version/backend/requirements.txt`.

Pinned packages detected:

- `fastapi==0.115.0`
- `uvicorn[standard]==0.30.6`
- `SQLAlchemy==2.0.34`
- `psycopg2-binary==2.9.9`
- `pydantic==2.8.2`
- `pydantic-settings==2.4.0`
- `PyJWT==2.9.0`
- `argon2-cffi==23.1.0`
- `python-multipart==0.0.12`
- `cryptography==42.0.8`
- `imageio-ffmpeg==0.5.1`
- `pypdf==4.3.1`

Docker base:

- Python 3.11
- ffmpeg installed in backend image

Optional ML image:

- Files: `saas-version/backend/requirements-ml.txt`, `saas-version/backend/Dockerfile.ml`.
- The default API/worker image still uses `requirements.txt`; heavy ML dependencies are isolated to Compose profile `ml`.
- ML package set includes MLflow, BentoML, XGBoost, LightGBM, scikit-learn, pandas/numpy, joblib and Prometheus client.
- Auto-label dataset building and autolabel training run only in the optional ML service image; the default API/worker image still does not import these heavy ML packages.
- `requirements-ml.txt` includes `-r requirements.txt`, so the ML service can reuse FastAPI/config/DB helpers.

## Frontend

Files:

- `saas-version/frontend/package.json`
- `saas-version/admin-frontend/package.json`

Detected package set in both:

- `react`: `^19.2.0`
- `react-dom`: `^19.2.0`
- `vite`: `^7.2.5`
- `@vitejs/plugin-react`: `latest` / `5.1.1` lockfile-resolved behavior must be checked before package changes.

Phase 14 Product Ops:

- No new frontend dependency was added for localization.
- Tenant/Admin locale catalogs use small local ES modules: `frontend/src/i18n.js` and `admin-frontend/src/i18n.js`.
- Product Ops checks use Node built-ins only: `saas-version/scripts/phase14-copy-audit.mjs` and `phase14-release-check.mjs`.

Phase 24.2 Voice Intelligence:

- No backend, frontend, Docker or ML dependency was added.
- Audio analysis reuses existing AI Gateway attachment support, existing HTTP provider helpers, existing Meta media helpers and existing frontend APIs.

Phase 24.3 Vision Intelligence:

- No backend, frontend, Docker or ML dependency was added.
- Image/document analysis reuses existing AI Gateway attachment support, existing HTTP provider helpers, existing Meta media helpers and existing frontend APIs.

Phase 24.4 Web/Image Search Intelligence:

- No backend, frontend, Docker, broker, search SDK or ML dependency was added.
- Provider calls use the existing stdlib/HTTP helper pattern and encrypted tenant API credentials.
- Tavily, Brave Search API and SerpAPI are integrated through direct HTTPS API calls, not installed SDKs.

Phase 24.5 Agent Multimodal Tools:

- No backend, frontend, Docker, broker, agent-framework, browser-search SDK or ML dependency was added.
- Agent tools reuse the existing Agent OS tool-run table, media router endpoints, AI Gateway attachment support and direct HTTPS search provider helpers.
- No LangGraph/CrewAI/AutoGen or separate multimodal runtime package was introduced in this phase.

Phase 24.6 Multimodal Memory & Training Events:

- No backend, frontend, Docker, broker, vector DB or ML dependency was added.
- Memory capture reuses existing PostgreSQL tables, Intelligence feature/usage gates, Knowledge/RAG helpers, collective agent memory helpers and Agent OS/media/search records.
- No training framework is invoked automatically; training-ready rows are stored only as signals for later ML pipelines.

Docker base:

- Node 20 build stage
- Nginx runtime stage

## Dependency Rules

- Do not update or install dependencies unless the user explicitly asks.
- Prefer existing packages and patterns.
- Phase 11 ML infrastructure now includes optional ML libraries, MLflow and BentoML only in `requirements-ml.txt`/`Dockerfile.ml`. Do not add them to the default API/worker image without explicit approval.
- Kafka/NATS and other event brokers were not added.
- If dependency files change, update this doc and `ai-memory/CURRENT_STATE.md`.
- Before dependency work, inspect both `package.json` and lockfiles.
- Do not commit `node_modules` or generated dependency folders unless user explicitly wants that state; note that SaaS currently has dependency/build artifacts in the working tree.
