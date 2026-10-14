#!/usr/bin/env python3
"""Validate audit data and render a portable, offline HTML report. Stdlib only."""

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


DIMENSIONS = {
    "Architecture", "Project structure", "Dependencies", "Separation of concerns",
    "Security", "Performance", "Testing", "Maintainability", "Deployment",
}
ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


class InvalidAudit(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidAudit(message)


def obj(value, where):
    require(isinstance(value, dict), f"{where}: expected an object")
    return value


def string(value, where):
    require(isinstance(value, str) and value.strip(), f"{where}: expected nonempty text")
    return value


def fields(value, names, where):
    obj(value, where)
    for name in names.split():
        string(value.get(name), f"{where}.{name}")


def items(value, where):
    require(isinstance(value, list), f"{where}: expected a list")
    return value


def strings(value, where):
    for i, entry in enumerate(items(value, where)):
        string(entry, f"{where}[{i}]")
    return value


def choice(value, allowed, where):
    require(isinstance(value, str) and value in allowed, f"{where}: expected one of {', '.join(sorted(allowed))}")


def path_string(value, where, allow_git=False):
    string(value, where)
    path = PurePosixPath(value)
    require("\\" not in value and ":" not in value and not path.is_absolute()
            and ".." not in path.parts and path.parts and (allow_git or path.parts[0] != ".git")
            and not any(ord(c) < 32 for c in value),
            f"{where}: use a repository-relative path without traversal or .git")
    return value


def collection(data, key):
    result = {}
    for i, value in enumerate(items(data.get(key), key)):
        obj(value, f"{key}[{i}]")
        identifier = value.get("id")
        require(isinstance(identifier, str) and ID.fullmatch(identifier), f"{key}[{i}]: invalid ID")
        require(identifier not in result, f"{key}: duplicate ID {identifier}")
        result[identifier] = value
    return result


def refs(value, allowed, where, nonempty=False):
    strings(value, where)
    require(not nonempty or value, f"{where}: at least one reference is required")
    require(len(value) == len(set(value)), f"{where}: duplicate references")
    require(all(v in allowed for v in value), f"{where}: unknown reference")


def validate(data, root=None):
    obj(data, "audit")
    require(type(data.get("schema_version")) is int and data["schema_version"] == 1, "schema_version must be 1")
    meta = obj(data.get("meta"), "meta")
    fields(meta, "project audited_at revision worktree scope", "meta")
    choice(meta.get("status"), {"complete", "partial"}, "meta.status")
    require(type(meta.get("is_demo")) is bool, "meta.is_demo must be a boolean")
    try:
        stamp = dt.datetime.fromisoformat(meta["audited_at"].replace("Z", "+00:00"))
        require(stamp.tzinfo is not None and stamp.utcoffset() is not None, "meta.audited_at needs a timezone")
    except ValueError as exc:
        raise InvalidAudit(f"meta.audited_at: invalid timestamp ({exc})") from exc
    if "repository_url" in meta:
        url = urlsplit(string(meta["repository_url"], "meta.repository_url"))
        require(url.scheme == "https" and url.hostname and not url.username and not url.password
                and not url.query and not url.fragment, "meta.repository_url must be a clean HTTPS URL")

    evidence_to_check = []

    def evidence(value, where, required=False):
        items(value, where)
        require(not required or value, f"{where}: evidence is required")
        for i, e in enumerate(value):
            loc = f"{where}[{i}]"
            obj(e, loc)
            path_string(e.get("path"), f"{loc}.path")
            string(e.get("note"), f"{loc}.note")
            start = e.get("line")
            end = e.get("end_line", start)
            require(type(start) is int and type(end) is int and 0 < start <= end,
                    f"{loc}: expected positive one-based line range")
            evidence_to_check.append((e["path"], start, end))

    layers = collection(data, "layers")
    require(layers, "layers: include at least one layer")
    for key, value in layers.items():
        fields(value, "label", f"layers.{key}")
    modules = collection(data, "modules")
    require(modules, "modules: include at least one module")
    for key, m in modules.items():
        where = f"modules.{key}"
        fields(m, "label layer type purpose business_role", where)
        require(m["layer"] in layers, f"{where}: unknown layer")
        choice(m.get("review_status"), {"reviewed", "sampled", "unreviewed"}, f"{where}.review_status")
        strings(m.get("paths"), f"{where}.paths")
        evidence(m.get("evidence"), f"{where}.evidence", m["review_status"] != "unreviewed")

    relationships = collection(data, "relationships")
    for key, edge in relationships.items():
        where = f"relationships.{key}"
        fields(edge, "source target label", where)
        require(edge["source"] in modules and edge["target"] in modules, f"{where}: unknown module")
        choice(edge.get("kind"), {"request", "data", "event", "dependency", "deployment"}, f"{where}.kind")
        choice(edge.get("confidence"), {"confirmed", "inferred"}, f"{where}.confidence")
        evidence(edge.get("evidence"), f"{where}.evidence", edge["confidence"] == "confirmed")

    journeys = collection(data, "journeys")
    for key, journey in journeys.items():
        where = f"journeys.{key}"
        fields(journey, "title description", where)
        steps = items(journey.get("steps"), f"{where}.steps")
        require(len(steps) >= 2, f"{where}: a journey needs at least two steps")
        for step in steps:
            fields(step, "module text", f"{where}.steps")
            require(step["module"] in modules, f"{where}: unknown step module")
        edge_ids = strings(journey.get("relationship_ids"), f"{where}.relationship_ids")
        require(len(edge_ids) == len(steps) - 1, f"{where}: one relationship per adjacent step is required")
        for i, edge_id in enumerate(edge_ids):
            require(edge_id in relationships, f"{where}: unknown relationship {edge_id}")
            edge = relationships[edge_id]
            require(edge["source"] == steps[i]["module"] and edge["target"] == steps[i + 1]["module"],
                    f"{where}: relationship direction does not match steps")

    findings = collection(data, "findings")
    for key, finding in findings.items():
        where = f"findings.{key}"
        fields(finding, "title category severity_reason description technical_impact business_impact recommendation verification", where)
        choice(finding.get("severity"), {"P0", "P1", "P2", "P3"}, f"{where}.severity")
        choice(finding.get("confidence"), {"confirmed", "potential"}, f"{where}.confidence")
        refs(finding.get("modules"), modules, f"{where}.modules", True)
        evidence(finding.get("evidence"), f"{where}.evidence", True)
        fields(finding.get("effort"), "range assumptions", f"{where}.effort")

    summary = obj(data.get("summary"), "summary")
    string(summary.get("verdict"), "summary.verdict")
    for name in ("executive", "architecture", "assumptions", "questions"):
        strings(summary.get(name), f"summary.{name}")
    refs(summary.get("priorities"), findings, "summary.priorities")
    for strength in items(summary.get("strengths"), "summary.strengths"):
        fields(strength, "description", "summary.strengths")
        evidence(strength.get("evidence"), "summary.strengths.evidence", True)

    roadmap = collection(data, "roadmap")
    seen_phases = set()
    assigned = []
    for key, phase in roadmap.items():
        where = f"roadmap.{key}"
        fields(phase, "title timing goal", where)
        refs(phase.get("finding_ids"), findings, f"{where}.finding_ids")
        refs(phase.get("dependencies"), seen_phases, f"{where}.dependencies")
        strings(phase.get("success_criteria"), f"{where}.success_criteria")
        require(phase["success_criteria"], f"{where}: include observable success criteria")
        assigned.extend(phase["finding_ids"])
        seen_phases.add(key)
    require(len(assigned) == len(set(assigned)) and set(assigned) == set(findings),
            "roadmap: assign every finding to exactly one phase")

    coverage = obj(data.get("coverage"), "coverage")
    files = items(coverage.get("files"), "coverage.files")
    require(type(coverage.get("inventory_count")) is int and coverage["inventory_count"] == len(files),
            "coverage.inventory_count must equal the number of inventoried files")
    paths = set()
    for file in files:
        fields(file, "path reason", "coverage.files")
        path_string(file["path"], "coverage.files.path")
        require(file["path"] not in paths, f"coverage.files: duplicate path {file['path']}")
        paths.add(file["path"])
        choice(file.get("status"), {"reviewed", "sampled", "unreviewed", "excluded"}, "coverage.files.status")
    for exclusion in items(coverage.get("exclusions"), "coverage.exclusions"):
        fields(exclusion, "path reason", "coverage.exclusions")
        path_string(exclusion["path"], "coverage.exclusions.path", allow_git=True)
    dimensions = items(coverage.get("dimensions"), "coverage.dimensions")
    names = []
    for dim in dimensions:
        fields(dim, "name summary", "coverage.dimensions")
        names.append(dim["name"])
        choice(dim.get("status"), {"reviewed", "partial", "not-assessed"}, "coverage.dimensions.status")
    require(DIMENSIONS <= set(names) and len(names) == len(set(names)),
            "coverage.dimensions: include all nine required dimensions without duplicates")
    for check in items(coverage.get("checks"), "coverage.checks"):
        fields(check, "name detail", "coverage.checks")
        choice(check.get("status"), {"passed", "failed", "not-run"}, "coverage.checks.status")
    strings(coverage.get("limitations"), "coverage.limitations")
    if meta["status"] == "complete":
        require(all(f["status"] in {"reviewed", "excluded"} for f in files)
                and all(m["review_status"] == "reviewed" for m in modules.values())
                and all(d["status"] == "reviewed" for d in dimensions),
                "meta.status cannot be complete while files, modules, or dimensions are partially/unreviewed")

    if root:
        root = Path(root).resolve()
        require(root.is_dir(), "--root must be a repository directory")
        line_counts = {}
        for path, start, end in evidence_to_check:
            resolved = (root / path).resolve()
            require(resolved.is_relative_to(root), f"Evidence escapes repository: {path}")
            require(resolved.is_file(), f"Evidence file does not exist: {path}")
            if path not in line_counts:
                line_counts[path] = len(resolved.read_text(encoding="utf-8", errors="replace").splitlines())
            require(end <= line_counts[path], f"Evidence lines {start}–{end} exceed {path} ({line_counts[path]} lines)")
    return data


def render(data):
    validate(data)
    template_path = Path(__file__).resolve().parent.parent / "assets" / "report.html"
    template = template_path.read_text(encoding="utf-8")
    require(template.count("__AUDIT_DATA__") == 1, "Report template must contain exactly one data placeholder")
    # JSON is inert inside a script element only when HTML raw-text delimiters are escaped.
    payload = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return template.replace("__AUDIT_DATA__", payload)


def write_report(output, html, data, force=False):
    """Refresh this project's existing report without truncating it on failure."""
    if output.exists() and not force:
        existing = output.read_text(encoding="utf-8")
        match = re.search(r'<script id="audit-data" type="application/json">(.*?)</script>', existing, re.DOTALL)
        require(match is not None, "Output exists and is not an audit report; refusing to overwrite it without --force")
        try:
            previous = json.loads(match.group(1))
            validate(previous)
        except (ValueError, TypeError) as exc:
            raise InvalidAudit("Existing output has invalid audit data; refusing to overwrite it without --force") from exc
        require(previous["meta"]["project"] == data["meta"]["project"],
                "Output belongs to another project; refusing to overwrite it without --force")
    output.parent.mkdir(parents=True, exist_ok=True)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=output.parent, prefix=f".{output.stem}-", suffix=".tmp",
                                         delete=False) as file:
            staged = Path(file.name)
            file.write(html)
            file.flush()
            os.fsync(file.fileno())
        os.replace(staged, output)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path, help="Read-only evidence file and line-range verification")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--force", action="store_true", help="Allow replacing unrelated HTML or another project's report; same-project audits update automatically")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        validate(data, args.root)
        if args.validate_only:
            print(f"Valid audit: {len(data['modules'])} modules, {len(data['findings'])} findings; coverage {data['meta']['status']}.")
            return 0
        require(args.output is not None, "--output is required unless --validate-only is used")
        output = args.output.resolve()
        require(output.suffix.lower() == ".html", "--output must end in .html")
        require(output != args.input.resolve(), "Input and output must differ")
        require(output != Path(__file__).resolve().parent.parent.joinpath("assets/report.html"), "Cannot overwrite the skill template")
        if args.root:
            require(not output.is_relative_to(args.root.resolve()), "Write the report outside --root to preserve the audited repository")
        html = render(data)
        write_report(output, html, data, args.force)
        print(f"Rendered {output} ({output.stat().st_size:,} bytes).")
        return 0
    except (InvalidAudit, OSError, ValueError, TypeError) as exc:
        print(f"Audit error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
