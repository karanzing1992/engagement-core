# Mandatory agent instructions — India Finance & GST (all connected projects)

**Always query this index first** for India tax, GST, bookkeeping compliance, TDS, fiscal-year interpretation, Indian invoices or statutory treatment. Then open the cited **official government primary source** at point of use. Do not use unverified model memory as current law.

## Minimal operating protocol

1. Classify case and collect jurisdiction `IN` plus state `IN-GA` as applicable, transaction/service, supply date, entity/GST registration, SAC/HSN, customer status, payment/credit dates and relevant turnover.
2. Build index once `python3 legal_search.py build`, search:
   `python3 legal_search.py search "terms" --as-of YYYY-MM-DD --jurisdiction IN-GA --json`.
   Add `--include-nonbinding` only when investigating proposals/historical changes.
3. **Mandatory validation gate:** record `record_id`, `source_url`, section/notification ID, tax period, `effective_from/to`, source timestamp, `checked_on`, interpretation and confidence. For a law-change announcement, find the corresponding enacted Act, notified rules, applicable Goa amendment and commencement, or mark **UNVERIFIED**.
4. Output `applicable | proposed | uncertain | superseded`; never conflate FAQ, Council recommendation and enacted law. If evidence conflicts, flag human review and withhold tax automation.
5. Apply date-sensitive law including **Income-tax Act 2025 / Rules 2026 transition (1 April 2026)**; previous-year transactions may retain 1961 Act references.
6. Do not automatically set GST rate, ITC eligibility, vendor TDS, invoice treatment, exemptions, filing regime or place of supply without confirming taxpayer facts and current binding source. **Do not submit GST returns, pay tax, alter ledgers or send reports without explicit user authorization.**
7. Add new verified source records via reviewed Git commits with original URL, status, publication/effective dates and concise summary. No invented citations, no copyrighted fulltext copying, no crawl avoidance bypass.

For Moksha: distinguish yoga, sauna, ice baths, mud/aloe rituals, retreats, bundled packages, advance payments and booking refunds. For Andaz: hostel accommodation, rooms, food/beverages and mixed supplies may require distinct SAC/GST treatment. Never infer one GST rate from another.

`recommendation` and `requires_verification` are not executable accounting rules. Confirm Goa SGST counterpart for intra-State GST. If `checked_on` is older than 14 days, proactively refresh before making a consequential filing decision.
