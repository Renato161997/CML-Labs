# Software First-Hop: DHCP Bindings, ARP and Source Inspection

## Scope and prerequisites

This is a bounded software first-hop inspection exercise on three native Services guests, not Cisco DHCP-snooping/DAI/IPSG CLI, switch ASIC validation or a full DHCP client/server implementation. Four previous Cisco reference-image trials did not establish the required IPSG behavior; this alternative explicitly changes the implementation under test. CLIENT eth1 -> GUARD eth1/eth2 -> SERVER eth1 is the only data path. A separate CLIENT eth2/GUARD eth3 control link has an independently verified unreachable route to the data subnet. GUARD has no data IPv4 address or kernel bridge; a live raw-Ethernet worker forwards only admitted frames. No external connector, host sysctl changes, new capabilities or production network are used.

The narrow selecting DORA profile follows the packet layout and message/options definitions in [RFC 2131](https://www.rfc-editor.org/rfc/rfc2131) and [RFC 2132](https://www.rfc-editor.org/rfc/rfc2132). Independent tcpdump decoding must recognize constructed Discover, Offer, Request and ACK packets without a bad IPv4 checksum. The live client then actually transmits and receives these messages over the inspected links with a fresh transaction nonce. Only a correctly sequenced ACK from the physically trusted ingress installs the fixed client's MAC/IP/ingress/lease binding. The helper assigns its kernel IPv4 address only after receiving that ACK. Configuring a binding string or matching the parser to its own constructor is insufficient acceptance.

The untrusted client injects syntactically valid rogue server ACKs and coherent ARP replies with a spoofed sender MAC. Fresh inspector counters must show their rejection; SERVER's actual neighbor entry must retain the admitted client MAC and legitimate data must still work. Assigning an additional real kernel source IP must yield zero of three data replies; removing only that secondary address must preserve the original address and recover two consecutive complete three-reply trains within the fixed recovery deadline. Incomplete ping output or late recovery fails.

The trusted server next offers an actual three-second lease. After the client receives it, the inspector must expire its learned binding and reject data even while the deliberately stale client retains its address. This tests inspector lease enforcement, not automatic operating-system lease removal or renewal. A fresh 600-second DORA exchange must relearn admission and restore real packets. The separate control link and local SERVER HTTP listener remain positive controls. The temporary control-path host route must not bypass inspection, and its removal must restore the normal path.

Scope is one fixed client and server, untagged non-fragmented IPv4, Ethernet/IPv4 checksums and the explicitly supported DHCP options. Relay, renew/rebind, general broadcast discovery, IPv6, VLAN tags and fragmented packets are unsupported; malformed/unsupported untrusted traffic fails closed. This fixture is not a standards conformance suite, throughput benchmark, production gateway or protection against a compromised trusted server. Cloning the admitted MAC and IP on the same permitted ingress is outside its identity assurance. All state and processes disappear with the disposable copy.


Use licensed reference images for cml-labs-services in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- CLIENT eth1 <-> GUARD eth1
- GUARD eth2 <-> SERVER eth1
- CLIENT eth2 <-> GUARD eth3

| Node | Interface | Address |
| --- | --- | --- |

## Tasks

1. Learn a software first-hop binding only from a real correctly sequenced trusted DHCP ACK.
2. Reject rogue server messages, forged ARP senders and unauthorized IPv4 sources while preserving legitimate traffic.
3. Expire an observed wire lease, distinguish stale addressing from admission and recover through a new exchange.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| SERVER | `python3 /lab/h.py decode-wire` | Require fresh actual wire, kernel, process or independently observed packet evidence for this phase. |
| CLIENT | `python3 /lab/h.py acquire` | Receive a matching real selecting DHCP ACK and confirm the received address in the actual kernel. |
| CLIENT | `python3 /lab/h.py data-good` | Require fresh actual wire, kernel, process or independently observed packet evidence for this phase. |
| GUARD | `python3 /lab/h.py bound` | Require fresh actual wire, kernel, process or independently observed packet evidence for this phase. |
| SERVER | `python3 /lab/h.py neighbor-safe` | Require fresh actual wire, kernel, process or independently observed packet evidence for this phase. |
| CLIENT | `ping -n -c 3 -W 1 198.18.99.1` | The separate control link remains healthy. |
| CLIENT | `python3 /lab/h.py control-no-bypass` | Require fresh actual wire, kernel, process or independently observed packet evidence for this phase. |
| SERVER | `python3 /lab/t.py probe 198.18.10.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |

## Transition: reject server messages from the untrusted ingress

On **CLIENT**:

```bash
python3 /lab/h.py rogue
```

- GUARD: `python3 /lab/h.py rogue-blocked` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- CLIENT: `python3 /lab/h.py data-good` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- SERVER: `python3 /lab/h.py neighbor-safe` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- SERVER: `python3 /lab/t.py probe 198.18.10.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Transition: reject coherent forged ARP sender bindings

On **CLIENT**:

```bash
python3 /lab/h.py arp-spoof
```

- GUARD: `python3 /lab/h.py arp-blocked` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- CLIENT: `python3 /lab/h.py data-good` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- SERVER: `python3 /lab/h.py neighbor-safe` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- SERVER: `python3 /lab/t.py probe 198.18.10.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Transition: reject a real unauthorized kernel source address

On **CLIENT**:

```bash
python3 /lab/h.py spoof-ip
```

- GUARD: `python3 /lab/h.py ip-blocked` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- CLIENT: `python3 /lab/h.py data-good` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- SERVER: `python3 /lab/h.py neighbor-safe` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- SERVER: `python3 /lab/t.py probe 198.18.10.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Transition: select a short real server lease

On **SERVER**:

```bash
python3 /lab/h.py short
```

- SERVER: `python3 /lab/t.py probe 198.18.10.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Transition: observe wire lease expiry with a deliberately stale client

On **CLIENT**:

```bash
python3 /lab/h.py acquire
```

- CLIENT: `python3 /lab/h.py expired-data` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- GUARD: `python3 /lab/h.py expired` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- CLIENT: `ping -n -c 3 -W 1 198.18.99.1` -- The separate control link remains healthy.
- SERVER: `python3 /lab/t.py probe 198.18.10.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Transition: restore the trusted long-lease policy

On **SERVER**:

```bash
python3 /lab/h.py long
```

- SERVER: `python3 /lab/t.py probe 198.18.10.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Transition: relearn from a new wire exchange and recover admission

On **CLIENT**:

```bash
python3 /lab/h.py acquire
```

- CLIENT: `python3 /lab/h.py data-good` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- GUARD: `python3 /lab/h.py recovered` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- SERVER: `python3 /lab/h.py neighbor-safe` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- CLIENT: `python3 /lab/h.py control-no-bypass` -- Require fresh actual wire, kernel, process or independently observed packet evidence for this phase.
- SERVER: `python3 /lab/t.py probe 198.18.10.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Inspectable software wire and admission implementation

The [wire parser/constructor](../../examples/security/first_hop_wire.py), [pure admission state machine](../../examples/security/first_hop_policy.py) and [live raw-Ethernet peers and inspector](../../examples/security/first_hop_runtime.py) are embedded from these exact sources. The unchanged [HTTP peer](../../examples/security/traffic_fixture.py) supplies an independent service control. This is a software variant, not validated Cisco switch behavior.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
