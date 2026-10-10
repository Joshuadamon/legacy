# LEGACY

An 18+ text-first life simulator. One life runs from birth to death, a year at a time. On death you continue as a child, or as a distant relative. Legacy Marks are a soft currency that persists across lives.

This repo is the local version of that game: FastAPI and MongoDB (or an in-memory stand-in) on the API, Expo on the phone.

## Run it

API, from `backend`:

```powershell
.\.venv\Scripts\python -m uvicorn server:app --host 0.0.0.0 --port 8001
```

The default database is in-memory (`MONGO_URL` unset or `memory://`). It resets when the process stops. For a real database, copy `backend/.env.example` to `backend/.env` and point `MONGO_URL` at MongoDB. `docker compose up -d` starts one if Docker is installed.

App, from `frontend`:

```powershell
npx expo start --web --port 3000
```

`frontend/.env` should contain `EXPO_PUBLIC_BACKEND_URL=http://localhost:8001`.

Sign-in is a name plus a one-time session on this server. It keeps the `/api/auth/session`, `/api/auth/me`, and Bearer-token contract so a Google login can replace the name field later without changing the app.

Years are written from a fixed deck unless `ANTHROPIC_API_KEY` is set. The model name is `ANTHROPIC_MODEL` (default `claude-sonnet-5`). If the model call fails, the deck is used and the year still resolves.

## Tests

```powershell
cd backend
.\.venv\Scripts\python -m pytest
```

From `frontend`, `npm run lint` is `tsc --noEmit`.

## What is in this pass

- Birth to death, personality flags, paths, heirs, lineage, save migration
- Legacy Marks: 250 to start, a grant on death, a store of career, skill, cosmetic, lifestyle, and supernatural packs
- Owned skill packs change the living character once per life. Career packs open fields in the year prompt. Supernatural packs are kept on the profile for a later birth; they do not change the body yet

## Next

Vampire meters end to end, then lycanthrope and witch, then marriage, careers and inherited businesses, the family tree, and skipping a few childhood years.
