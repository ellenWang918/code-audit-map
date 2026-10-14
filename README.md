# Code Audit Map

**English** | [简体中文](README.zh-CN.md)

![Read-only audit](https://img.shields.io/badge/audit-read--only-0071e3)
![HTML report](https://img.shields.io/badge/report-interactive_HTML-5856d6)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776ab)
![Renderer](https://img.shields.io/badge/renderer-standard_library_only-343434)

A reusable Codex skill that turns a repository into an interactive architecture map and an evidence-backed code audit that non-technical people can understand.

Understand what the software does, how its parts connect, which risks matter, and what to improve next—without changing the code being audited.

![Code Audit Map illustrated overview](docs/assets/overview.svg)

*Illustrated overview. The bundled demonstration uses a fictional ordering platform; it is not an audit of a real project.*

## Why Use It

A list of technical problems is difficult to act on when you cannot see the system behind it. Code Audit Map connects the architecture to the decisions: what customers depend on, where failures could occur, and which changes have a defensible business benefit.

The skill guides an AI agent through a Principal Software Engineer's review. The agent reads and assesses the repository; a deterministic Python renderer validates the report data and builds the HTML. The renderer itself does not discover defects or assign quality scores.

## Highlights

- **A map of business capabilities.** Explore areas such as customer checkout, identity checks, order storage, and external integrations rather than a wall of filenames.
- **Clickable relationships and guided journeys.** Select a capability to inspect direct connections, or follow a representative request, data, event, or deployment flow.
- **Evidence for decisions.** Findings include P0–P3 severity, certainty, relevant file paths and lines, technical and business impact, a recommendation, effort assumptions, and a validation step.
- **Honest uncertainty.** Confirmed problems, potential risks, assumptions, inferred connections, and unreviewed areas remain visibly distinct.
- **A practical remediation roadmap.** Sequence containment, validation, stabilization, and targeted improvements around value and dependencies.
- **One report that stays current.** Repeat audits update the same HTML and JSON paths; continuing findings retain their IDs.
- **An Apple-inspired presentation.** System typography, generous spacing, rounded cards, translucent navigation, blue accents, and printable detail.
- **An offline report.** The generated HTML embeds its data, styles, scripts, and SVG map. No CDN, hosted dashboard, or network connection is needed to view it.

## Workflow

![Audit workflow](docs/assets/workflow.svg)

```text
Repository
  → Inventory and understand the system
  → Trace capabilities, boundaries, and real flows
  → Review evidence and prioritize risk
  → Validate audit-data.json
  → Create or refresh the same code-audit.html
```

The review covers architecture, project structure, dependencies, separation of concerns, security, performance, testing, maintainability, and deployment. Repository content and existing check results inform the assessment; measurements or live verification are identified separately.

## What You Get

| Output | Purpose |
| --- | --- |
| `code-audit.html` | The interactive report: executive summary, architecture assessment, code map, user journeys, prioritized findings, remediation roadmap, and coverage. |
| `audit-data.json` | The structured source of truth used to reproduce and refresh the report. |

Every finding records:

| Field | What it explains |
| --- | --- |
| Severity | P0 emergency, P1 high, P2 medium, or P3 low, with a rationale. |
| Category and description | The observed behavior, trigger, and context. |
| Certainty | A confirmed problem or a potential risk with a condition to validate. |
| Evidence | Repository-relative paths, one-based line numbers, and what the cited code establishes. |
| Impact | The technical consequence and its customer, operational, or delivery effect. |
| Improvement | A scoped change with a clear benefit. |
| Effort | An engineering range with assumptions, rather than an unsupported delivery quote. |
| Verification | A check that demonstrates the correction or resolves the uncertainty. |

## Install

Requirements: Codex with local skill support, repository read access, and Python 3.9 or newer for rendering. The renderer uses only the Python standard library. Git is needed for the clone commands below.

### Personal installation

Install the repository as one skill folder. Current Codex documentation lists `~/.agents/skills` as the user-level discovery location. See the [official skill documentation](https://learn.chatgpt.com/docs/build-skills).

**macOS / Linux**

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/ellenWang918/code-audit-map.git ~/.agents/skills/code-audit-map
```

**Windows PowerShell**

```powershell
$skillParent = Join-Path $env:USERPROFILE '.agents\skills'
New-Item -ItemType Directory -Force -Path $skillParent | Out-Null
git clone https://github.com/ellenWang918/code-audit-map.git (Join-Path $skillParent 'code-audit-map')
```

If you already installed this skill in another location recognized by your Codex setup, update that copy instead of installing a duplicate with the same skill name.

### Project installation

From the root of the project where the skill should be available:

```bash
git clone https://github.com/ellenWang918/code-audit-map.git .agents/skills/code-audit-map
```

The skill folder contains the audit instructions and renderer. It is separate from the repository's generated audit report. Codex detects installed skills automatically; if the skill does not appear, restart Codex.

## Use

Open the repository you want to audit in Codex, then ask:

```text
Use $code-audit-map to audit this entire repository without changing its source.
Explain the architecture and business impact for a non-technical reader,
and produce the interactive HTML report with a phased remediation roadmap.
```

For a later review:

```text
Use $code-audit-map to refresh the audit of this repository.
Update the existing HTML and audit-data files at their current paths.
Recheck the evidence and explain meaningful changes since the previous audit.
```

You can specify a persistent output folder, a business context, a review scope, and the language of the explanations in the same request. The bundled interface labels are in English.

## Report Location and Repeat Runs

Without a chosen destination, the first audit uses a persistent folder outside the target repository:

```text
<repository-parent>/.code-audit-map/<repository-folder>/
├── audit-data.json
└── code-audit.html
```

Previously established or user-selected paths take precedence. Later audits reuse those exact paths; they do not create dated, numbered, or duplicate HTML reports by default.

The agent refreshes the inventory, architecture, evidence, findings, coverage, and roadmap. It preserves IDs for continuing findings and removes an active finding only after verifying resolution. An unchecked area is not treated as fixed.

The renderer recognizes an existing report for the same project and replaces it atomically after validation. Invalid input or a replacement failure preserves the previous HTML. Unrelated files and reports for another project are protected unless replacement is explicitly requested. The JSON and HTML are separate files, so the agent must finish and verify both updates before declaring the refresh complete.

## Try the Fictional Demo

Download or clone this repository, then open [examples/code-audit.html](examples/code-audit.html) in your browser. GitHub's file viewer shows source; download the HTML to use its interactive map.

To regenerate it from the repository root:

```bash
python scripts/render_audit.py --input examples/audit-data.json --output examples/code-audit.html
```

Run the same command again to refresh that same file. The example's product, evidence, findings, and estimates are all fictional.

To validate report data without writing HTML:

```bash
python scripts/render_audit.py --input examples/audit-data.json --validate-only
```

For a real audit, add `--root /path/to/repository` to validate cited file existence and line ranges. Keep the report output outside that root. Omit `--root` for the demo because its cited source files do not exist.

## Privacy and Read-only Boundaries

- The workflow instructs the agent to preserve the audited repository's source, tests, manifests, lockfiles, configuration, Git state, and existing changes.
- It does not authorize autofixes, dependency installation, migrations, deployments, or production operations.
- Secret values and customer records must not be copied into report data. Evidence identifies locations with redacted descriptions.
- Generated reports remain local by default and can contain internal architecture and source paths. Share them deliberately.
- The renderer contains no telemetry or network requests. An AI agent's repository access and model processing still follow that host's own permissions and data-handling policies; an offline report does not imply offline AI analysis.

## Review Limits

This is an agent-guided repository assessment, not an exhaustive defect detector, penetration test, performance benchmark, or verification of production state. A code path can establish a risk without proving that a real incident occurred.

The report tracks reviewed, sampled, unreviewed, and excluded files, plus the status of each review dimension and check. Partial review remains labeled partial. Large files, old code, and style preferences are investigative leads rather than automatic defects. Broad refactors require evidence of value and a reason a smaller change is insufficient.

## Documentation

| Need | Link |
| --- | --- |
| Agent workflow and boundaries | [SKILL.md](SKILL.md) |
| Evidence, severity, and effort standards | [Audit method](references/audit-method.md) |
| Report schema and renderer commands | [Report data contract](references/report-data.md) |
| Complete fictional input | [Example data](assets/example-audit.json) |
| Interactive fictional report | [HTML demo](examples/code-audit.html) |
| Renderer implementation | [render_audit.py](scripts/render_audit.py) |

## Development

Run the renderer's behavioral checks:

```bash
python -m unittest discover -s tests -v
```

The tests cover report validation, directed journeys, evidence ranges, HTML injection handling, repeat-run replacement, unrelated-file protection, and preservation of the last valid report on failure. No additional Python packages are required.

## Project Status

- Distribution: source repository and a bundled fictional demo.
- Primary host: Codex with local skill support.
- Report runtime: a modern browser with JavaScript enabled.
- Renderer: Python 3.9+, standard library only.
- Visual direction: Apple-inspired; this is an independent project.
- Reuse license: not selected. Public visibility alone does not specify reuse permissions.

## Acknowledgements

The evidence-first audit approach was informed by [ksimback/tech-debt-skill](https://github.com/ksimback/tech-debt-skill), and capability mapping by [Asixa/codemap-skill](https://github.com/Asixa/codemap-skill). This implementation follows a read-only workflow and produces HTML rather than a Markdown audit.

The README's presentation structure was inspired by [Zhijuan Prompt Card](https://github.com/papperrollinggery/zhijuan-prompt-card). Its product-specific content and visual assets are not included here.
