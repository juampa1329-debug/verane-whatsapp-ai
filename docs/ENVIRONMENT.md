# ENVIRONMENT

Scope: SaaS only.

## Backend Settings

Source: `saas-version/backend/app_saas/config.py`.

Core env vars:

- `DATABASE_URL`
- `SAAS_ENV`
- `SAAS_JWT_SECRET`
- `SAAS_JWT_ISSUER`
- `SAAS_ACCESS_TOKEN_MINUTES`
- `SAAS_REFRESH_TOKEN_DAYS`
- `SAAS_SECRET_KEY`
- `SAAS_CORS_ORIGINS`
- `SAAS_TRIAL_DAYS`
- `SAAS_TRIAL_PLAN_CODE`

Worker env vars:

- `SAAS_EMBEDDED_WORKER_ENABLED`
- `SAAS_WORKER_IDLE_SEC`
- `SAAS_WORKER_BATCH_SIZE`
- `SAAS_WORKER_NAME`
- `SAAS_META_TOKEN_REFRESH_INTERVAL_SEC`
- `SAAS_META_TOKEN_REFRESH_DAYS_BEFORE_EXPIRY`
- `SAAS_INTELLIGENCE_WORKER_INTERVAL_MINUTES`
- `SAAS_INTELLIGENCE_EVENT_LIMIT`
- `SAAS_INTELLIGENCE_LOOKBACK_HOURS`
- `SAAS_INTELLIGENCE_PREDICTION_COOLDOWN_MINUTES`
- `SAAS_AUTONOMOUS_OPS_ANALYSIS_LIMIT`

Database pool env vars:

- `SAAS_DB_POOL_SIZE`
- `SAAS_DB_MAX_OVERFLOW`
- `SAAS_DB_POOL_TIMEOUT_SEC`
- `SAAS_DB_POOL_RECYCLE_SEC`

Production note: these values are consumed by `app_saas/db.py` when creating the SQLAlchemy engine. They exist to avoid default `QueuePool` exhaustion under browser polling and worker load. Tune them with PostgreSQL `max_connections`, not in isolation.

Optional ML env vars:

- `SAAS_ML_ENABLED`
- `SAAS_ML_SHADOW_INFERENCE_ENABLED`
- `SAAS_ML_AUTO_TRAIN_ENABLED`
- `SAAS_ML_SERVICE_URL`
- `SAAS_ML_INFERENCE_TIMEOUT_SEC`
- `SAAS_MLFLOW_TRACKING_URI`
- `MLFLOW_TRACKING_URI`
- `SAAS_ML_MODEL_DIR`
- `BENTOML_HOME`
- `SAAS_QDRANT_URL`

Security/captcha/rate limit:

- `SAAS_CAPTCHA_ENABLED`
- `SAAS_CAPTCHA_PROVIDER`
- `TURNSTILE_SECRET_KEY`
- `SAAS_RATE_LIMIT_ENABLED`
- `SAAS_LOGIN_LOCK_FAILED_ATTEMPTS`
- `SAAS_LOGIN_LOCK_MINUTES`
- `SAAS_PASSWORD_RESET_MINUTES`
- `SAAS_PASSWORD_RESET_PATH`
- `SAAS_MFA_OTP_MINUTES`
- `SAAS_MFA_OTP_LENGTH`
- `SAAS_MFA_MAX_ATTEMPTS`
- `SAAS_MFA_REQUIRED_ROLES`
- `SAAS_ADMIN_MFA_REQUIRED_ROLES`
- `SAAS_SECURITY_NOTIFY_ENABLED`

Password recovery email:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_STARTTLS`

Transactional email scope:

- The same SMTP channel is used by password recovery, email OTP MFA and security notices today.
- The same SMTP channel also supports welcome emails, role/access alerts, and optional email copies for internal Admin notifications.
- Email templates are rendered by `app_saas.shared.email` in Spanish with Scentra branding from `https://scentra-ai.online/favicon.png` and `https://scentra-ai.online/scentra-logo.png`.
- Internal notification delivery reuses these SMTP settings for optional email copies, but SMTP delivery is not required for in-app notification persistence.

Phase 13 MFA/security notices:

- Email OTP MFA uses the same SMTP settings as password recovery.
- In local mode, OTP/reset flows can expose dev tokens for smoke testing. Production must configure SMTP instead.
- `SAAS_MFA_REQUIRED_ROLES` and `SAAS_ADMIN_MFA_REQUIRED_ROLES` are comma-separated role lists. Empty means only users with 2FA enabled are challenged.
- `SAAS_SECURITY_NOTIFY_ENABLED=true` enables security notification emails for supported account/security changes.

