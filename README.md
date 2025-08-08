# TrueLink API (Advanced)

This project provides a FastAPI-based HTTP API around the `truelink` Python library.
It supports single and batch URL resolution and is ready to deploy on Render.

## Endpoints

- `GET /health` - Health check.
- `GET /resolve?url=...` - Resolve a single URL.
- `POST /resolve-batch` - Body: `{ "urls": ["url1", "url2"] }` to resolve multiple URLs concurrently.
- `GET /supported-domains` - Returns list of supported domains.

## Deploy on Render

1. Push repository to GitHub.
2. Create a new Web Service on Render and connect the repo.
3. Use the provided `render.yaml` or configure build/start commands manually.

The build command installs the latest `truelink` on each deployment to ensure you get updates.

## Notes

- Concurrency for batch resolution is limited with a Semaphore to avoid overloading providers.
- Results are converted to JSON-friendly structures where possible.
