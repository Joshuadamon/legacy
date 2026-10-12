# LEGACY in the browser

The web build is the same game. Cloudflare Pages serves the static Expo export. The FastAPI app stays on its own host and keeps the Stripe secrets.

## Cloudflare Pages

1. In the Cloudflare dashboard, open **Workers & Pages → Create → Pages → Connect to Git**.
2. Choose the GitHub repository `https://github.com/Joshuadamon/legacy`.
3. Production branch: `main`.
4. Root directory: `frontend`.
5. Build command: `npx expo export --platform web`
6. Build output directory: `dist`
7. Add this environment variable to the Pages project (it is inlined at build time):
   - `EXPO_PUBLIC_BACKEND_URL` — the public base URL of the existing API, with no `/api` suffix. Example shape: `https://api.example.com`

Do not add `STRIPE_SECRET_KEY` or `STRIPE_WEBHOOK_SECRET` to Pages. Those stay on the API host only (`backend/.env` locally, or the API process environment). Use Stripe test mode (`sk_test_` or `rk_test_`, and a `whsec_` signing secret). This build refuses live secret keys.

Point a Stripe test-mode webhook at `POST {API}/api/store/stripe-webhook` for `checkout.session.completed` and `checkout.session.async_payment_succeeded`.

`frontend/public/_redirects` is copied into `dist` so client-side routes fall back to `index.html`.

Changing `EXPO_PUBLIC_BACKEND_URL` requires a new build. The static site does not read it at runtime.

## Check the export locally

From `frontend`, with the API already running:

```
npx expo export --platform web
npx serve dist -p 3011
```

Leave ports 3000 and 3010 alone if something else is using them. For local play, `EXPO_PUBLIC_BACKEND_URL` is `http://127.0.0.1:8001` (no `/api`).
