# Dockerized Tool: Artifact Provenance and Runtime Contract

## Scope and prerequisites

Two actual CML Docker protocol-services guests use the immutable separately published OCI image and their registered configuration payloads. SERVER 198.18.0.1:8080 is the unchanged OpenAPI/JSON-Schema teaching endpoint; CLIENT 198.18.0.2 first performs root-only network/bootstrap setup, then starts a separate short-lived Python HTTP workload with actual UID/GID 65534, no supplementary groups, no effective/permitted/inheritable/ambient capabilities and kernel no-new-privileges set before exec. The child reads its own real /proc/self/status and must be unable to regain UID zero. It still performs actual authenticated HTTP and pinned contract/schema validation, creates a mode-0600 result owned by that UID, reads it back and removes it before exiting. The parent observes the completed child and a PID different from its own. Kernel SYS_ADMIN must be absent in the bootstrap container too. This is a finite measured privilege profile, not a general container-escape or host-boundary proof.

The only image bind is the existing declared CML boot configuration; there is no nested Docker daemon, host-network mode, extra host mount, paid service or production credential. The classroom API key is deliberately public source, not a secret protected by this exercise. The root-only file is an explicitly PUBLIC permission-test sentinel, never a real key. Actual UID-65534 reads must fail in the secure mode and succeed only after the controlled root chmod-0644 fault; restoring chmod-0600 must deny reads again without breaking legitimate API requests. These file tests do not protect data from container root. HTTP is plaintext on closed lab links, not an Internet deployment pattern. Every file/process disappears when the imported copy is wiped.

The [separate services image build](../../services/README.md) records real OCI config digest, source revision and Debian package inventory. CML's registered Docker kind plus the actual guest observations support the runtime claim; a copied Docker marker alone is not an isolation assessment. The exercise does not run docker build inside a privileged nested guest or claim a container power-cycle. Source-contract faults are rejected by the unchanged real JSON Schema client while independent kernel carrier and ICMP stay healthy. Container/UID success and API semantic success are separate observations.


Use licensed reference images for cml-labs-services in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SERVER eth1 <-> CLIENT eth1

| Node | Interface | Address |
| --- | --- | --- |
| SERVER | eth1 / HTTP 8080 | 198.18.0.1/30 |
| CLIENT | eth1 | 198.18.0.2/30 |

## Tasks

1. Connect the actual immutable Docker artifact, registered payload and independently measured guest runtime.
2. Observe a genuinely unprivileged API workload, denied root regain and scoped file-permission outcomes.
3. Reject actual source/authorization faults without mistaking container liveness for API correctness, then recover.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `python3 /lab/u.py baseline` | Require actual Docker guest, kernel UID/GID/capability/NNP measurements in a separate exited workload, denied UID-zero regain, actual sentinel-file read result, owned output cleanup and the specified real API result. |
| CLIENT | `python3 /lab/a.py baseline` | The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation. |
| SERVER | `cat /sys/class/net/eth1/carrier` | An independent guest-kernel read observes actual carrier up, even during the schema-valid false API claim. |
| CLIENT | `ping -n -c 3 -W 2 198.18.0.1` | Independent IP reachability stays healthy during contract, status, media and schema faults. |
| CLIENT | `stat -c "%a %u" /lab/root-only.fixture` | Independently observe root ownership and actual sentinel-file permission mode. |

## Transition: produce a schema-invalid response without breaking the container link

On **SERVER**:

```bash
python3 /lab/a.py schema
```

- CLIENT: `python3 /lab/u.py schema` -- Require actual Docker guest, kernel UID/GID/capability/NNP measurements in a separate exited workload, denied UID-zero regain, actual sentinel-file read result, owned output cleanup and the specified real API result.
- CLIENT: `python3 /lab/a.py schema-bad` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- SERVER: `cat /sys/class/net/eth1/carrier` -- An independent guest-kernel read observes actual carrier up, even during the schema-valid false API claim.
- CLIENT: `ping -n -c 3 -W 2 198.18.0.1` -- Independent IP reachability stays healthy during contract, status, media and schema faults.

## Transition: restore the contract and run fresh stateless workloads

On **SERVER**:

```bash
python3 /lab/a.py good
```

- CLIENT: `python3 /lab/u.py baseline` -- Require actual Docker guest, kernel UID/GID/capability/NNP measurements in a separate exited workload, denied UID-zero regain, actual sentinel-file read result, owned output cleanup and the specified real API result.
- CLIENT: `python3 /lab/u.py baseline` -- Require actual Docker guest, kernel UID/GID/capability/NNP measurements in a separate exited workload, denied UID-zero regain, actual sentinel-file read result, owned output cleanup and the specified real API result.
- CLIENT: `python3 /lab/a.py baseline` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- CLIENT: `ping -n -c 3 -W 2 198.18.0.1` -- Independent IP reachability stays healthy during contract, status, media and schema faults.

## Transition: verify real API refusal with the workload still unprivileged

On **CLIENT**:

```bash
python3 /lab/u.py no-key
```

- CLIENT: `python3 /lab/u.py baseline` -- Require actual Docker guest, kernel UID/GID/capability/NNP measurements in a separate exited workload, denied UID-zero regain, actual sentinel-file read result, owned output cleanup and the specified real API result.
- CLIENT: `python3 /lab/a.py baseline` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- CLIENT: `stat -c "%a %u" /lab/root-only.fixture` -- Independently observe root ownership and actual sentinel-file permission mode.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Inspectable workload and source

The [runtime privilege/workload implementation](../../examples/automation/container_tool.py) uses the unchanged [actual API/contract implementation](../../examples/automation/openapi_contract.py). Root bootstrap is distinct from the measured nonroot child; the sentinel and classroom key are public fixtures. Inspect only the owned copy, and never substitute static UID/configuration strings for actual kernel/process/file/HTTP evidence.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