Public URLs:

- `SAAS_PUBLIC_API_BASE`
- `SAAS_PUBLIC_APP_BASE`

Meta/Instagram:

- `META_APP_ID`
- `META_APP_SECRET`
- `META_GRAPH_VERSION`
- `META_REDIRECT_URI`
- `META_WEBHOOK_VERIFY_TOKEN`
- `INSTAGRAM_APP_ID`
- `INSTAGRAM_APP_SECRET`
- `INSTAGRAM_REDIRECT_URI`
- `INSTAGRAM_WEBHOOK_VERIFY_TOKEN`

Billing:

- `SAAS_BILLING_PROVIDER`
- `SAAS_BILLING_SUCCESS_URL`
- `SAAS_BILLING_CANCEL_URL`
- `SAAS_BILLING_LIFECYCLE_INTERVAL_MINUTES`
- `BILLING_PAST_DUE_GRACE_DAYS`
- Stripe, MercadoPago, and Wompi provider vars are present in config/compose.
- Production provider webhooks require provider-specific secrets: `STRIPE_WEBHOOK_SECRET`, `MERCADOPAGO_WEBHOOK_SECRET`, and `WOMPI_EVENTS_KEY`.

Billing provider setup for production:

- Runtime checkout endpoint: tenant users call `POST /saas/v1/billing/checkout`.
- Provider webhook endpoints:
  - Wompi: `https://api.scentra-ai.online/saas/v1/billing/webhooks/wompi`
  - MercadoPago: `https://api.scentra-ai.online/saas/v1/billing/webhooks/mercadopago`
  - Stripe: `https://api.scentra-ai.online/saas/v1/billing/webhooks/stripe`
- Default provider selector:
  - `BILLING_DEFAULT_PROVIDER=wompi` uses Wompi when checkout payload says `provider=auto`.
  - Valid values in code: `manual`, `stripe`, `mercadopago`, `wompi`.
- Common billing URLs:
  - `BILLING_SUCCESS_URL=https://app.scentra-ai.online/?billing=success`
  - `BILLING_CANCEL_URL=https://app.scentra-ai.online/?billing=cancelled`
- Wompi variables required by current code:
  - `WOMPI_ENVIRONMENT=production` or `sandbox`.
  - `WOMPI_PUBLIC_KEY`: public checkout key.
  - `WOMPI_PRIVATE_KEY`: private API key used to fetch transaction details when needed.
  - `WOMPI_INTEGRITY_KEY`: integrity secret used to sign Web Checkout links.
  - `WOMPI_EVENTS_KEY`: event/signature secret used to verify Wompi webhooks.
  - Current Wompi checkout path only accepts plan currency `COP`; plans charged by Wompi must have `currency='COP'`.
- MercadoPago variables required by current code:
  - `MERCADOPAGO_ACCESS_TOKEN`: production or sandbox access token used to create preferences and fetch payments.
  - `MERCADOPAGO_WEBHOOK_SECRET`: webhook signature secret used to verify `x-signature`.
  - Current code does not use MercadoPago public key in backend checkout.
- Stripe variables required by current code:
  - `STRIPE_SECRET_KEY`
  - `STRIPE_WEBHOOK_SECRET`
- Provider behavior:
  - Wompi creates a Web Checkout URL with `public-key`, `amount-in-cents`, `currency`, `reference`, `signature:integrity`, `redirect-url`, and owner email/name when available.
  - MercadoPago creates a checkout preference and stores its `init_point` or `sandbox_init_point`.
  - Approved provider webhooks activate the tenant subscription, update tenant plan/status, create a paid invoice and payment row.
  - Failed/rejected provider webhooks mark the checkout/subscription as failed or past due and can notify the tenant owner by email when SMTP is configured.

## Frontend Env

Client app:

- `VITE_API_BASE`
- `VITE_CAPTCHA_ENABLED`
- `VITE_TURNSTILE_SITE_KEY`
- `VITE_APP_LOCALE` optional; defaults to `es-CO` in the Phase 14 text catalog.

Admin app:

- `VITE_API_BASE`
- `VITE_CLIENT_APP_BASE`
- `VITE_CAPTCHA_ENABLED`
- `VITE_TURNSTILE_SITE_KEY`
- `VITE_ADMIN_BOOTSTRAP_ENABLED`
- `VITE_ADMIN_LOCALE` optional; defaults to `es-CO` in the Phase 14 text catalog.

Docker Compose build vars for admin app:

