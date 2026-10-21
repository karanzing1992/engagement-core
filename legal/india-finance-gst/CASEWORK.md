# Casework retrieval templates

## Moksha sauna or ice bath paid booking
- Inputs: service(s), price inclusive/exclusive of tax, location, date of supply, booking advance date, voucher/refund terms, billing entity GSTIN, customer GSTIN and place of supply.
- Search: `python3 legal_search.py search "wellness sauna GST classification" --jurisdiction IN-GA --strict`.
- Consult CGST Act, IGST place-of-supply rules, current Central Tax (Rate) notification, Goa counterpart and service classification (SAC); combine/exemptions require accountant sign-off.
- Do **not** use 57th Council suggestions or generic yoga/health/spa assumptions as an effective rate.
- Reconcile WooCommerce receipt versus Razorpay settled amount and refund/advance; avoid double-counting revenue.

## GST returns
- Search: `python3 legal_search.py search "GSTR 1 GSTR 3B QRMP" --as-of 2026-10-21`.
- Check portal extension notices and entity's actual filing frequency. Reconcile GSTR-1, 3B and 2B; don't claim credit without entitlement evidence.
- Prepare draft → discrepancy report → accountant approval → payment/EVC/DSC → retain ARN and reconciliation receipts.

## TDS vendor invoice or contractor payment
- Search: `python3 legal_search.py search "TDS 2026 section 393" --as-of 2026-10-21`.
- Resolve payee residency/PAN, nature of payment, date of credit/payment, thresholds and applicable 2025 Act table item. For transactions before 2026-04-01, review savings and legacy Act provisions.
- Produce exact section/table item and threshold with official evidence; seek validation before remittance.

## Change alert for 57th GST Council meeting
- `python3 legal_search.py search "57th" --include-nonbinding`.
- Only signal a **proposal** until the Gazette notification/Act/rule and commencement are established. Do not update live tax rates.
