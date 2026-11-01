# Event Automation: Gateway Restart and Retry-Safe Jobs

## Scope and prerequisites

A separate native publisher sends actual HTTP event deliveries to a fixture gateway on TOOLS 198.18.1.1:8081. The gateway verifies a bounded UTF8 JSON body, exactly one SHA256 HMAC signature header, exact fields/scalar types, integer timestamp within 60seconds and the fixed business-event/resource allowlist. Duplicate JSON fields and ambiguous HTTP lengths/types/signatures are rejected. The only mappings are quarantine/withdraw-1 -> remove 192.0.2.42/32, and release/repair-1 -> restore that same route through 198.18.0.2. No freeform commands, destinations, URLs or client-provided approval are forwarded.

Accepted events call the unchanged controller northbound API; its separate root-owned exact-intent approval policy still applies. Its actual RESTCONF facts, key-pinned NETCONF device changes, readback and durable SQLite lifecycle record are independent of the event signature. The initial seed submits the already approved install-1 through that real controller, then independent CSR RIB and ICMP probes establish a usable initial route. Invalid signed/unsigned event cases must leave the complete device-job history unchanged and preserve actual route/facts.

Withdrawal must genuinely remove the CSR host route and stop its service-loopback packets while connected management remains reachable. Two concurrent freshly signed redeliveries of the same committed business ID must both be reported as replays without another write or history event. The publisher preserves the business ID and refreshes its signed transport timestamp; an expired original body is rejected rather than silently exempted from freshness checks. A signed release must create exactly one additional successful job, restore the route and recover actual ICMP.

The signature key and backend bearer token are explicitly public classroom fixtures. Northbound HTTP is plaintext on isolated links; this is not a secure Internet webhook product, encryption/confidentiality, a real external detector, a commercial SOAR/controller API, an end-user identity workflow or a distributed exactly-once guarantee. Approval changes are controlled root CLI fixture actions, not a human ticket system. CLIENT also holds the public operator fixture to seed/read the teaching controller for acceptance; no publisher/operator network trust separation is inferred. Only committed replay and the explicitly tested failure windows are claimed. Backend management uses real certificate/key verification. No production credential, cloud service, Internet connector, malware or existing user lab is used. Nominal RAM 4608MiB requires one explicitly selected reserved larger-case run.


After an actual committed route withdrawal, stop only the frontend event gateway. Its TCP listener must refuse connections while the original controller PID, complete committed history, withdrawn RIB and connected device-management path remain unchanged. Restart the frontend with a genuinely different PID. Freshly signed redeliveries retain their committed business ID and must not create another job/history event or device write. A signed release recovers the route and actual packets. There is no claim about interruption during an uncommitted write or a distributed message queue.

Use licensed reference images for cml-labs-toolbox, csr1000v, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- API GigabitEthernet1 <-> TOOLS eth1
- TOOLS eth2 <-> CLIENT eth1

| Node | Interface | Address |
| --- | --- | --- |
| API | GigabitEthernet1 | 198.18.0.1/30 |
| TOOLS | eth1 device-facing | 198.18.0.2/30 |
| TOOLS | eth2 northbound | 198.18.1.1/30 |
| TOOLS | lo service target | 192.0.2.42/32 |
| CLIENT | eth1 publisher | 198.18.1.2/30 |
| API | GigabitEthernet1 | `ip address 198.18.0.1 255.255.255.252` |
| TOOLS | eth1 | `198.18.0.2/30` |
| TOOLS | eth2 | `198.18.1.1/30` |
| TOOLS | lo | `192.0.2.42/32` |
| CLIENT | eth1 | `198.18.1.2/30` |

## Tasks

1. Validate real signed, fresh and fixed-scope event deliveries without letting authentication grant approval.
2. Observe real controller jobs plus independent device RIB/ICMP consequences and unchanged management reachability.
3. Replay committed business IDs without duplicate writes and recover the approved service route.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `python3 /lab/event_client.py seed` | The real network publisher verifies seed against the actual gateway, durable controller jobs and certificate/key-verified device adapter. |
| CLIENT | `python3 /lab/event_client.py invalids` | The real network publisher verifies invalids against the actual gateway, durable controller jobs and certificate/key-verified device adapter. |
| API | `show ip route 192.0.2.42` | The independent IOS RIB contains the intended installed static route. |
| API | `ping 192.0.2.42 repeat 3` | Three real requests reach the Linux loopback through the installed route. |
| API | `ping 198.18.0.2 repeat 3` | The connected device-management path remains healthy. |

## Transition: deliver the initial approved event

On **CLIENT**:

```ios
python3 /lab/event_client.py quarantine
```

- API: `show ip route 192.0.2.42` -- The independent device RIB actually lacks the withdrawn service host route.
- API: `ping 192.0.2.42 repeat 3` -- Three real requests cannot reach the loopback while its usable route is absent.
- API: `ping 198.18.0.2 repeat 3` -- The connected device-management path remains healthy.

## Transition: stop only the frontend gateway

On **TOOLS**:

```ios
python3 /lab/event_gateway.py stop
```

- CLIENT: `python3 /lab/event_client.py gateway-down` -- The real network publisher verifies gateway-down against the actual gateway, durable controller jobs and certificate/key-verified device adapter.
- API: `show ip route 192.0.2.42` -- The independent device RIB actually lacks the withdrawn service host route.
- API: `ping 198.18.0.2 repeat 3` -- The connected device-management path remains healthy.

## Transition: restart only the frontend gateway

On **TOOLS**:

```ios
python3 /lab/event_gateway.py start
```

- CLIENT: `python3 /lab/event_client.py repeat-after-restart` -- The real network publisher verifies repeat-after-restart against the actual gateway, durable controller jobs and certificate/key-verified device adapter.
- API: `show ip route 192.0.2.42` -- The independent device RIB actually lacks the withdrawn service host route.
- API: `ping 198.18.0.2 repeat 3` -- The connected device-management path remains healthy.

## Transition: deliver approved recovery

On **CLIENT**:

```ios
python3 /lab/event_client.py release
```

- API: `show ip route 192.0.2.42` -- The independent IOS RIB contains the intended installed static route.
- API: `ping 192.0.2.42 repeat 3` -- Three real requests reach the Linux loopback through the installed route.
- API: `ping 198.18.0.2 repeat 3` -- The connected device-management path remains healthy.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### API

```ios
hostname API
no ip domain-lookup
ip domain name cml-lab.example
username CML-LAB privilege 15 secret Cml-lab-only-984
aaa new-model
aaa authentication login default local
aaa authorization exec default local
aaa authentication login CONSOLE none
line console 0
 login authentication CONSOLE
 privilege level 15
 exec-timeout 0 0
 logging synchronous
 exit
interface GigabitEthernet1
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
no ip http server
no ip http secure-server
ip http authentication local
ip ssh version 2
line vty 0 4
 login authentication default
 transport input ssh
 exit
end
```

### Inspectable event and device implementations

The [gateway](../../examples/automation/event_gateway.py) and [publisher/probes](../../examples/automation/event_client.py) delegate only to the unchanged [controller](../../examples/automation/controller.py), [contract](../../examples/automation/controller_contract.py), [device network client](../../examples/automation/controller_client.py) and [approval fixture](../../examples/automation/api_security.py). Registered bytes are checked. All generated history, approval, PID and experiment state stays inside the imported copy; wiping it removes that state.

Use `show ip route 192.0.2.42` and the declared independent pings on API. Inspecting a configured string or receiving a gateway 200 alone is insufficient. The exact fields, signature rules, source profiles and bounded fixture assumptions are in the linked source.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
