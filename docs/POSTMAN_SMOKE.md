# Postman Smoke Tests

Basic API checks using Postman or Newman.

## Import Collection
- File: `docs/postman/AP2Expense-Smoke.postman_collection.json`
- Set collection variable `baseUrl` to your backend URL.

## Run with Newman (CLI)
```bash
npm install -g newman
newman run docs/postman/AP2Expense-Smoke.postman_collection.json \
  --env-var baseUrl=https://<BACKEND_HOST>
```

## Expected
- `/health`, `/api/webhooks/gcp/health`, `/metrics` return 200.
- `/metrics` contains `http_requests_total` and latency histogram.

