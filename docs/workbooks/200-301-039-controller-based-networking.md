# Controller, Management and Data-Path Independence

## Scope and prerequisites

Three real CML guests separate the application client, local teaching controller and managed CSR1000v. The CLIENT net-tools eth1 address 198.18.1.2/30 reaches only the TOOLS eth2 controller listener 198.18.1.1:8080. TOOLS eth1 198.18.0.2/30 connects to API GigabitEthernet1 198.18.0.1/30. The destination 192.0.2.42/32 is an actual TOOLS Linux loopback. IOS CLI, its installed RIB and real ICMP independently establish the forwarding outcome. The controller reads real interface facts using certificate-verified RESTCONF and changes only that host route through explicitly key-pinned NETCONF. The registered iosxe-api-v1 preparation creates and serially transfers public trust material for these disposable guests; no private key or administrator credential enters the client.

Northbound HTTP uses a public classroom bearer token on its separate isolated Ethernet segment. It demonstrates the stated application contract, not production transport confidentiality or an external authorization service. A root-owned local fixture policy separately approves exact request identifiers and route intent; a client cannot grant approval with a field in its request. Duplicate JSON fields, unknown keys, wrong scalar types, unexpected targets and conflicting request identifiers are rejected. A single owned service process serializes concurrent device operations. SQLite WAL retains job state and ordered lifecycle events across process restart; completed replay does not perform another write. A resumed pending job reads actual device state before deciding whether a write is necessary. This is a single-process compensation model, not a distributed transaction or multi-replica service.

Every mutation observes the before state and confirms actual device readback. An application confirmation fault can be enabled only by the fixture CLI; it occurs after a real write/readback and must restore the before state through a fresh verified device session. Failed compensation remains explicitly unverified. No external connector, personal token, cloud account or existing user lab is used. Nominal RAM is 4608 MiB, requiring the explicitly reserved larger-case mode. Exact licensed images and fresh results are recorded separately. These are local controller/application exercises; the historical Catalyst Center concept filenames do not establish integration with that product.

After the baseline transaction installs the route, the fault stops only the application process. The router and Linux loopback remain running. A refused client HTTP connection and independent successful device packets must coexist. Restart must expose the durable job and a new actual service PID, retain ordered history and replay the completed request without changing the device.

Use licensed reference images for cml-labs-toolbox, csr1000v, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- API GigabitEthernet1 <-> TOOLS eth1
- TOOLS eth2 <-> CLIENT eth1

| Node | Interface | Address |
| --- | --- | --- |
| TOOLS | eth1 (device-facing) | 198.18.0.2/30 |
| TOOLS | eth2 (northbound) | 198.18.1.1/30 |
| TOOLS | lo (data endpoint) | 192.0.2.42/32 |
| CLIENT | eth1 | 198.18.1.2/30 |
| API | GigabitEthernet1 | `ip address 198.18.0.1 255.255.255.252` |
| TOOLS | eth1 | `198.18.0.2/30` |
| TOOLS | eth2 | `198.18.1.1/30` |
| TOOLS | lo | `192.0.2.42/32` |
| CLIENT | eth1 | `198.18.1.2/30` |

## Tasks

1. Submit an approved route intent over a real northbound Ethernet link and verify actual device forwarding.
2. Stop only the controller service and prove that its listener is unavailable while the programmed RIB and data path continue.
3. Restart the same process state and replay its completed job without another device change.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `python3 /lab/client.py baseline` | The real northbound HTTP client verifies baseline against the durable controller and its actual device adapter. |
| API | `show ip route 192.0.2.42` | The independent IOS RIB contains the intended installed static route. |
| API | `ping 192.0.2.42 repeat 3` | Three real requests reach the Linux loopback through the installed route. |
| API | `ping 198.18.0.2 repeat 3` | The connected device-management path remains healthy. |

## Transition: stop only the controller application

On **TOOLS**:

```ios
python3 /lab/c.py stop
```

- CLIENT: `python3 /lab/client.py down` -- The real northbound HTTP client verifies down against the durable controller and its actual device adapter.
- API: `show ip route 192.0.2.42` -- The independent IOS RIB contains the intended installed static route.
- API: `ping 192.0.2.42 repeat 3` -- Three real requests reach the Linux loopback through the installed route.
- API: `ping 198.18.0.2 repeat 3` -- The connected device-management path remains healthy.

## Transition: restart the controller with durable state

On **TOOLS**:

```ios
python3 /lab/c.py start
```

- CLIENT: `python3 /lab/client.py persistence` -- The real northbound HTTP client verifies persistence against the durable controller and its actual device adapter.
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

### Application sources and state

The topology embeds the readable [contract](../../examples/automation/controller_contract.py), [controller](../../examples/automation/controller.py) and [network client](../../examples/automation/controller_client.py). The existing immutable device adapters provide actual RESTCONF/NETCONF operations. Embedded bytes are checked automatically.

The fixture policy, SQLite database, daemon PID and private experiment log remain under `/lab` in the imported guest. Lifecycle history is available from the authenticated `/v1/history` endpoint. Stop/start preserves that database; wiping only the imported lab removes all its state. Resetting a classroom experiment is distinct from undoing a production change.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
