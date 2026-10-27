"""Validate topology references and build the public catalog without starting CML."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml
from acceptance import validate_plan

ROOT = Path(__file__).resolve().parents[1]
PHYSICAL = {
    "iosv": [f"GigabitEthernet0/{i}" for i in range(16)],
    "iosvl2": [f"GigabitEthernet{i // 4}/{i % 4}" for i in range(16)],
    "iol-xe": [f"Ethernet{i // 4}/{i % 4}" for i in range(32)],
    "ioll2-xe": [f"Ethernet{i // 4}/{i % 4}" for i in range(32)],
    "desktop": [f"eth{i}" for i in range(4)],
    "alpine": [f"eth{i}" for i in range(4)],
    "ubuntu": [f"ens{i}" for i in range(2, 10)],
    "csr1000v": [f"GigabitEthernet{i}" for i in range(1, 27)],
}
PHYSICAL.update(
    {
        kind: [f"eth{i}" for i in range(4)]
        for kind in ("net-tools", "radius", "syslog", "tacplus", "cml-labs-toolbox")
    }
)
RAM_MIB = {"iosv": 512, "iosvl2": 768, "desktop": 512, "alpine": 512, "ubuntu": 2048}
RAM_MIB.update({"iol-xe": 1024, "ioll2-xe": 1024, "cml-labs-toolbox": 1024})
RAM_MIB.update({"csr1000v": 3072, "net-tools": 512, "radius": 512, "syslog": 512, "tacplus": 512})


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def load(path):
    return yaml.load(Path(path).read_text(encoding="utf-8"), Loader=UniqueLoader)


def validate(data):
    errors = []
    if not isinstance(data, dict):
        return ["topology must be a mapping"]
    lab = data.get("lab", {})
    if not isinstance(lab, dict) or not all(
        isinstance(lab.get(k), str) and lab[k].strip()
        for k in ("title", "description", "notes", "version")
    ):
        errors.append("lab needs title, description, notes and format version")
    nodes = data.get("nodes")
    if isinstance(lab, dict) and isinstance(lab.get("title"), str) and len(lab["title"]) > 64:
        errors.append("CML lab title must be at most 64 characters")
    links = data.get("links")
    if not isinstance(nodes, list) or not nodes or not isinstance(links, list):
        return errors + ["nodes must be nonempty and links must be a list"]
    ids = set()
    labels = set()
    interfaces = {}
    for n in nodes:
        if not isinstance(n, dict):
            errors.append("node must be a mapping")
            continue
        nid = n.get("id")
        if not isinstance(nid, str) or nid in ids:
            errors.append(f"invalid/duplicate node id: {nid}")
        ids.add(nid)
        if not isinstance(n.get("label"), str) or n["label"] in labels:
            errors.append(f"invalid/duplicate label: {nid}")
        labels.add(n.get("label"))
        definition = n.get("node_definition")
        if definition not in PHYSICAL:
            errors.append(f"unsupported or external node type: {definition}")
        if n.get("image_definition"):
            errors.append(
                f"host-specific image pin: {nid}; use installed default or a private override"
            )
        if n.get("cpu_limit") is not None and not 1 <= n["cpu_limit"] <= 100:
            errors.append(f"invalid CPU limit: {nid}")
        cfg = n.get("configuration")
        if not isinstance(cfg, list) or any(
            not isinstance(x, dict)
            or not isinstance(x.get("name"), str)
            or not isinstance(x.get("content"), str)
            for x in cfg
        ):
            errors.append(f"configuration must be a list of named files: {nid}")
        ports = n.get("interfaces")
        if not isinstance(ports, list) or not ports:
            errors.append(f"missing interfaces: {nid}")
            ports = []
        interfaces[nid] = {}
        slots = set()
        for interface in ports:
            iid = interface.get("id")
            if not isinstance(iid, str) or iid in interfaces[nid]:
                errors.append(f"invalid/duplicate interface id: {nid}/{iid}")
            interfaces[nid][iid] = interface
            if interface.get("type") == "physical":
                slot = interface.get("slot")
                expected = PHYSICAL.get(definition, [])
                if type(slot) is not int or slot in slots or not 0 <= slot < len(expected):
                    errors.append(f"invalid/duplicate physical slot: {nid}/{iid}")
                elif interface.get("label") != expected[slot]:
                    errors.append(f"interface label does not match slot: {nid}/{iid}")
                slots.add(slot)
    link_ids = set()
    occupied = set()
    for link in links:
        if not isinstance(link, dict):
            errors.append("link must be a mapping")
            continue
        lid = link.get("id")
        if not isinstance(lid, str) or lid in link_ids:
            errors.append(f"invalid/duplicate link id: {lid}")
        link_ids.add(lid)
        endpoints = []
        for side in ("1", "2"):
            nid, iid = link.get("n" + side), link.get("i" + side)
            port = interfaces.get(nid, {}).get(iid) if isinstance(iid, str) else None
            if not port or port.get("type") != "physical":
                errors.append(f"unknown/nonphysical endpoint: {lid}/{nid}/{iid}")
            endpoint = (nid, iid)
            if endpoint in occupied:
                errors.append(f"interface used by multiple links: {nid}/{iid}")
            occupied.add(endpoint)
            endpoints.append(nid)
        if endpoints[0] == endpoints[1]:
            errors.append(f"self-link: {lid}")
    return errors


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def config_signature(nodes):
    return {
        n["label"]: [(f["name"], f["content"].rstrip("\r\n")) for f in n["configuration"]]
        for n in nodes
    }


def graph_signature(data):
    nodes = {n["id"]: n for n in data["nodes"]}
    ports = {(n["id"], i["id"]): i["label"] for n in data["nodes"] for i in n["interfaces"]}
    edges = []
    for link in data["links"]:
        endpoints = [
            (nodes[link["n" + s]]["label"], ports[link["n" + s], link["i" + s]]) for s in ("1", "2")
        ]
        edges.append(tuple(sorted(endpoints)))
    return sorted((n["label"], n["node_definition"]) for n in nodes.values()), sorted(edges)


def plan_digest(plan):
    return hashlib.sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def check_evidence(proof, path, expected_hash, phase, expected_plan_hash=None, expected_plan=None):
    """Reject stale hashes and a green status without successful acceptance checks."""
    errors = []
    if proof.get("sha256") != expected_hash:
        errors.append(f"{phase} evidence is stale after file change")
    if phase == "runtime" and proof.get("status") == "passed":
        checks = proof.get("checks", [])
        if not checks or any(x.get("passed") is not True for x in checks):
            errors.append("functional pass requires successful acceptance checks")
        if proof.get("test_lab_removed") is not True:
            errors.append("functional pass requires test-lab cleanup")
        if not proof.get("cml_version"):
            errors.append("functional pass requires the tested CML version")
        if expected_plan_hash and proof.get("plan_sha256") != expected_plan_hash:
            errors.append("acceptance plan changed; refresh or remove the functional evidence")
        if expected_plan is not None:
            from collections import Counter

            required = Counter(
                ("check", "baseline", c["node"], c["command"])
                for c in expected_plan.get("checks", [])
            )
            for step in expected_plan.get("transitions", []):
                required.update(
                    ("check", step["name"], c["node"], c["command"]) for c in step["checks"]
                )
                required.update(
                    ("action", step["name"], step["node"], command) for command in step["commands"]
                )
            observed = Counter(
                (
                    "action" if c.get("kind") in ("action", "configuration") else "check",
                    c.get("phase", "baseline"),
                    c.get("node"),
                    c.get("command"),
                )
                for c in checks
                if c.get("command") and c.get("passed") is True
            )
            if required - observed:
                errors.append("functional evidence omits planned checks or transitions")
    return [f"{path}: {e}" for e in errors]


def catalog(root=ROOT):
    curated = json.loads((root / "catalog/curated.json").read_text(encoding="utf-8"))
    evidence_path = root / "validation/runtime.json"
    evidence = (
        json.loads(evidence_path.read_text(encoding="utf-8"))
        if evidence_path.exists()
        else {"labs": []}
    )
    runtime = {r["path"]: r for r in evidence["labs"]}
    import_path = root / "validation/import.json"
    imported = (
        json.loads(import_path.read_text(encoding="utf-8"))
        if import_path.exists()
        else {"labs": []}
    )
    import_proofs = {r["path"]: r for r in imported["labs"]}
    plans = json.loads((root / "validation/checks.json").read_text(encoding="utf-8"))
    records = []
    failures = []
    for path in sorted((root / "labs").rglob("*.yaml")):
        relative = path.relative_to(root).as_posix()
        try:
            data = load(path)
            errors = validate(data)
        except (ValueError, yaml.YAMLError, TypeError, KeyError) as exc:
            failures.append(f"{relative}: {exc}")
            continue
        failures.extend(f"{relative}: {e}" for e in errors)
        info = curated.get(relative, {})
        proof = runtime.get(relative, {})
        if proof:
            failures.extend(
                check_evidence(
                    proof,
                    relative,
                    digest(path),
                    "runtime",
                    plan_digest(plans.get(relative, {})),
                    plans.get(relative, {}),
                )
            )
        import_proof = import_proofs.get(relative, {})
        if import_proof:
            failures.extend(check_evidence(import_proof, relative, digest(path), "import"))
        if proof.get("status") == "passed":
            actual = {(c.get("node"), c.get("command")) for c in proof.get("checks", [])}
            required = {
                (c["node"], c["command"]) for c in plans.get(relative, {}).get("checks", [])
            }
            if not required or not required.issubset(actual):
                failures.append(f"{relative}: evidence does not cover the acceptance plan")
        if relative in plans:
            labels = {n["label"] for n in data["nodes"]}
            failures.extend(
                f"{relative}: {error}" for error in validate_plan(plans[relative], labels)
            )
        records.append(
            {
                "path": relative,
                "title": data["lab"]["title"],
                "track": "-".join(path.relative_to(root / "labs").parts[0].split("-")[:2]),
                "topic": path.parent.name,
                "nodes": len(data["nodes"]),
                "node_types": sorted({n["node_definition"] for n in data["nodes"]}),
                "nominal_ram_mib": sum(
                    n.get("ram") or RAM_MIB[n["node_definition"]] for n in data["nodes"]
                ),
                "image_selection": "installed default; verify image availability before boot",
                "difficulty": info.get("difficulty", "Unrated"),
                "duration_minutes": info.get("duration_minutes"),
                "workbook": info.get("workbook"),
                "kind": info.get("kind", "scaffold"),
                "runtime_status": proof.get("status", "not-run"),
                "import_status": import_proof.get("status", "not-run"),
                "cml_version": proof.get("cml_version"),
                "validated_utc": proof.get("completed_utc"),
                "sha256": digest(path),
            }
        )
    paths = {r["path"] for r in records}
    for path, info in curated.items():
        if path not in paths:
            failures.append(f"orphan curated entry: {path}")
        if not (root / info["workbook"]).is_file():
            failures.append(f"missing workbook: {path}")
    for path in set(runtime) | set(import_proofs):
        if path not in paths:
            failures.append(f"orphan runtime evidence: {path}")
    if len(runtime) != len(evidence["labs"]) or len(import_proofs) != len(imported["labs"]):
        failures.append("duplicate evidence path")
    if set(plans) != set(curated):
        failures.append("acceptance plans must cover exactly the curated workbook paths")
    if failures:
        raise ValueError("\n".join(failures))
    return {"schema_version": 1, "lab_count": len(records), "labs": records}


def generated_files(root=ROOT):
    data = catalog(root)
    lines = [
        "# Lab catalog",
        "",
        "Generated from the topology files. Run `python scripts/labtools.py generate` after changes.",
        "",
        "RAM is the sum of node-definition defaults in MiB, excluding controller/host overhead and image overrides. It is not a measured peak.",
        "Node count alone does not imply CML Free compatibility: IOSv/IOSvL2 images require the appropriate entitlement.",
        "",
        "Status is deliberately separate from import validation. See [validation](../validation/README.md).",
        "",
        "| Lab | Track | Nodes | RAM MiB* | Type | Import/export | Runtime | Workbook |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for r in data["labs"]:
        wb = f"[Guide](../{r['workbook']})" if r["workbook"] else "—"
        lines.append(
            f"| [{r['title']}](../{r['path']}) | {r['track']} | {r['nodes']} | {r['nominal_ram_mib']} | {r['kind']} | {r['import_status']} | {r['runtime_status']} | {wb} |"
        )
    evidence_path = root / "validation/runtime.json"
    runtime = (
        json.loads(evidence_path.read_text(encoding="utf-8"))["labs"]
        if evidence_path.exists()
        else []
    )
    imported = sum(x["import_status"] == "import-export-pass" for x in data["labs"])
    titles = {x["path"]: x["title"] for x in data["labs"]}
    results = [
        "# Observed validation results",
        "",
        "Generated from the file-hash-checked evidence. CI checks these records; it does not boot CML.",
        "",
        f"Import/export passes: **{imported}/{data['lab_count']}**. Functional passes: **{sum(r['status'] == 'passed' for r in runtime)}**.",
        "",
        "[Raw import/export evidence](import.json) · [Raw functional evidence](runtime.json) · [Meaning and reproduction](README.md)",
        "",
        "| Exercise | Functional status | CML | Explicit image selections | Checks passed | Transition commands | Completed UTC |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in sorted(runtime, key=lambda r: r["path"]):
        images = (
            ", ".join(
                sorted(
                    {
                        image or "controller default (unresolved)"
                        for image in row.get("images", {}).values()
                    }
                )
            )
            or "—"
        )
        passed = sum(
            c.get("passed") is True and c.get("kind") not in ("action", "configuration")
            for c in row.get("checks", [])
        )
        actions = sum(
            c.get("passed") is True and c.get("kind") in ("action", "configuration")
            for c in row.get("checks", [])
        )
        results.append(
            f"| [{titles[row['path']]}](../{row['path']}) | {row['status']} | {row.get('cml_version', '—')} | {images} | {passed} | {actions} | {row.get('completed_utc', '—')} |"
        )
    results += [
        "",
        "All other exercises have no functional-validation claim. Read the workbooks and image requirements before starting them.",
        "",
    ]
    return {
        "catalog/labs.json": json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        "docs/CATALOG.md": "\n".join(lines) + "\n",
        "validation/RESULTS.md": "\n".join(results),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "generate", "check"])
    args = parser.parse_args()
    try:
        files = generated_files()
        if args.command == "generate":
            for name, text in files.items():
                p = ROOT / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8", newline="\n")
        elif args.command == "check":
            stale = [
                name
                for name, text in files.items()
                if not (ROOT / name).exists() or (ROOT / name).read_text(encoding="utf-8") != text
            ]
            if stale:
                raise ValueError("Generated catalog out of date: " + ", ".join(stale))
        print(
            f"OK: {len(list((ROOT / 'labs').rglob('*.yaml')))} topologies; references, interfaces, isolation and catalog checked"
        )
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
