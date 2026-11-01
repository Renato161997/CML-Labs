# Policy as Code: Guarded Artifacts, Real Deployment and Rollback

## Scope and prerequisites

A native publisher compiles a deliberately closed JSON classroom intent into an actual IOS ACL merge artifact. Its only resources are source 198.18.10.10/32, service 198.18.20.20/32, application TCP 8080 and administration-port fixture TCP 9090. It accepts application allow/deny but always denies administration and preserves ICMP. Extra fields, command injection, changed resources, noninteger/out-of-range versions and an administration allow are rejected before publication. Every rejected example must leave the complete previously approved artifact bytes unchanged. This is a finite teaching compiler, not a general policy language or universal security validator.

The initial published version 1 allows the application, but the actual router reference starts with application deny. This intentionally distinguishes staged desired state from deployed running state. The router's real HTTP client fetches the complete artifact from INSIDE 198.18.10.10:8081/approved and merges it into its actual running configuration. Four fixed ACL sequences are explicitly deleted/re-added while the ACL stays defined; this is not an atomic transactional device commit or a zero-loss change. Sequence 5 is a separate immutable, narrowly scoped stateless TCP-return exception for that router-originated artifact download. It is not identity authentication or a stateful firewall. No other client/admin permit is implied.

After applying version 1, actual remote application HTTP must work with the observed client peer while the remote administration request remains blocked. Both local service listeners and three routed ICMP replies remain positive controls. Publish version 2 with application deny: running traffic must remain allowed until the router actually downloads/applies it. After real deployment the application must fail while administration stays blocked and controls remain healthy. Publish the previously stored accepted version-1 snapshot: traffic must remain blocked until the rollback is actually applied; then recover the original allow/deny matrix. Rejected unsafe intent must never alter the published artifact or deployed behavior.

State stores intent, complete bytes and SHA256; every served artifact must match its validated intent and digest. This is representation consistency, not a digital signature. The HTTP path is read-only and intentionally plaintext inside an isolated link. CLI root fixture actions stage the two accepted intents; there is no authenticated production approval interface, signed supply chain, remote secret, cloud service, real CI deployment, vendor firewall manager or formal all-flow equivalence claim. No Internet connector or original user lab is touched. Only the imported copy may be stopped/wiped.


Use licensed reference images for iol-xe, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

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

1. Reject unsafe or out-of-scope desired intent before changing the published artifact.
2. Distinguish staged desired state from actual IOS configuration and actual service packets.
3. Perform real HTTP artifact deployment and rollback, preserving administration denial and independent controls.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| OUTSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.20.20 --port 9090` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| INSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection is blocked while its separately checked server stays healthy. |
| INSIDE | `python3 /lab/t.py probe 198.18.20.20 --port 9090` | The actual plain-HTTP connection is blocked while its separately checked server stays healthy. |
| INSIDE | `ping -n -c 3 -W 2 198.18.20.20` | The routed ICMP control stays usable regardless of the staged or deployed application decision. |
| FW | `show ip interface Ethernet0/0` | The actual named client ingress policy remains bound. |

## Transition: reject unsafe candidates before any deployment

On **INSIDE**:

```ios
python3 /lab/p.py reject-unsafe
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: deploy the accepted version-1 application permit

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

## Transition: stage version-2 application deny without deploying it

On **INSIDE**:

```ios
python3 /lab/p.py block
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: deploy the actual application-deny change

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

## Transition: stage the saved version-1 rollback without deploying it

On **INSIDE**:

```ios
python3 /lab/p.py rollback
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- The routed ICMP control stays usable regardless of the staged or deployed application decision.
- FW: `show ip interface Ethernet0/0` -- The actual named client ingress policy remains bound.

## Transition: apply the accepted prior snapshot and recover packets

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

## Transition: reject unsafe candidates while safe traffic remains deployed

On **INSIDE**:

```ios
python3 /lab/p.py reject-unsafe
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

### Inspectable policy and packet implementations

The [closed compiler and staged artifact publisher](../../examples/security/policy_code.py) run on INSIDE. The [unchanged HTTP peer fixture](../../examples/security/traffic_fixture.py) supplies real packet observations and local service controls. Inspect the startup files in the YAML for the full native bootstrap. No copy success message alone establishes policy correctness: repeat the independent application/admin/ICMP matrix.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
