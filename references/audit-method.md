# Audit method

## Evidence and certainty

A confirmed finding requires an observed code/configuration defect and an established failure mechanism. Explain the triggering inputs, missing protection, and whether deployment or runtime evidence exists. Static evidence may confirm an unsafe code path without proving that an incident occurred. Use `potential` when reachability, intent, scale, configuration, or impact remains unverified, and specify a concrete validation step. Keep general assumptions and unanswered questions outside the findings unless they describe a specific supported risk.

For each finding include a stable ID, short plain-language title, category, P0–P3 severity, severity rationale, certainty, affected module IDs, description, file/line evidence with an explanation, technical impact, business impact, recommended improvement, estimated engineering effort and assumptions, and verification/acceptance criteria. Cite multiple locations when a conclusion depends on their interaction. Quote only the minimum needed and redact secrets. For an absent file or control, cite the relevant registration/configuration and explain the searched scope; absence cannot be proven by an invented line number.

Verify that a suspicious pattern is active and understand its callers, guards, and tests. Large files, old code, duplicate libraries, TODOs, missing comments, and style preferences are investigative leads rather than defects. Avoid fabricated precision, dollar losses, incident frequencies, throughput, or performance percentages. Record “not assessed” rather than “no problems” where evidence is missing.

## Severity

| Level | Meaning | Evidence needed |
| --- | --- | --- |
| P0 | Emergency: ongoing or immediately credible catastrophic impact, such as broad compromise or irreversible data loss. | Demonstrated reachable mechanism and exceptional impact; distinguish confirmed incidents from credible threats. |
| P1 | High: a credible path to serious exposure, major outage, material data loss, or broken core business functionality. | Concrete trigger, affected boundary or flow, and serious consequence. |
| P2 | Medium: bounded correctness, reliability, performance, testing, or maintainability problem with meaningful cost. | An observed problem and a defensible connection to delivery or operational risk. |
| P3 | Low: limited impact, local friction, or a useful small improvement. | Specific evidence and a clear benefit; omit taste-only suggestions. |

Severity and certainty are separate. A potential P1 has high impact if its condition holds; present that condition and validation prominently. Confirmed severity must not be increased because a module is large or has many dependents. Do not impose target counts or score all modules 0–100 from model judgment. An unreviewed module has unknown risk.

## Coverage dimensions

| Dimension | Investigate |
| --- | --- |
| Architecture | Actual boundaries, entry points, dependency direction/cycles, data ownership, event flows, external integrations, background work, runtime topology, mismatch with documented design. |
| Project structure | Capability organization, build/workspace boundaries, shared code, ownership, generated/vendored separation, configuration consistency. |
| Dependencies | Manifest and lockfile consistency, active use, overlapping responsibilities, risky pins, update practices, advisories verified against official sources, applicable license obligations when relevant. |
| Separation of concerns | Business logic versus transport/storage/UI, cross-boundary contracts, coupling that causes demonstrated change cost, conflicting responsibilities, duplicated rules that can diverge. |
| Security | Trust boundaries, authentication, authorization and tenant isolation, input validation, injection, secret handling, unsafe serialization, file/URL access, exposed debug/admin paths, sensitive logging. |
| Performance | Real hot paths, repeated queries, unbounded work/payloads, synchronous blocking, concurrency, cache correctness, resource lifecycle; separate static suspicion from measured bottlenecks. |
| Testing | Critical user journeys and failure modes, behavioral assertions, isolation, skipped/flaky tests, meaningful integration coverage, CI enforcement. Coverage percentages alone do not prove quality. |
| Maintainability | Contracts/types, error handling, observable failures, change hotspots, duplicated business rules, dead paths with verified non-use, documentation drift, operability. |
| Deployment | CI gates, environment parity, build reproducibility, privilege boundaries, config/secrets, migration ordering, rollback, recovery/backups, health checks and observability. Repository config does not prove deployed state. |

Add domain-specific checks when supported by the product context. For every dimension record `reviewed`, `partial`, or `not-assessed`, plus the inspected scope and result. “Reviewed” means the applicable scope was assessed, not that it passed.

## Effort and investment

Estimate ranges for one engineer familiar with the repository: hours or engineer-days, including tests and review. State assumptions such as access, data migration, release coordination, and external dependencies. Mark unknowns explicitly and separate engineering effort from elapsed delivery time. Avoid mechanically adding overlapping estimates.

Recommendations should describe what to change, the expected risk reduction, and how to prove success. A larger refactor needs evidence of current cost/failure, a smaller option considered, expected value, and a staged migration with regression protection. Keep intentional simplicity when its replacement would cost more than it returns.

## Roadmap and verification

Prioritize containment for urgent issues, validation of uncertain high-impact risks, stabilization of critical behavior, then targeted debt repayment. Use phases as sequencing guidance; timing is indicative unless the user supplies capacity/deadlines. Dependencies refer to earlier phase IDs. Each finding belongs to exactly one phase so nothing falls out of the plan; a phase may first validate a potential risk before deciding whether to implement its correction.

Review the final findings against evidence a second time. Confirm paths and one-based lines at the recorded revision, severity/likelihood, certainty, effort assumptions, and recommendation value. Explain checks unavailable due to tool, credential, environment, or side-effect limitations. A successful render is artifact validation, not proof that the audit identified every defect.
