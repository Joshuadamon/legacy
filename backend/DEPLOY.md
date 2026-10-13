# Deploy LEGACY on Railway

Handoff steps for the live API service and the Pages web build are in `DEPLOY.md` at the repository root.

Do not put secrets, connection strings, or API keys in this file or in git.

1. Install the Railway CLI and log in: `railway login`
2. From `backend/`, link the service to the project that already exists: `railway link`
   Do not create a Railway project from this repository.
3. Set these variables on the service. The values stay in Railway.
   - `MONGO_URL` — the Atlas connection string
   - `DB_NAME` — optional, default `legacy`
   - `ANTHROPIC_API_KEY` — server only. Never prefix it with `EXPO_PUBLIC_`
   - `PORT` — Railway sets this. The process reads it.
   - `MODEL_PROVIDER` — optional, default `anthropic`
   - `MODEL_NAME` — optional. If unset, the server uses `ANTHROPIC_MODEL`, then `claude-sonnet-5`
   - `ANTHROPIC_MODEL` — optional default model name when `MODEL_NAME` is unset
   - `LEGACY_SEASON_LIMIT` — optional seasons per user per hour, default `60`
   - `LEGACY_STARTING_MARKS` — leave unset so a new profile still starts at 250 marks
4. Deploy from `backend/` with `railway up` onto the existing `legacy-api` service.
   Railpack starts `uvicorn main:app`. `backend/main.py` re-exports the app from `server.py`.
5. Set the Expo production secret `EXPO_PUBLIC_BACKEND_URL` to the Railway host. The host is not written here.
