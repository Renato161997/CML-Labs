# DNS Security Concepts: Policy, Bypass and Unavailability

## Scope and prerequisites

Two isolated automation-toolbox guests exchange actual DNS on UDP and TCP port 53. The native fixture uses the header/question/A-record framing from [RFC 1035](https://www.rfc-editor.org/rfc/rfc1035.html); the installed independent BIND dig client constructs queries and interprets responses. The server never performs recursive queries, contacts an upstream resolver or accepts an arbitrary forwarded destination. Its closed hostname profile contains allowed.lab.example and blocked.lab.example, both synthetic classroom names. It returns only one fixed benchmark IPv4 address with zero TTL, or the explicitly tested error status. Compressed questions, EDNS, extra records, nonstandard opcodes and malformed packets are outside this bounded teaching profile and receive FORMERR. Unsupported type/class receives NOTIMP; unknown names receive REFUSED. This is not a general DNS server or standards conformance suite.

In enforce mode the allowed name must produce its exact IN A answer and the blocked name must produce NXDOMAIN with no answer, independently over UDP and TCP. Deliberately bypassing only the local block policy must let that previously blocked name resolve; restoring enforcement must recover denial. A controlled unavailable-policy mode returns actual SERVFAIL for both known names while unknown names remain REFUSED. SERVFAIL is not a timeout or NXDOMAIN, and no stale successful address is fabricated. Restoring the policy must recover legitimate resolution and intentional blocking. This is a local response-policy exercise, not a test of Cisco Umbrella, reputation/category intelligence, a commercial tenant or a cloud API.

Independent ICMP and both local and remote HTTP controls must remain healthy through every DNS change. In particular, a direct-IP HTTP request still succeeds while name policy blocks the corresponding synthetic name. DNS filtering alone is not packet access control: this topology does not force endpoints to use the resolver, prevent alternate DNS/DoH or prohibit known-IP access. It makes no phishing, malware, browser or TLS-inspection claim. No resolv.conf, host OS DNS, production network, licensed vendor image, paid account, real credential or external connector is changed. Wiping the disposable copy removes the fixture state and listeners.


Use licensed reference images for cml-labs-toolbox in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- DNS eth1 <-> CLIENT eth1

| Node | Interface | Address |
| --- | --- | --- |
| DNS | eth1 | `198.18.0.1/30` |
| CLIENT | eth1 | `198.18.0.2/30` |

## Tasks

1. Observe real allowed, policy-denied, refused and unsupported DNS responses over both UDP and TCP.
2. Detect deliberate policy bypass and distinguish DNS unavailability from an intentional domain block.
3. Recover filtering with independent IP/service controls and demonstrate the boundary of DNS-only enforcement.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `python3 /lab/d.py probe-enforce` | The real dig client must observe all eight expected DNS response outcomes over UDP and TCP; no answer, refusal, policy denial and unavailability have distinct statuses. |
| CLIENT | `ping -n -c 3 -W 1 198.18.0.1` | The guest and IP path remain healthy independently of DNS policy. |
| DNS | `python3 /lab/t.py probe 198.18.0.1` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| CLIENT | `python3 /lab/t.py probe 198.18.0.1` | The actual plain-HTTP connection succeeds with the expected observed peer. |

## Transition: observe removal of only the domain block

On **DNS**:

```bash
python3 /lab/d.py bypass
```

- CLIENT: `python3 /lab/d.py probe-bypass` -- The real dig client must observe all eight expected DNS response outcomes over UDP and TCP; no answer, refusal, policy denial and unavailability have distinct statuses.
- CLIENT: `ping -n -c 3 -W 1 198.18.0.1` -- The guest and IP path remain healthy independently of DNS policy.
- DNS: `python3 /lab/t.py probe 198.18.0.1` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- CLIENT: `python3 /lab/t.py probe 198.18.0.1` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Transition: restore explicit DNS denial

On **DNS**:

```bash
python3 /lab/d.py enforce
```

- CLIENT: `python3 /lab/d.py probe-recovered` -- The real dig client must observe all eight expected DNS response outcomes over UDP and TCP; no answer, refusal, policy denial and unavailability have distinct statuses.
- CLIENT: `ping -n -c 3 -W 1 198.18.0.1` -- The guest and IP path remain healthy independently of DNS policy.
- DNS: `python3 /lab/t.py probe 198.18.0.1` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- CLIENT: `python3 /lab/t.py probe 198.18.0.1` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Transition: distinguish policy service unavailability

On **DNS**:

```bash
python3 /lab/d.py unavailable
```

- CLIENT: `python3 /lab/d.py probe-unavailable` -- The real dig client must observe all eight expected DNS response outcomes over UDP and TCP; no answer, refusal, policy denial and unavailability have distinct statuses.
- CLIENT: `ping -n -c 3 -W 1 198.18.0.1` -- The guest and IP path remain healthy independently of DNS policy.
- DNS: `python3 /lab/t.py probe 198.18.0.1` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- CLIENT: `python3 /lab/t.py probe 198.18.0.1` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Transition: recover legitimate resolution and domain denial

On **DNS**:

```bash
python3 /lab/d.py enforce
```

- CLIENT: `python3 /lab/d.py probe-recovered` -- The real dig client must observe all eight expected DNS response outcomes over UDP and TCP; no answer, refusal, policy denial and unavailability have distinct statuses.
- CLIENT: `ping -n -c 3 -W 1 198.18.0.1` -- The guest and IP path remain healthy independently of DNS policy.
- DNS: `python3 /lab/t.py probe 198.18.0.1` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- CLIENT: `python3 /lab/t.py probe 198.18.0.1` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Inspectable DNS policy fixture

The [closed DNS server and dig-based checks](../../examples/security/dns_policy.py) expose the exact supported wire/policy profile. The unchanged [HTTP peer](../../examples/security/traffic_fixture.py) provides an independent service control. A policy file change is not acceptance: remote dig responses and actual IP/HTTP checks must all satisfy the documented phase.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
