# Telemetry: Fresh State and Honest Byte Rates

## Scope and prerequisites

An IOL-XE router exposes a separate management link to TOOLS and data link to CLIENT. The new status-board collector uses the unchanged real Net-SNMP authPriv request implementation, not preconfigured metric strings. It verifies exact OID/type/value responses, actual agent R1 identity, discovers only the declared Ethernet0/1 within the fixed agent's first sixteen interface rows, and reads actual ifOperStatus/ifInOctets/ifOutOctets plus uptime. A second uptime read rejects an agent restart during collection. Counter32 and uptime values are bounded unsigned values; sequential reads are not claimed to be an atomic hardware snapshot.

The console board keeps a last valid sample inside the disposable collector and labels actual fresh availability, operational state and RX/TX bytes from the router interface's perspective. Rates are bytes per elapsed collector-monotonic second, calculated only from two matching interface/agent series within sixty seconds. A counter decrease/wrap, agent-uptime reset, identity change or invalid/stale interval produces unknown rate metadata, not a fabricated large or zero rate. Authenticated idle counters may legitimately produce zero; an unavailable response instead has no fresh sample and no rates. Failed positive-rate acceptance does not advance its reference sample. No clock-to-UTC accuracy, hardware throughput or exclusive attribution of all background bytes to test pings is inferred.

Actual CLIENT traffic must succeed and both interface byte counters must increase between the measured samples. Shutting only the data port must produce a fresh available/down state and failed data pings, while encrypted management SNMP and management IP controls remain healthy. Deliberately selecting the wrong public fixture auth key must produce explicit unavailable/null metrics, with the last valid cache retained; an independent correctly credentialed Net-SNMP probe must still work. Restoring the key and data path must recover real samples and positive measured rates. The optional `python3 /lab/d.py watch` provides a live terminal status board with a two-second pause after each collection; stop it before acceptance because the exercise uses one collector cache, not a concurrent dashboard service. No graphical browser UI, alerting platform or production monitoring deployment is claimed.

All addresses/engine IDs/passwords are public classroom fixtures on closed links. SNMPv3 SHA1/AES128 are the reference-image interoperability settings already verified by the separate SNMP exercise, not a production crypto recommendation. Collection is read-only and fixed to one agent; there is no external discovery, cloud account, Internet connector or real credential. Wiping only this imported lab removes the cache and all state.


Use licensed reference images for iol-xe, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> TOOLS eth1
- R1 Ethernet0/1 <-> CLIENT eth1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| TOOLS | eth1 | `198.18.0.2/30` |
| CLIENT | eth1 | `198.18.1.2/30` |

## Tasks

1. Read actual SNMPv3 interface/identity/counter observations and display their explicit freshness and availability.
2. Calculate defensible byte rates from matching measured samples while rejecting stale/reset/discontinuous series.
3. Distinguish real data-port down from collection/authentication failure, retain positive management controls and recover.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| TOOLS | `python3 /lab/d.py healthy` | Require an actual authenticated/encrypted SNMP sample, exact interface state or explicitly unavailable data; rate acceptance requires positive deltas from two real matching fresh Counter32 samples. |
| TOOLS | `python3 /lab/snmp_probe.py healthy` | The unchanged independent authPriv probe verifies real uptime/sysName and wrong-key rejection while the board is healthy, down or deliberately miscredentialed. |
| TOOLS | `ping -n -c 3 -W 1 198.18.0.1` | Collector-to-agent management IP connectivity is an independent positive control. |
| CLIENT | `ping -n -c 3 -W 1 192.0.2.1` | The actual data interface carries successful service-loopback traffic. |

## Transition: generate observed traffic and require real byte-rate deltas

On **CLIENT**:

```ios
ping -n -c 8 -i 0.2 -W 1 192.0.2.1
```

- TOOLS: `python3 /lab/d.py rates` -- Require an actual authenticated/encrypted SNMP sample, exact interface state or explicitly unavailable data; rate acceptance requires positive deltas from two real matching fresh Counter32 samples.
- TOOLS: `python3 /lab/snmp_probe.py healthy` -- The unchanged independent authPriv probe verifies real uptime/sysName and wrong-key rejection while the board is healthy, down or deliberately miscredentialed.
- TOOLS: `ping -n -c 3 -W 1 198.18.0.1` -- Collector-to-agent management IP connectivity is an independent positive control.

## Transition: shut only the monitored data interface

On **R1**:

