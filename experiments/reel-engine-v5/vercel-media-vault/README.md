# Moksha V5 Vercel Media Vault
Private Vercel Blob store: `store_l05UzStrKsGssbGf`; connected project `prj_D0y6OIJmt5QUCqzHXoL2hEANajlK`.

## Required environment variables
- `BLOB_READ_WRITE_TOKEN`: Vercel Blob store credential (not yet provisioned).
- `VAULT_TOKEN`: separate random API bearer secret.

Do not store credentials in GitHub. Upload and download endpoints are restricted to the bearer token. Private preview requires authenticated GET. No public Blob URLs.

## Integration
GitHub V5 pipeline downloads `source/1000083489.mp4` via `GET /api/media?key=source%2F1000083489.mp4` with `Authorization: Bearer $VAULT_TOKEN`, verifies SHA256 `931a373e5b392de395bb5d6e0a11780e83dbe43977715129c5796faac1b13a6f`. Upload final to `render/<job-id>.mp4` after rights gates.

## Important limitations
This initial server-side PUT intentionally limits bodies to 4 MiB; source file ~9.56 MB requires multipart/client upload or trusted backend transfer. Do not claim source ingestion or rendering complete. Private preview range support needs verification and may require upstream range passthrough. Vercel project has not been deployed. Credential provisioning, deploy, end-to-end QA and master registry update remain required.
