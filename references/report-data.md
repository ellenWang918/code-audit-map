# Report data contract (version 1)

Write UTF-8 JSON, then render using `scripts/render_audit.py`. The example in `assets/example-audit.json` demonstrates the full shape; its repository, paths, findings, and effort are fictional. The renderer requires the fields below and rejects broken references. Extra fields are not rendered.

## Top-level fields

- `schema_version`: integer `1`.
- `meta`: `project`, `audited_at` (ISO 8601 with timezone), `revision` (commit or “unavailable”), `worktree` (status or “unavailable”), `scope`, `status` (`complete` or `partial`), `is_demo` (boolean). Optional `repository_url` is an HTTPS repository URL used to link evidence at a full commit hash; omit for private/offline projects or unsupported hosts.
- `summary`: `verdict` (a qualified assessment), `executive` (list of key conclusions), `architecture` (list of actual-system assessment paragraphs), `priorities` (ordered finding IDs), `strengths` (list of `{description, evidence}`), `assumptions` and `questions` (lists of strings). Empty lists are valid when justified; do not invent strengths or questions to fill a template.
- `layers`: ordered list of `{id, label}` defining map columns in flow order. Use topology appropriate to the repository rather than imposing a web-app template.
- `modules`: list of `{id, label, layer, type, purpose, business_role, review_status, paths, evidence}`. `layer` references a layer ID. `type` is a plain-language label (e.g. “Data store”). `review_status` is `reviewed`, `sampled`, or `unreviewed`. `paths` lists repository-relative files/directories or external service identifiers; exact file citations belong in `evidence`. Audited first-party modules need evidence; an unreviewed or inferred external boundary can have none if its uncertainty is explicit in purpose/business_role.
- `relationships`: list of `{id, source, target, label, kind, confidence, evidence}`. `source`/`target` are module IDs; direction is the actual relationship, not an assumed reciprocal dependency. `kind` is `request`, `data`, `event`, `dependency`, or `deployment`. `confidence` is `confirmed` or `inferred`; confirmed edges require evidence. Use short labels explaining the action. Dashed edges indicate inference.
- `journeys`: list of `{id, title, description, steps, relationship_ids}`. Each step is `{module, text}`. `relationship_ids` contains exactly the directed relationship between each consecutive pair of steps. Provide representative product paths when present; a library or infrastructure repository can instead trace a consumer call, build, or deployment. An empty list is allowed when no path can responsibly be established.
- `findings`: list of the finding objects below. Its order determines the prioritized table within severity; sort deliberately by business risk, certainty, and dependencies.
- `roadmap`: ordered phases `{id, title, timing, goal, finding_ids, dependencies, success_criteria}`. `timing` can be “Before next release” or another justified indicative sequence; `success_criteria` is a list of observable conditions. `dependencies` references earlier phase IDs. Every finding is assigned once; no findings means an empty roadmap is valid.
- `coverage`: `inventory_count` (equals length of `files`), `files` (unique `{path, status, reason}` entries), `exclusions` (list of `{path, reason}` for omitted directory scopes, sensitive files, inaccessible submodules, etc.), `dimensions` (one `{name, status, summary}` per required audit dimension), `checks` (list of `{name, status, detail}`), `limitations` (list of strings).

File statuses: `reviewed`, `sampled`, `unreviewed`, `excluded`. Dimension statuses: `reviewed`, `partial`, `not-assessed`. Check statuses: `passed`, `failed`, `not-run`. Required dimension names: `Architecture`, `Project structure`, `Dependencies`, `Separation of concerns`, `Security`, `Performance`, `Testing`, `Maintainability`, `Deployment`.

`complete` requires no sampled/unreviewed inventoried files, no partially reviewed/unreviewed modules, and all required dimensions reviewed; declared generated/vendor/sensitive exclusions can remain. This describes completion of the declared scope, never certainty that no bugs exist. Use `partial` for inaccessible first-party areas or any unresolved review coverage. If live checks cannot run, state that limitation even when static review is complete.

## Finding object

```json
{
  "id": "F001",
  "title": "Business consequence in plain language",
  "severity": "P1",
  "confidence": "confirmed",
  "category": "Security",
  "severity_reason": "Concrete exposure and reason for this priority",
  "modules": ["orders"],
  "description": "Observed behavior, trigger, and context",
  "evidence": [{"path": "src/orders.ts", "line": 32, "end_line": 40, "note": "What these lines establish"}],
  "technical_impact": "Failure mechanism and scope",
  "business_impact": "Customer or operational consequence without invented financial claims",
  "recommendation": "Smallest useful correction and its benefit",
  "effort": {"range": "1–2 engineer-days", "assumptions": "Includes regression tests; assumes no data migration"},
  "verification": "Observable acceptance check or risk-validation step"
}
```

`severity` is `P0`, `P1`, `P2`, or `P3`; `confidence` is `confirmed` or `potential`. At least one affected module and one evidence citation are required. Module status must reflect how much was read, not whether a finding exists. Paths in evidence and coverage are repository-relative, without `..`, absolute paths, or credential-bearing URLs. Evidence is `{path, line, end_line?, note}` with positive one-based lines. Notes describe the relevant behavior, not copied secrets. Use `verification` to identify the missing fact for potential risks.

IDs use letters/digits/hyphens/underscores, beginning with a letter; they are unique within each collection. References must resolve. Rendered text is treated as text, not HTML; report content cannot introduce executable markup.

## Commands

```text
python <skill-directory>/scripts/render_audit.py --input <report-directory>/audit-data.json --output <report-directory>/code-audit.html
python <skill-directory>/scripts/render_audit.py --input <report-directory>/audit-data.json --validate-only
python <skill-directory>/scripts/render_audit.py --input <report-directory>/audit-data.json --validate-only --root <repository>
```

`--root` verifies cited files exist and line ranges fit while rejecting links escaping the repository. It reads only cited files as UTF-8 (replacement for undecodable bytes). Omit it for the fictional example; it cannot validate source behavior or the coverage ledger. Keep outputs outside the audited tree; the renderer cannot infer that boundary without `--root`, so the auditor must resolve it.

## Repeat runs and replacement

Keep the same output directory, JSON path, and HTML path across runs. The first-run default directory is `<repository-parent>/.code-audit-map/<repository-folder>/`; user-selected and previously established destinations take precedence. Update the current report rather than producing a filename with a date, counter, or revision suffix.

The renderer automatically replaces an existing report when its embedded audit JSON passes validation and `meta.project` matches the incoming data. It recognizes reports generated by earlier versions of this skill. It writes a temporary sibling file, then atomically replaces the HTML only after rendering succeeds. Temporary files are cleaned up. Unrelated HTML, invalid embedded data, or a different project are preserved unless `--force` is supplied. If intentionally renaming the report's project title, use `--force` for that explicitly requested rename while retaining the same output path.

Keep IDs for continuing modules/findings, refresh evidence and assessment metadata, remove only verified resolved findings from the active list, and explain material changes in the executive summary. Stage and validate updated JSON before rendering; promote it to the existing `audit-data.json` after successful HTML generation, then verify the two artifacts agree. JSON/HTML replacement is not a multi-file transaction: if interrupted between replacements, use the validated staged data to finish the update and restore consistency before reporting success. Do not copy prior coverage or certainty without rechecking it.
