# Indicator Feed: Revalidation, Revocation and Cache Integrity

## Scope and prerequisites

Two actual isolated native Linux nodes exchange real HTTP on SOURCE 198.18.0.1:8080 and ANALYST 198.18.0.2. The source publishes five explicitly synthetic benchmark IPv4 indicators in a deliberately closed JSON/indicator exercise profile. Only literal IPv4 equality patterns are supported; this is not a conforming STIX/TAXII implementation, a general STIX parser, a vendor feed or live threat intelligence. Public fixture UUIDs are intentionally fixed. No actual malicious content, real-world IOC, production credential, external connector or Internet feed is involved.

The field conventions are derived from the [OASIS STIX 2.1 indicator/common-property definitions](https://docs.oasis-open.org/cti/stix/v2.1/os/stix-v2.1-os.html). Producer confidence is bounded 0..100; the exercise chooses 70 as its alert threshold, not a probability or verified truth. A match also requires a supported literal pattern, current validity and no revocation. Missing confidence is unspecified. Separate low-confidence, expired, revoked and future-valid indicators must not match. The first indicator matches only until the source explicitly revokes it. Validity windows are one hour from initial fixture configuration; use a fresh imported copy if teaching is paused beyond that window.

The analyst obtains a real initial 200 representation and uses its actual strong SHA256 ETag for conditional revalidation. An unchanged representation produces a real HTTP 304. Cached bytes must still match that tag and pass the closed profile before use. Revalidation proves communication and representation consistency, not source authentication, producer publication freshness or the accuracy of the intelligence. Isolated plaintext HTTP is not an Internet-ready secure feed transport.

Controlled source 503 returns unknown despite a previously matched cached indicator. A separate source fault returns HTTP 200 with an invalid confidence field; transport success must still produce unknown and preserve the last valid cache. Three independent ICMP replies remain available during both source faults. Restore a valid response and recover a verified match. Publish revocation, observe a different ETag and a fresh 200, and require no match; no match does not establish benignness. Finally alter only local cached body bytes without updating their tag. The client must detect this mismatch, omit the unusable conditional tag, obtain a real 200, validate and replace the cache, and retain the observed revoked/no-match state. There is no automated firewall change, commercial integration, TLS-origin proof or malware classification claim.


Use licensed reference images for net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SOURCE eth1 <-> ANALYST eth1

| Node | Interface | Address |
| --- | --- | --- |
| SOURCE | eth1/feed HTTP 8080 | 198.18.0.1/30 |
| ANALYST | eth1/source client | 198.18.0.2/30 |

## Tasks

1. Enrich a synthetic IPv4 observation only from a successfully revalidated and structurally accepted source representation.
2. Exclude low-confidence, expired, revoked and future-valid indicators; distinguish no match from unknown and from benign.
3. Exercise actual 200/304/503 transitions, invalid content and cache corruption without promoting stale evidence.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| ANALYST | `ping -n -c 3 -W 2 198.18.0.1` | All three independent packets reach the source even while its feed is unavailable or invalid. |
| ANALYST | `python3 /lab/ti.py baseline` | Observe a real source HTTP response and validate the bounded indicator/cache profile; uncertainty is never converted into a clean verdict. |
| ANALYST | `python3 /lab/ti.py cached` | Observe a real source HTTP response and validate the bounded indicator/cache profile; uncertainty is never converted into a clean verdict. |

## Transition: make only the feed temporarily unavailable

On **SOURCE**:

```ios
python3 /lab/ti.py unavailable
```

- ANALYST: `python3 /lab/ti.py offline` -- Observe a real source HTTP response and validate the bounded indicator/cache profile; uncertainty is never converted into a clean verdict.
- ANALYST: `ping -n -c 3 -W 2 198.18.0.1` -- All three independent packets reach the source even while its feed is unavailable or invalid.

## Transition: recover the valid matching representation

On **SOURCE**:

```ios
python3 /lab/ti.py healthy
```

- ANALYST: `python3 /lab/ti.py recovered` -- Observe a real source HTTP response and validate the bounded indicator/cache profile; uncertainty is never converted into a clean verdict.
- ANALYST: `ping -n -c 3 -W 2 198.18.0.1` -- All three independent packets reach the source even while its feed is unavailable or invalid.

## Transition: publish invalid content with HTTP 200

On **SOURCE**:

```ios
python3 /lab/ti.py malformed
```

- ANALYST: `python3 /lab/ti.py invalid-feed` -- Observe a real source HTTP response and validate the bounded indicator/cache profile; uncertainty is never converted into a clean verdict.
- ANALYST: `ping -n -c 3 -W 2 198.18.0.1` -- All three independent packets reach the source even while its feed is unavailable or invalid.

## Transition: recover structurally accepted content

On **SOURCE**:

```ios
python3 /lab/ti.py healthy
```

- ANALYST: `python3 /lab/ti.py recovered` -- Observe a real source HTTP response and validate the bounded indicator/cache profile; uncertainty is never converted into a clean verdict.

## Transition: publish an explicit revocation

On **SOURCE**:

```ios
python3 /lab/ti.py withdraw
```

- ANALYST: `python3 /lab/ti.py withdrawn` -- Observe a real source HTTP response and validate the bounded indicator/cache profile; uncertainty is never converted into a clean verdict.
- ANALYST: `ping -n -c 3 -W 2 198.18.0.1` -- All three independent packets reach the source even while its feed is unavailable or invalid.

## Transition: detect locally corrupted cache and fetch a full representation

On **ANALYST**:

```ios
python3 /lab/ti.py corrupt-cache
```

- ANALYST: `python3 /lab/ti.py cached-withdrawn` -- Observe a real source HTTP response and validate the bounded indicator/cache profile; uncertainty is never converted into a clean verdict.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Inspectable indicator and cache implementation

The [closed-profile parser, actual HTTP source, conditional client and probes](../../examples/security/intel_fixture.py) are embedded unchanged on both nodes. SOURCE owns only this synthetic feed. ANALYST caches only accepted bytes and rejects uncertainty as actionable evidence. All state and server processes disappear when your imported copy is wiped.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
