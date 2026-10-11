# Verified brand asset system — first-party Media Studio

## Exact provenance

The original Moksha logo is stored in **Google Drive** as `Moksha_Logo_Source_01.jpeg` with immutable file ID `1XwmlYRfjfkcnbEOlJLNJc8bGHm9uxkyv`. The approved source-of-truth record is `Moksha_Brand_Asset_Defaults.txt` (Drive ID `1px59pg6Asp3AntBRvgUGO1zazcl39LX8`). The master is a black-backed 737 × 681 JPEG containing the gold floral emblem and MOKSHA WELLNESS serif wordmark.

The Git repository contains a **byte-identical mirror**, used only to bootstrap WordPress and by trusted render workers. SHA-256: `76e89b83667827da4b5d89143fb267f4000a9392eff685129c838c3d0b24748c`. **Google Drive remains the authoritative editable source.** This mirror is not an alternate logo.

### Automatic workflow

1. Resolve `brand=moksha` to one exact Drive ID; never search for `logo` and choose the first result.
2. Check exact bytes, hash, file dimensions and MIME type before accepting a master or WordPress cached copy.
3. The first explicit WP Control sync imports the original byte-for-byte into WordPress uploads, registers its attachment ID, source ID and SHA-256. It never alters the master.
4. On every resolved asset request, reverify the cached attachment file hash and fail closed if mismatched.
5. When an administrator creates a fresh Moksha Media Studio draft, automatically populate the canonical verified attachment, not an unrelated logo already in the Media Library.
6. Reconcile existing **unapproved** private drafts without touching approved creatives or overwriting manually chosen incompatible assets. A previously rendered preview without the logo is demoted to `draft` with `rebranding_required` so an unbranded render cannot be approved by mistake.
7. Rendering workers call the signed WP Control `/brand-assets/moksha/resolve?placement=reel` endpoint and download the returned public **official logo attachment URL**, verify SHA-256 again locally, and place it according to the registered policy. WordPress itself does not encode videos.
8. Published media is never created or scheduled by this feature. Render approval remains separate.

### Endpoints

These are registered by **Engagement Core** and are accessible only to authenticated WP administrators or workers with the independently scoped `X-WP-Control-Brand-Token` HMAC derived from the existing Deployer secret (no new credential required):

- `POST /wp-json/wp-control/v1/brand-assets/moksha/sync` — import/verify master and reconcile private drafts; safe and idempotent.
- `GET /wp-json/wp-control/v1/brand-assets/moksha/resolve?placement=reel` — return file ID, approved hash, verified WordPress attachment ID/URL, dimensions and output-specific placement.
- `GET /wp-json/wp-control/v1/brand-assets/moksha/status` — report integrity state.

**No generic remote-fetch endpoint exists.** This design cannot be abused to download arbitrary URLs onto WordPress. The source is embedded via a known blob and checksum; new approved masters require an explicitly reviewed registry change.

### Future Drive update protocol

Drive master modification **does not automatically rotate** the pinned asset. On detecting that Drive metadata modifiedTime or the file SHA-256 differs, stop and request human approval. A new approval should record the canonical ID, exact bytes, cryptographic hash, repository mirror update, WordPress copy replacement via reviewed upgrade, and all affected output variants. Do not simply repoint a Drive link or use another search result. For unattended change detection, provision a restricted Drive credential in the cloud worker separately; **none is assumed or requested here**.

### Hard safety rules

- Never invent, vectorize, redraw, recolor, crop to an unapproved symbol or erase the black backing of the logo. Only scale the authentic source preserving its aspect ratio. A different transparent variant requires explicit approval and a *separate* immutable checksum.
- Don't put a logo splash card in the first 1–1.5 seconds of discovery Reels and Shorts. Use a subtle appropriate branded closing card after the hook. Keep story/feed safe zones for platform UI.
- If brand, placement, Drive file ID, file hash, dimensions, WordPress attachment identity, or license/provenance are inconsistent: **block**, audit, and request review. Never guess.

### Future brand expansion

Add another brand only with its own explicitly approved Drive master, verified bytes/hash, placements and an isolated registry record. Nothing for Andaz or other brands is auto-approved by the existence of this Moksha asset.