# India Finance & GST — source-verified legal index (MVP)

A **public, non-confidential, searchable pointer database** for Indian business finance, central GST, **Goa SGST** and income-tax rules. This is a legal source index, **not** an authoritative consolidated statute or permission to automate tax filing.

**As-of:** 2026-10-21. **Coverage:** 30 curated records. Only verified primary government links and concise original summaries. Key 2026 updates are included; coverage is **not exhaustive** and a linked source may later change.

## Quick search (no dependencies, Python 3.10+)

```sh
cd legal/india-finance-gst
python3 legal_search.py build
python3 legal_search.py search "GSTR-3B ITC" --jurisdiction IN-GA --as-of 2026-10-21
python3 legal_search.py search "sauna gst rate" --jurisdiction IN-GA --strict
python3 legal_search.py search "57th council" --include-nonbinding --json
python3 -m unittest discover -s tests -v
```

Indexed fields: title, summary, topic, keywords, authority, jurisdiction and legal instrument. Local SQLite **FTS5** database is generated from Git-tracked `data/records.jsonl`; no paid API, network or LLM required for searches. The JSONL is also ordinary **GitHub code-searchable text**. Run `python3 legal_search.py source-check` for rapid official-URL availability checks (best-effort; fail-closed). The SQLite file is generated and must not be edited as the source of truth.

## Rules of use

1. Gather **transaction date, state, entity legal type, GSTIN/registration status, supply nature and SAC/HSN, domestic/foreign buyer, turnover, return filing preference, invoice/payment event date**. Ask for unknowns.
2. Query records relevant to the **law and time period**. Central and Goa rules both matter for Goa sales. A recommendation/FAQ never silently overrides a statute or notified rule.
3. Open primary source and identify the **operative statute, amendment, Gazette/notification number, commencement date and transitional provisions**. Source-index summaries are leads, not rulings.
4. Quote the exact official URL, rule/section, date checked, analysis and unknowns. For rates, thresholds and ITC, require formal accountant/tax-professional validation before saving automation rules.
5. Recheck against live government sites before each return and after each law change. A 2025/2026 Council recommendation remains nonbinding unless implemented. No auto-GST submission.

## Change management

- Records have `status` (`in_force`, `guidance`, `reference`, `recommendation`, `historical`, `requires_verification`), `effective_from/to` and `checked_on`.
- Run `python3 monitor.py --state data/watch-state.json` to fingerprint selected official **hub pages** and identify change candidates. It never transforms announcements into active law, and it won't bypass robots, login, CAPTCHA or rate limits.
- Review every changed government item and append an amended record with traceable effective dates; preserve superseded historic rules, do not overwrite historical truth.
- For ingestion of full government PDFs, keep **original URLs and hashes**, respect website terms and copyright, and do not bulk republish unlicensed text.
- This initial index is a seed, not a guarantee that every Indian finance law has been captured. Prioritise GST, income tax, TDS, payroll, accounting standards and RBI/payment circulars in future reviewed batches.

See [AGENTS.md](AGENTS.md) for required retrieval steps and [CASEWORK.md](CASEWORK.md) for Zoho/Moksha examples.
