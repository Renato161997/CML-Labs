# CML Labs

[![Lab quality](https://github.com/Renato161997/CML-Labs/actions/workflows/quality.yml/badge.svg)](https://github.com/Renato161997/CML-Labs/actions/workflows/quality.yml)

**233 Cisco Modeling Labs exercises, with a curated starting path and explicit validation levels.**

Practice enterprise routing, switching, security concepts and network automation.
Topology files and original teaching examples only: no vendor images, entitlement files or exam dumps.

**[Browse all labs](docs/CATALOG.md)** · **[Validation evidence](validation/README.md)** · **[Certification/image scope](docs/CERTIFICATIONS.md)** · **[Report a problem](https://github.com/Renato161997/CML-Labs/issues/new/choose)**

## Start here

Choose an exercise with a workbook, import its YAML and read the starting-state instructions before changing configuration. Some are working reference baselines; the OSPF troubleshooting exercise is deliberately broken.

| Workbook | What you can observe |
| --- | --- |
| [Single-area OSPF](docs/workbooks/017-single-area-ospfv2.md) | FULL adjacency, learned loopbacks and sourced ping |
| [OSPF troubleshooting](docs/workbooks/018-ospfv2-neighbor-troubleshooting.md) | Area mismatch, diagnosis, repair and recovery |
| [Router on a stick](docs/workbooks/007-vlan-router-on-a-stick.md) | 802.1Q trunk and two VLAN subinterfaces |
| [STP root selection](docs/workbooks/009-stp-root-selection.md) | Root bridge, root port and alternate blocking path |
| [NAT/PAT edge](docs/workbooks/024-nat-pat-edge.md) | Translation hits and return traffic without a private-subnet route |
| [Extended ACLs](docs/workbooks/032-standard-extended-acls.md) | A specific blocked flow, an allowed flow and deny counters |
| [eBGP neighbors](docs/workbooks/013-ibgp-ebgp-neighbors.md) | Received prefix, AS path and loopback connectivity |
| [BGP path selection](docs/workbooks/014-bgp-path-selection-local-pref-med.md) | Two competing paths and local-preference selection |
| [Webhook receiver](docs/workbooks/011-webhook-receiver.md) | Authenticated HTTP requests, duplicate events and safe rejection |
| [Intent validation](docs/workbooks/035-webhook-receiver-config-validation.md) | Device/interface allowlists, strict types and an approval boundary |

The catalog separates **curated practice/break-fix** entries from **scaffolds**. A scaffold is a starting topology and exercise outline, not a complete workbook or a claim that every technology in its title is implemented. Functional status is attached to a dated file hash and the actual tested CML/images.

## Import and run

1. Download or clone this repository.
2. Check node types, memory estimate, image availability and license requirements in the catalog/workbook.
3. In CML, import the selected `.yaml` from `labs/`.
4. Start the isolated lab and wait for the startup configuration to finish applying; IOS images can take several minutes before their CLI is ready.
5. Follow the workbook and acceptance checks. Stop/wipe only your exercise when resetting it.

The normalized format targets **CML 2.10.1**, using named configuration files and explicit interface IDs. Older releases have not been certified. The files use installed default images; no host-specific image IDs are required.

**Keep these exercises isolated.** Do not attach an external connector to your home/work network. Demo access and console settings are designed for disposable practice. CML Free's node limit alone does not establish image compatibility or entitlement.

## Tracks

| Track | Exercises | Scope |
| --- | ---: | --- |
| 200-301 CCNA | 50 | Fundamentals, switching, routing and services |
| 350-401 ENCOR | 51 | Enterprise core scenarios |
| 300-410 ENARSI | 46 | Advanced routing and troubleshooting |
| 350-701 SCOR | 46 | Security concepts and network scenarios |
| 350-901 DEVCOR | 40 | **Legacy:** retained paths; see the current AUTOCOR mapping |

Cisco's 2026 Automation changes include revised content. Legacy DEVCOR exercises are not complete AUTOCOR coverage. [Read the mapping and limitations](docs/CERTIFICATIONS.md).

## Searchable local catalog

The HTML catalog filters by track, topic, node count, difficulty and functional status. It runs locally and sends no telemetry:

```sh
python -m http.server 8000 --bind 127.0.0.1
# Open http://127.0.0.1:8000/docs/catalog.html
```

## Quality and contribution

```sh
python -m pip install -r requirements-dev.txt
ruff check scripts tests examples
ruff format --check scripts tests examples
python scripts/labtools.py generate
python scripts/labtools.py check
python scripts/embed_webhook.py --check
python -m unittest discover -s tests -v
```

CI checks YAML, topology references, interface slots, isolation constraints, catalog freshness and real HTTP example tests. It does not connect to CML. [Live validation](validation/README.md) is a separate, opt-in operation. See [CONTRIBUTING.md](CONTRIBUTING.md) for reproducible bug reports and changes.

## Disclaimer and licensing

This is an independent practice collection. Cisco, CML, IOS, IOS-XE and related names belong to their respective owners. It is not official courseware or an exam-coverage guarantee. Vendor software must be obtained under the user's own entitlement. An explicit license for this repository's original material still requires a maintainer decision; public visibility is not a substitute for one.
