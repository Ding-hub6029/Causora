# Model request provenance — current and historical evidence

## Current OpenRouter validation

On 2026-10-08 the backend SDK was configured with **https://openrouter.ai/api/v1** and the existing securely injected OPENROUTER_API_KEY. No credential was copied from chat/attachments into source. The verifier records `chatOrAttachmentKeyImported=false`, exact requested model IDs, timestamp, request/schema/output hashes, returned provider/model/request ID where supplied, usage and cost. No key value/header/label is retained.

The current actual record is verification/wang_day4/budget_portable_revision/live/final_openrouter_evidence.json. This is application-side evidence of authenticated HTTPS SDK requests and API responses, not a signed provider execution/billing export. The actual API named itself OpenRouter and returned OpenAI provider/model IDs for four successful transports. Deeper upstream routing/ownership/invoices are **Unverified**.

| Stage | Observed result | Claim allowed |
| --- | --- | --- |
| CFO/COO/Risk | Fresh openai/gpt-5-mini requests/returned IDs, usage/cost, accepted role checks | Actual new role responses. Not fixtures/cache |
| Gemini Critic | google/gemini-3.1-pro-preview requested. Provider_bad_request. No returned model/usage | Actual failed request. **not successful Gemini validation** |
| GPT Critic fallback | openai/gpt-5-mini returned, usage/cost, but numerical-word one rejected | Successful HTTP/content return. **not accepted Critic/fallback success** |
| Synthesizer | No request after both Critics failed acceptance | **Not executed**. No old response substituted |
| Full workflow | Failed at Critic. No published Brief | **Not completed** |

All model stages attempted were new. No old role, fixture, cached payload or checkpoint entered this verifier. The identity-bound MC input/capture was reused without recomputation. Actual capture bytes/traces and runtime fingerprint remain identical before/after. Later documentation/local tests do not change inference runtime. Fingerprints are in the manifest and final_runtime_attestation.json.

Five new reservations, no auto retry. Four response usage.cost fields total **USD 0.0042940**. Gemini actual cost is **Unverified**. Its USD 0.081288 reserve remains. The whole conservative shared-journal total is USD 0.11379800. The immediate read-only key usage delta is zero, which is not proof of no charge: delayed settlement/other key activity is not independently measured. No complete invoice, account-owner proof or independently verified user-charge attribution exists. We do not infer a Manus subscription/billing result.

No purchase, top-up, key mutation or extra model request followed verification. Current paid one-shot is consumed and cannot be repeated by deleting history.

## Historical preconfigured proxy evidence

The previous full forensic report is preserved verbatim under `verification/wang_day4/budget_portable_revision/prior_delivery_documents/MODEL_REQUEST_PROVENANCE.md` and earlier archives. Its old 'no network assessment' and 'blocked preflight' statements apply to that historical snapshot, not this current run.

Old agent_day4.provider.LiveProvider reads sandbox-preconfigured OPENAI_API_KEY and OPENAI_API_BASE/OPENAI_BASE_URL. Runtime documentation identifies these as the Manus-provided OpenAI-compatible sandbox capability. The old endpoint was locally classified as private/non-public. Its hostname/management URL is deliberately not published. Therefore the supported historical statement is **Manus-preconfigured SDK proxy path**, not a user-purchased direct OpenAI/Gemini account. Exact operator, upstream route/model and historical costs remain **Unverified**.

Old local audits assert eighteen requests and two additional six-call followups, thirty cumulative in that chronology. Duplicate snapshots are not added again. The final old followup records Gemini provider_bad_request then GPT Critic/Synthesizer returned and accepted by that old pipeline. It does **not** establish successful Gemini. Its D2 concentration wording was later identified as invalid and is not current business acceptance.

Relevant preserved files:

- verification/wang_day4/live/continuation_actual_audit.json — old sixteen-to-eighteen continuation, not a fresh complete flow.
- verification/wang_day4/followup/live/fresh_session_audit.json — old first six-call followup.
- verification/wang_day4/followup/live_second/fresh_session_audit.json — old Gemini error/GPT fallback sequence.
- verification/wang_day4/followup/final_runtime_attestation.json — old source hashes. Those differ from current allocation/provider/pipeline runtime.
- verification/wang_day4/live/openrouter/openrouter_evidence_manifest.json — previous **zero-call** read-only preflight, retained unchanged.

Historical source/ZIP fingerprint tables remain in their original report. They identify old code, not the new current run. Historical failures were not overwritten as passes.

## Evidence exclusions and limits

Fixtures labelled TEST_FIXTURE_ONLY, locally mocked SDKs, cache files, test pass counts and offline replay of the actual rejected Critic are **not new model calls**. Current `critic_rejection_forensics.json` explicitly says zero new requests and OFFLINE_FORENSIC_RECHECK_NOT_NEW_MODEL_VALIDATION.

No provider-signed logs, invoice/account ownership, exhaustive upstream model provenance, comprehensive semantic/business/legal approval or formal three-person E2E is claimed. Native Windows execution is also NOT_RUN. See DAY4_TEST_REPORT.md and DAY4_ACCEPTANCE_REPORT.md for separate local, actual-model, Windows and team states.
