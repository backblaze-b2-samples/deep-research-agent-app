# Railway Deployment

Deploy both services (web + api) on Railway.

## Setup

1. Create a new Railway project
2. Add two services from the same repo:

### Web Service (Next.js)
- **Root Directory**: `apps/web`
- **Build Command**: `pnpm install && pnpm build`
- **Start Command**: `pnpm start`
- **Port**: `3000`

### API Service (FastAPI)
- **Root Directory**: `services/api`
- **Build Command**: `pip install -r requirements.txt && python -m playwright install --with-deps chromium`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

> The research agent renders pages in headless Chromium, so the build must
> install the browser (and its OS deps via `--with-deps`).

## Environment Variables

Set these on the API service:

| Variable | Value |
|----------|-------|
| `B2_REGION` | Your B2 S3 region (e.g. `us-west-004`) |
| `B2_APPLICATION_KEY_ID` | Your B2 application key ID |
| `B2_APPLICATION_KEY` | Your B2 application key |
| `B2_BUCKET_NAME` | Your bucket name |
| `B2_PUBLIC_URL_BASE` | Optional public object URL base for public buckets |
| `ANTHROPIC_API_KEY` | Your Anthropic API key (powers the agent) |
| `API_CORS_ORIGINS` | Your web service URL (e.g., `https://web-production-xxx.up.railway.app`) |

Roll out B2 env changes in expand/contract order: add `B2_REGION` and, for
public buckets, `B2_PUBLIC_URL_BASE` before removing old variables. Legacy
`B2_ENDPOINT` can remain set without blocking startup but is ignored. Legacy
`B2_PUBLIC_URL` is used only as a temporary fallback when
`B2_PUBLIC_URL_BASE` is absent. Remove both legacy variables after the Railway
environment has the standard names.

**After rollout:** delete `B2_ENDPOINT` and `B2_PUBLIC_URL` from Railway
Variables so the deployment only carries the standardized B2 contract.

Set this on the Web service:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your API service URL (e.g., `https://api-production-xxx.up.railway.app`) |