```ios
configure terminal
interface Ethernet0/1
shutdown
end
```

- TOOLS: `python3 /lab/d.py down` -- Require an actual authenticated/encrypted SNMP sample, exact interface state or explicitly unavailable data; rate acceptance requires positive deltas from two real matching fresh Counter32 samples.
- CLIENT: `ping -n -c 3 -W 1 192.0.2.1` -- The administratively shut data interface actually prevents service packets.
- TOOLS: `python3 /lab/snmp_probe.py healthy` -- The unchanged independent authPriv probe verifies real uptime/sysName and wrong-key rejection while the board is healthy, down or deliberately miscredentialed.
- TOOLS: `ping -n -c 3 -W 1 198.18.0.1` -- Collector-to-agent management IP connectivity is an independent positive control.

## Transition: restore real interface and service availability

On **R1**:

```ios
configure terminal
interface Ethernet0/1
no shutdown
end
```

- TOOLS: `python3 /lab/d.py healthy` -- Require an actual authenticated/encrypted SNMP sample, exact interface state or explicitly unavailable data; rate acceptance requires positive deltas from two real matching fresh Counter32 samples.
- CLIENT: `ping -n -c 3 -W 1 192.0.2.1` -- The actual data interface carries successful service-loopback traffic.
- TOOLS: `ping -n -c 3 -W 1 198.18.0.1` -- Collector-to-agent management IP connectivity is an independent positive control.

## Transition: select only a wrong public fixture authentication key

On **TOOLS**:

```bash
python3 /lab/d.py bad-auth
```

- TOOLS: `python3 /lab/d.py unavailable` -- Require an actual authenticated/encrypted SNMP sample, exact interface state or explicitly unavailable data; rate acceptance requires positive deltas from two real matching fresh Counter32 samples.
- TOOLS: `python3 /lab/snmp_probe.py healthy` -- The unchanged independent authPriv probe verifies real uptime/sysName and wrong-key rejection while the board is healthy, down or deliberately miscredentialed.
- TOOLS: `ping -n -c 3 -W 1 198.18.0.1` -- Collector-to-agent management IP connectivity is an independent positive control.

## Transition: restore authenticated live observations

On **TOOLS**:

```bash
python3 /lab/d.py good-auth
```

- TOOLS: `python3 /lab/d.py healthy` -- Require an actual authenticated/encrypted SNMP sample, exact interface state or explicitly unavailable data; rate acceptance requires positive deltas from two real matching fresh Counter32 samples.
- TOOLS: `python3 /lab/snmp_probe.py healthy` -- The unchanged independent authPriv probe verifies real uptime/sysName and wrong-key rejection while the board is healthy, down or deliberately miscredentialed.
- CLIENT: `ping -n -c 3 -W 1 192.0.2.1` -- The actual data interface carries successful service-loopback traffic.

## Transition: verify fresh positive rates after full recovery

On **CLIENT**:

```ios
ping -n -c 8 -i 0.2 -W 1 192.0.2.1
```

- TOOLS: `python3 /lab/d.py rates` -- Require an actual authenticated/encrypted SNMP sample, exact interface state or explicitly unavailable data; rate acceptance requires positive deltas from two real matching fresh Counter32 samples.
- TOOLS: `ping -n -c 3 -W 1 198.18.0.1` -- Collector-to-agent management IP connectivity is an independent positive control.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### R1

```ios
hostname R1
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
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
ip access-list standard SNMP-SOURCES
 permit 198.18.0.2
 exit
snmp-server engineID local 8000000903AABBCC000001
snmp-server view LABVIEW iso included
snmp-server view LABVIEW 1.3.6.1.2.1.1.5 included
snmp-server group LAB v3 priv read LABVIEW access SNMP-SOURCES
snmp-server user CML-SNMP LAB v3 auth sha Cml-Snmp-Auth-Only-983 priv aes 128 Cml-Snmp-Priv-Only-984
snmp-server location ISOLATED-CML-LAB
end
```

### Inspectable collector and terminal board

The [typed collector/rate/freshness implementation](../../examples/management/telemetry_board.py) uses the [unchanged Net-SNMP authPriv request source](../../examples/management/snmp_probe.py). Optional `python3 /lab/d.py watch` prints live terminal observations; use Ctrl-C before the acceptance sequence so only one process owns the cache. Fresh/down, unavailable/null and unknown-rate states have distinct meanings. No graphical UI validation is claimed.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