- `ADMIN_VITE_API_BASE`
- `ADMIN_VITE_CLIENT_APP_BASE`
- `ADMIN_VITE_CAPTCHA_ENABLED`
- `ADMIN_VITE_TURNSTILE_SITE_KEY`
- `ADMIN_VITE_BOOTSTRAP_ENABLED`
- `SAAS_ADMIN_HOST_PORT`

Optional platform admin seed vars:

- `SAAS_ADMIN_EMAIL`
- `SAAS_ADMIN_PASSWORD`
- `SAAS_ADMIN_FULL_NAME`
- `SAAS_ADMIN_ROLE`
- `SAAS_ADMIN_NOTES`

## Docker Compose

File: `saas-version/docker-compose.saas.yml`.

Services:

- `scentra-saas-db`: Postgres 16
- `api`: migrations then Uvicorn
- `worker`: standalone background worker
- `admin-frontend`: Nginx-served React admin app for `admin.scentra-ai.online`
- `platform-admin-seed`: optional `admin-seed` profile service for secure first superadmin creation
- `mlflow`: optional `ml` profile service for experiment/model tracking
- `ml-service`: optional `ml` profile FastAPI/BentoML image for synthetic/autolabel training, dataset building, inference, drift and metrics
- `qdrant`: optional `ml` profile vector infrastructure for future use

Network:

- external network `coolify`

Important compose defaults:

- `SAAS_JWT_SECRET` defaults to `change-me-local-saas-secret`; never use this in production.
- `SAAS_CORS_ORIGINS` includes local and production Scentra domains.
- API/worker services pass through Phase 1 security env vars for CAPTCHA, rate limits, lockout, reset expiry/path, and SMTP.
- The Compose API service defaults `SAAS_EMBEDDED_WORKER_ENABLED=false` because a standalone `worker` service already exists. Enable the embedded worker only for single-container deployments.
- The default worker idle interval is now `10` seconds and default batch size is `10` to reduce DB pressure in small VPS deployments.
- API DB pool defaults are `SAAS_DB_POOL_SIZE=10`, `SAAS_DB_MAX_OVERFLOW=20`, `SAAS_DB_POOL_TIMEOUT_SEC=20`, and `SAAS_DB_POOL_RECYCLE_SEC=1800`.
- Worker DB pool defaults are smaller: `SAAS_DB_POOL_SIZE=5`, `SAAS_DB_MAX_OVERFLOW=10`, `SAAS_DB_POOL_TIMEOUT_SEC=20`, and `SAAS_DB_POOL_RECYCLE_SEC=1800`.
- `api` command applies migrations from `/app/migrations`, runs `app_saas.tools.schema_check /app/migrations`, and starts Uvicorn only if the schema readiness contract passes.
- API Docker healthcheck calls `/saas/v1/ready`, not `/health`, so Coolify/Traefik should not route traffic to a container whose database schema is incomplete.
- `admin-frontend` defaults to production API/client URLs unless `ADMIN_VITE_*` build vars override them.
- `platform-admin-seed` is not part of default `up`; run it explicitly with the `admin-seed` profile.
- ML services are not part of default `up`; run them explicitly with the `ml` profile. API/worker defaults keep `SAAS_ML_ENABLED=false`.
- Optional local ML ports: `SAAS_MLFLOW_HOST_PORT` default `5000`, `SAAS_ML_HOST_PORT` default `8090`, `SAAS_QDRANT_HOST_PORT` default `6333`.
- `ml-service` depends on DB and MLflow; it can log training jobs/artifacts/inference/drift plus datasets/evaluations to Postgres when migrations `049` and `050` exist.
- Local validation on non-default admin ports must include that origin in `SAAS_CORS_ORIGINS`; default compose includes local admin port `8011`.
- Avoid running multiple SaaS Compose projects on the same external `coolify` network at once unless aliases are isolated; duplicate `scentra-saas-db` aliases can make API containers reach the wrong DB.
- Zero-downtime production deployments should run migrations/schema checks before switching traffic, or use rolling/blue-green behavior. A failed schema check intentionally prevents a new API container from becoming ready.
- Dockerfile-only deployments must still build from the SaaS source. If Coolify imports `juampa1329-debug/Scentra-AI` directly, the SaaS is already at repo root: use base directory `/` and Dockerfile `/backend/Dockerfile`. If Coolify imports the monorepo `juampa1329-debug/verane-whatsapp-ai`, use base directory `/saas-version` and Dockerfile `/backend/Dockerfile`.
- Do not mix those modes. `lstat .../saas-version/backend: no such file or directory` means Coolify is using the direct `Scentra-AI` repo and the base directory must be `/`.
- `saas-version/backend/Dockerfile` now runs the same startup gate as Compose by default: `migrate -> schema_check -> uvicorn`. Do not paste that command into the VPS host shell; it must run inside the container/Coolify app where Python and `app_saas` exist.
- Admin Dockerfile-only deployments should use the admin frontend as build context: base directory `/admin-frontend`, Dockerfile `/Dockerfile`, exposed port `80`. The admin context excludes `node_modules`, `dist`, and `.env`; otherwise local Windows dependencies can overwrite container-installed Linux dependencies and produce `vite: Permission denied`.

