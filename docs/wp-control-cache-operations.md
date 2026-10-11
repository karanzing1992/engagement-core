# WordPress Control - Single-page cache diagnostics

Source: engagement-core plugin v0.9.14. Reuse existing authenticated WordPress Control rather than new plugins or generic remote code execution.

Operations:
- cache_diagnose: published same-site page post_id plus optional visible expected_text, at most 160 characters. Compares canonical and cache-busted HTML (hashes, safe headers, expected-text presence), 256 KiB each, 12s timeout, no cookies, no redirects. Page content is not returned.
- cache_purge_target: published page post_id, mode=url (default) or post, dry_run or explicit confirm=true. Uses LiteSpeed's documented litespeed_purge_url or litespeed_purge_post hooks. Post mode may also invalidate tagged archives. Never purges all caches.
- WordPress abilities: wp-control/cache-diagnose, wp-control/cache-purge-target. Both enforce WordPress manage_options capability. The existing OAuth gateway additionally enforces paired owner and site identity.
- Existing broad full-cache ability is unchanged. Do not invoke it for routine SEO updates.

Example diagnostic input: {"post_id":12627,"expected_text":"Where can I book sauna and ice bath contrast therapy in Goa?"}
Example targeted purge input: {"post_id":12627,"mode":"url","confirm":true}

Test source with: php -l src/class-grec-cache-tools.php; php tests/cache-control-smoke.php.
Stage and review via GitHub PR. Deploy the installed WordPress plugin using existing approved Deployer for Git/signed update flow, separately deploy gateway function only after drift inspection. Verify live installed version and direct canonical page. Purge hook dispatch is not proof the visitor cache is fresh: Hostinger/edge caches may be separate.

Rollback: revert versioned merge and restore prior plugin release; restore gateway separately if deployed. No database migration, WooCommerce checkout changes, or customer data access.

LiteSpeed reference: https://docs.litespeedtech.com/lscache/lscwp/api/
