# Local CI/CD: Committed Policy, Test Gates and Real Deployment

## Scope and prerequisites

Three isolated guests implement a local Git-to-tested-policy-to-device pipeline. INSIDE has a real local Git repository containing only intent.json; no remote repository, GitHub credential, webhook or production runner is used. FW is an actual IOL-XE router enforcing the unchanged closed ACL compiler's output, and OUTSIDE has real application/admin HTTP listeners. The software publisher starts with a version-1 application-deny artifact, matching the router's initial deny behavior. The first committed candidate permits only the classroom application. These are public synthetic policy resources, not a general security policy language.

Each build requires a clean worktree, a literal committed Git object ID and one regular-mode source blob. It reads the committed bytes, not an unchecked worktree path, and runs eight fixed policy tests in a separate Python process. The candidate itself must satisfy the closed compiler, preserve admin denial/control and reject the fixed unsafe-field/type/scope examples. The accepted bundle binds the exact commit, source SHA-256, intent, complete compiled bytes and artifact SHA-256. These hashes provide consistency/provenance within the root-owned fixture, not a signature or protection from a compromised publisher/root user. The compiler and gate code are fixed reviewed inputs outside the candidate repository; untrusted candidate code is never executed. Git's SHA-1 object identifier is an opaque local revision identity here, not a cryptographic trust anchor.

Building does not publish, publishing does not deploy and a command echo does not establish forwarding. Root-only classroom promotion revalidates the full bundle against its committed source and requires the current clean HEAD. Staging a new deny commit must make the old build stale; an attempted promotion must be rejected with the complete old bundle and publication bytes unchanged. A new tested deny build can then be promoted. The router's real HTTP client separately fetches and merges the approved artifact. Actual client application HTTP must change only after that device step; administration remains denied, both local listeners stay available and independent routed ICMP remains healthy.

The first accepted allow bundle is retained for explicit rollback. Historical rollback verifies that bundle against its original committed bytes without rewriting Git history; actual traffic remains denied until the router applies it. A subsequently committed unsafe admin-allow request must make the actual gate process fail, preserving the previous bundle, published bytes and safe traffic. A final valid commit/build/promotion/device application restores the reference state. Gate success alone does not prove all possible flows or all policies; the fixed actual packet matrix supplies separate deployment evidence.

The unchanged publisher uses read-only plaintext HTTP on the closed link, and IOS merges fixed ACL sequences while the ACL stays defined. This is not an atomic commit, zero-loss change, signed supply chain, authenticated production approval system or hosted CI service. The immutable narrow TCP-return exception for the router-originated artifact fetch is not a stateful firewall. The lab has no Internet connector, external account, production secret or original user lab. Wiping only the imported copy removes its Git repository, artifacts and processes.


Use licensed reference images for cml-labs-toolbox, iol-xe, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- INSIDE eth1 <-> FW Ethernet0/0
- OUTSIDE eth1 <-> FW Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| FW | Ethernet0/0 | `ip address 198.18.10.1 255.255.255.0` |
| FW | Ethernet0/1 | `ip address 198.18.20.1 255.255.255.0` |
| INSIDE | eth1 | `198.18.10.10/24` |
| OUTSIDE | eth1 | `198.18.20.20/24` |

## Tasks

1. Build a deterministic guarded ACL artifact from actual committed Git bytes and a separate test process.
2. Reject stale promotion and unsafe source while distinguishing builds, publication and actual device deployment.
3. Roll back a verified historical artifact and require real packet-level recovery before declaring success.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| INSIDE | `python3 /lab/c.py build` | The actual fixed eight-test child process passes for the committed candidate without publishing it. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.20.20 --port 9090` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| INSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection is blocked while its separately checked server stays healthy. |
| INSIDE | `python3 /lab/t.py probe 198.18.20.20 --port 9090` | The actual plain-HTTP connection is blocked while its separately checked server stays healthy. |
| INSIDE | `ping -n -c 3 -W 2 198.18.20.20` | The routed ICMP control stays usable regardless of the staged or deployed application decision. |
| FW | `show ip interface Ethernet0/0` | The actual named client ingress policy remains bound. |

## Transition: promote the tested allow artifact without deploying it

On **INSIDE**:

```bash
python3 /lab/c.py promote
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: deploy the tested committed application permit

On **FW**:

```ios
copy http://198.18.10.10:8081/approved running-config
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: commit deny and reject the stale previous build

On **INSIDE**:

```bash
python3 /lab/c.py deny-stale
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: build the new deny commit without publishing it

On **INSIDE**:

```bash
python3 /lab/c.py build
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: publish the tested deny without changing device state

On **INSIDE**:

```bash
python3 /lab/c.py promote
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: apply the tested committed deny to the actual router

On **FW**:

```ios
copy http://198.18.10.10:8081/approved running-config
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: stage the verified historical allow rollback

On **INSIDE**:

```bash
python3 /lab/c.py rollback
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: apply rollback and verify actual service recovery

On **FW**:

```ios
copy http://198.18.10.10:8081/approved running-config
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: reject a committed unsafe admin permit in the gate process

On **INSIDE**:

```bash
python3 /lab/c.py unsafe
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: commit and test a new valid recovery intent

On **INSIDE**:

```bash
python3 /lab/c.py restore
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: promote the current clean tested recovery commit

On **INSIDE**:

```bash
python3 /lab/c.py promote
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: apply the final reference artifact and verify controls

On **FW**:

```ios
copy http://198.18.10.10:8081/approved running-config
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### FW

```ios
hostname FW
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
interface range Ethernet0/0 - 3
 no ip address
 shutdown
 exit
no logging console
file prompt quiet
ip http client source-interface Ethernet0/0
ip access-list extended POLICY-CODE
 5 permit tcp host 198.18.10.10 eq 8081 host 198.18.10.1 established
 10 deny tcp host 198.18.10.10 host 198.18.20.20 eq 8080
 20 deny tcp any host 198.18.20.20 eq 9090
 30 permit icmp any any
 40 deny ip any any
 exit
interface Ethernet0/0
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 ip access-group POLICY-CODE in
 exit
interface Ethernet0/1
 ip address 198.18.20.1 255.255.255.0
 no shutdown
 exit
end
```

### Inspectable local pipeline and compiler

The [Git/build/gate/provenance/promotion implementation](../../examples/automation/ci_pipeline.py) uses the unchanged [bounded ACL compiler and HTTP publisher](../../examples/security/policy_code.py). The [HTTP peer](../../examples/security/traffic_fixture.py) supplies independent application/admin controls. The fixture uses local Git only; host CI validates repository quality but does not substitute for these actual CML integrations.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