Voice Intelligence runtime:

- No new environment variable is required for Phase 24.2.
- Real audio analysis requires an encrypted tenant Google/Gemini credential configured through SaaS API credentials, with an audio-capable selected model such as a Gemini Flash family model.
- If no valid tenant provider credential/model is available, the endpoint fails safely instead of falling back to a non-audio provider.

Vision Intelligence runtime:

- No new environment variable is required for Phase 24.3.
- Real image/document analysis requires encrypted tenant AI credentials configured through SaaS API credentials.
- Google/Gemini is the default/safest provider path and the current document/OCR route.
- OpenRouter and Kimi can be selected for image analysis when the tenant credential and selected model support vision; the endpoint fails safely if the provider/model cannot process the media.

Web/Image Search Intelligence runtime:

- No new environment variable is required for Phase 24.4.
- Real search requires an encrypted tenant API credential configured through SaaS API credentials for one of:
  - `tavily` with `TAVILY_API_KEY`.
  - `brave_search` with `BRAVE_SEARCH_API_KEY`.
  - `serpapi` with `SERPAPI_API_KEY`.
- If no valid tenant search credential is configured, `/saas/v1/media/search` fails safely with a controlled client error instead of falling back to a global key.
- External result URLs are screened for public HTTP(S) targets before persistence/approval; private/internal URLs are blocked.

Agent Multimodal Tools runtime:

- No new environment variable is required for Phase 24.5.
- Full commercial use is controlled by plan/tenant Intelligence flags: `agent_multimodal_tools`, `agent_voice_tools`, `agent_vision_tools`, `agent_external_search_tools`, or umbrella `ai_premium`; demo mode can preview through existing demo gates.
- Voice/vision agent tools still require the same tenant AI credentials and media availability as Phase 24.2/24.3.
- Web/image search agent tools still require tenant Tavily/Brave/SerpAPI credentials and human approval of each result before the runtime agent can use an external source as context.
- Missing credentials or invalid media fail safely and leave an auditable failed tool run; no global provider secret fallback is used.

Multimodal Memory runtime:

- No new environment variable is required for Phase 24.6.
- Full commercial use is controlled by plan/tenant Intelligence flags: `multimodal_memory_events`, `multimodal_training_events`, `multimodal_rag_materialization`, `multimodal_agent_memory`, or umbrella `ai_premium`.
- Training-ready event capture is separate from memory capture; enabling memory does not automatically authorize training usage.
- RAG/collective-memory materialization uses existing Knowledge and agent memory tables; customer content requires explicit operator approval.

## Secret Handling

- Tenant/provider credentials use encrypted storage via `shared/secrets.py`.
- Encryption key is derived from `SAAS_SECRET_KEY` or `SAAS_JWT_SECRET`.
- `SAAS_SECRET_KEY` must be stable across redeploys. Do not replace it with a Meta token or a newly generated value after tenants have saved provider credentials; existing encrypted AI/TTS/search keys will become unreadable and the AI Gateway will behave as if credentials are missing.
- `saas-version/keys/saasprivate.key` exists in the tree; treat as sensitive until ownership/purpose is verified.

## Billing Provider Runtime

- Wompi and Mercado Pago can now be configured from SaaS Admin > Facturacion > Pasarelas de pago.
- Admin-stored credentials are encrypted in PostgreSQL and split by mode: prueba and produccion.
- Coolify/env vars remain fallback only: `BILLING_DEFAULT_PROVIDER`, `MERCADOPAGO_ACCESS_TOKEN`, `MERCADOPAGO_WEBHOOK_SECRET`, `WOMPI_ENVIRONMENT`, `WOMPI_PUBLIC_KEY`, `WOMPI_PRIVATE_KEY`, `WOMPI_INTEGRITY_KEY`, `WOMPI_EVENTS_KEY`.
- If a provider has no DB row, runtime preserves the env-based behavior.
- If Admin saves a provider row and disables it, checkout for that provider is blocked even if env fallback exists.
- The Admin UI exposes each provider webhook URL; external provider dashboards must still be configured to call `/saas/v1/billing/webhooks/{provider}`.
