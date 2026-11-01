# OpenAPI: Pinned Contracts, Response Drift and Factual Limits

## Scope and prerequisites

Two isolated native protocol-services guests exchange real HTTP between CLIENT 198.18.0.2 and SERVER 198.18.0.1:8080. The fixed teaching OpenAPI 3.1.1 document declares GET /devices/{device_id}, a path parameter, a public classroom API-key header, documented status/media responses and local Device/Error schemas. The default Schema Object dialect is explicitly JSON Schema Draft 2020-12, as described in the [OpenAPI specification](https://spec.openapis.org/oas/v3.1.1.html). The client uses the actual [jsonschema validator/check_schema implementation](https://python-jsonschema.readthedocs.io/en/stable/validate/) for the selected component schema. This exercise is not a general OpenAPI document validator, all-version conformance test or Cisco product API.

The client carries its agreed contract snapshot and rejects a changed remote document before accepting a response or a schema reference. Only the fixed local component references are allowed; no remote reference or server-selected destination is fetched. HTTP 200 alone is insufficient: the documented response status, exact JSON media type, required fields/types and additional-property restrictions must all hold. Duplicate JSON fields, non-JSON numeric constants and oversized responses are rejected. The normal Device response reports the guest's actual eth1 carrier through its kernel sysfs file. It does not represent a physical router inventory.

An authorized GET establishes the baseline. Real missing-key 401, invalid-parameter 400 and missing-device 404 bodies must satisfy the declared error schema. An undocumented POST must actually return 405 with Allow: GET. Controlled faults then return a string instead of a boolean, an undeclared 201, an incorrect media type and a changed contract version; each must be rejected while independent ICMP remains usable, then recovered. Finally the source deliberately reports carrier false with otherwise valid structure. The validator must accept that schema-valid value, while an independent server sysfs read and actual packets prove the interface is up. This counterexample demonstrates that structural validation alone does not prove factual truth or provenance. Restore actual facts and recover the baseline.

The API key is an explicit public training fixture. HTTP is plaintext on a closed link; a pinned document hash is an agreed-byte comparison, not authenticated source identity or encryption. No device change, live vendor service, production credential, external connector or Internet reference is used. Native guests share their compute kernel. Only the imported copy may be stopped/wiped. Each protocol-services node budgets 1024MiB.


Use licensed reference images for cml-labs-services in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SERVER eth1 <-> CLIENT eth1

| Node | Interface | Address |
| --- | --- | --- |
| SERVER | eth1 / HTTP 8080 | 198.18.0.1/30 |
| CLIENT | eth1 | 198.18.0.2/30 |

## Tasks

1. Use a pinned operation contract plus actual JSON Schema validation on real HTTP responses.
2. Distinguish authentication/resource errors, schema drift, wrong media/status and contract changes from network loss.
3. Demonstrate why schema-valid data still needs independent factual and source evidence.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `python3 /lab/a.py baseline` | The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation. |
| CLIENT | `python3 /lab/a.py auth-errors` | The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation. |
| SERVER | `cat /sys/class/net/eth1/carrier` | An independent guest-kernel read observes actual carrier up, even during the schema-valid false API claim. |
| CLIENT | `ping -n -c 3 -W 2 198.18.0.1` | Independent IP reachability stays healthy during contract, status, media and schema faults. |

## Transition: return an invalid response field type

On **SERVER**:

```bash
python3 /lab/a.py schema
```

- CLIENT: `python3 /lab/a.py schema-bad` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- CLIENT: `ping -n -c 3 -W 2 198.18.0.1` -- Independent IP reachability stays healthy during contract, status, media and schema faults.
- SERVER: `cat /sys/class/net/eth1/carrier` -- An independent guest-kernel read observes actual carrier up, even during the schema-valid false API claim.

## Transition: recover after schema fault

On **SERVER**:

```bash
python3 /lab/a.py good
```

- CLIENT: `python3 /lab/a.py baseline` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- CLIENT: `ping -n -c 3 -W 2 198.18.0.1` -- Independent IP reachability stays healthy during contract, status, media and schema faults.

## Transition: return an undeclared response status

On **SERVER**:

```bash
python3 /lab/a.py status
```

- CLIENT: `python3 /lab/a.py status-bad` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- CLIENT: `ping -n -c 3 -W 2 198.18.0.1` -- Independent IP reachability stays healthy during contract, status, media and schema faults.
- SERVER: `cat /sys/class/net/eth1/carrier` -- An independent guest-kernel read observes actual carrier up, even during the schema-valid false API claim.

## Transition: recover after status fault

On **SERVER**:

```bash
python3 /lab/a.py good
```

- CLIENT: `python3 /lab/a.py baseline` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- CLIENT: `ping -n -c 3 -W 2 198.18.0.1` -- Independent IP reachability stays healthy during contract, status, media and schema faults.

## Transition: return an incorrect media type

On **SERVER**:

```bash
python3 /lab/a.py media
```

- CLIENT: `python3 /lab/a.py media-bad` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- CLIENT: `ping -n -c 3 -W 2 198.18.0.1` -- Independent IP reachability stays healthy during contract, status, media and schema faults.
- SERVER: `cat /sys/class/net/eth1/carrier` -- An independent guest-kernel read observes actual carrier up, even during the schema-valid false API claim.

## Transition: recover after media fault

On **SERVER**:

```bash
python3 /lab/a.py good
```

- CLIENT: `python3 /lab/a.py baseline` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- CLIENT: `ping -n -c 3 -W 2 198.18.0.1` -- Independent IP reachability stays healthy during contract, status, media and schema faults.

## Transition: change the remote agreed document

On **SERVER**:

```bash
python3 /lab/a.py contract
```

- CLIENT: `python3 /lab/a.py contract-bad` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- CLIENT: `ping -n -c 3 -W 2 198.18.0.1` -- Independent IP reachability stays healthy during contract, status, media and schema faults.
- SERVER: `cat /sys/class/net/eth1/carrier` -- An independent guest-kernel read observes actual carrier up, even during the schema-valid false API claim.

## Transition: recover after contract fault

On **SERVER**:

```bash
python3 /lab/a.py good
```

- CLIENT: `python3 /lab/a.py baseline` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- CLIENT: `ping -n -c 3 -W 2 198.18.0.1` -- Independent IP reachability stays healthy during contract, status, media and schema faults.

## Transition: demonstrate a schema-valid but factually false claim

On **SERVER**:

```bash
python3 /lab/a.py lie
```

- CLIENT: `python3 /lab/a.py semantic-lie` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- SERVER: `cat /sys/class/net/eth1/carrier` -- An independent guest-kernel read observes actual carrier up, even during the schema-valid false API claim.
- CLIENT: `ping -n -c 3 -W 2 198.18.0.1` -- Independent IP reachability stays healthy during contract, status, media and schema faults.

## Transition: restore actual interface facts

On **SERVER**:

```bash
python3 /lab/a.py good
```

- CLIENT: `python3 /lab/a.py baseline` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- CLIENT: `python3 /lab/a.py auth-errors` -- The actual HTTP response is classified against the pinned operation/status/media agreement and real Draft202012 schema validation.
- SERVER: `cat /sys/class/net/eth1/carrier` -- An independent guest-kernel read observes actual carrier up, even during the schema-valid false API claim.
- CLIENT: `ping -n -c 3 -W 2 198.18.0.1` -- Independent IP reachability stays healthy during contract, status, media and schema faults.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Inspectable contract, source and client

The [OpenAPI reference document, actual HTTP source, validator and acceptance probes](../../examples/automation/openapi_contract.py) are embedded unchanged. The [separate services image](../../services/README.md) supplies the real JSON Schema library. Inspect only this imported copy; the source has no production inventory or credential.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
