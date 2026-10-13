# Deploy LEGACY

Names only. Do not put secret values, connection strings, or API keys in this file or in git.

The public game is the Cloudflare Pages site. The API is the Railway service `legacy-api`. Both track `main` on `https://github.com/Joshuadamon/legacy`.

## Where it lives

| | |
| --- | --- |
| Web | https://legacy.thelittlebrownphamily.com and https://legacy-abm.pages.dev |
| API | https://legacy-api-production-8754.up.railway.app |
| Health | `GET /api/health` |

Pages project name: `legacy`. Direct upload, not a Git-connected build. The Cloudflare account is the one that owns `thelittlebrownphamily.com` (`5c0cb491a8fa18904a09d6f0d9114497`).

Railway project: `legacy`. Environment: `production`. API service: `legacy-api`. A `legacy-web` service also exists on that project; the custom domain is the Pages project, not that service.

## Web (Cloudflare Pages)

From `frontend/`:

- Build command: `npx expo export --platform web`
- Output directory: `dist`
- `frontend/public/_redirects` is copied into `dist` so client routes fall back to `index.html`.

`EXPO_PUBLIC_BACKEND_URL` is inlined at build time. `frontend/.env` overrides the shell. For a production export, set that name in `frontend/.env` to the public API origin with no `/api` suffix, run the export with `--clear`, then restore the local value (`http://localhost:8001`). Do not commit `.env`.

Deploy the export:

```
npx wrangler pages deploy dist --project-name legacy --commit-dirty=true
```

Set `CLOUDFLARE_ACCOUNT_ID` to the account above when Wrangler can see more than one account.

Required at build time:

- `EXPO_PUBLIC_BACKEND_URL`

Optional, read by the native purchase path, not by the static site's coin checkout:

- `EXPO_PUBLIC_REVENUECAT_APPLE_KEY`
- `EXPO_PUBLIC_REVENUECAT_GOOGLE_KEY`

Do not put `STRIPE_SECRET_KEY` or `STRIPE_WEBHOOK_SECRET` on Pages.

Local check, leaving ports 3000 and 3010 alone:

```
npx expo export --platform web
npx serve dist -p 3011
```

## API (Railway)

From `backend/`, against the project that already exists. Do not create a second Railway project.

```
railway link -p 8988fe8f-6b01-4f28-8449-adbcba7fe5bb -e production -s legacy-api
railway up
```

Start file: `backend/main.py`. Railpack runs `uvicorn main:app`, and `main.py` re-exports the FastAPI app from `server.py`. `backend/railway.toml` records `startCommand = python server.py`. Leave `main.py` in place.

`server.py` listens on `0.0.0.0` and `PORT` when started directly.

Required on `legacy-api`:

- `MONGO_URL`
- `DB_NAME` (default `legacy` when unset)

Railway injects `PORT`.

Optional. Unset means the code default:

- `ANTHROPIC_API_KEY` — server only. Never prefix it with `EXPO_PUBLIC_`. Unset uses the fallback event deck.
- `MODEL_PROVIDER` — default `anthropic`
- `MODEL_NAME` — if unset, `ANTHROPIC_MODEL`, then `claude-sonnet-5`
- `ANTHROPIC_MODEL`
- `LEGACY_SEASON_LIMIT` — seasons per user per hour, default `60`
- `LEGACY_STARTING_MARKS` — leave unset so a new profile starts at 250 marks
- `STRIPE_SECRET_KEY` — test mode only (`sk_test_` or `rk_test_`). A live key is refused.
- `STRIPE_WEBHOOK_SECRET` — signing secret for `POST /api/store/stripe-webhook`
- `LEGACY_TEST_PURCHASES` — default `1` accepts the local test receipt. Set to `0` to refuse that stub. Web coins are granted only by the Stripe webhook.

Stripe webhook events: `checkout.session.completed` and `checkout.session.async_payment_succeeded`.
