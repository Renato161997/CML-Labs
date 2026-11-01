# QoS: Receiver-Verified DSCP and Selective Policing

## Scope and prerequisites

A real IOL-XE router forwards between two native Linux endpoints. UDP destination 9000 is the only selected data class; an egress MQC policy sets its actual DSCP to EF. The receiver obtains each datagram's real IP_TOS ancillary value, requiring 184 (DSCP 46, ECN 0). Source sockets explicitly send TOS 0. Four independent UDP 9001 controls must all arrive with TOS 0 in every phase. No configured marking string can replace receiver evidence.

Every probe creates an acknowledged fresh evidence generation over an isolated HTTP control fixture, then sends exactly 16 distinct data datagrams of 1000-byte UDP payload and four 100-byte controls, paced 10ms apart. The receiver rejects malformed payloads and duplicate sequence evidence; older generations cannot supply current results. A bounded settling window precedes acceptance. These are small finite correctness probes, not a benchmark or calibrated rate/throughput test.

Remove the marking attachment: all 16 data packets must still arrive but now with observed TOS 0. Restore marking and require actual TOS 184 again. Attach only the ingress data-class policer, CIR 8000bit/s and burst 1500bytes, conform transmit/exceed drop. Its fresh exceeded counter must initially be zero. The bounded burst must then deliver some but fewer than 16 data packets, all still EF, while all four unselected controls survive; the actual policer must show both conformed and exceeded packets. Finally detach policing and recover all 16 EF packets and four controls.

The fixture HTTP 8081 interface exists solely for resetting/reading the disposable receiver's bounded counters. It accepts only the declared client source and exact generation fields; it is not an authenticated production API or a latency/packet-loss monitor. Images, virtual scheduling, IOL-XE software rate behavior and host load constrain observations. No hardware QoS accuracy, queuing fairness, congestion avoidance or service guarantee is inferred. No external connector, installed production policy or credential is required. Stop/wipe only the imported copy to reset.


Use licensed reference images for iol-xe, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- CLIENT eth1 <-> R1 Ethernet0/0
- R1 Ethernet0/1 <-> SERVER eth1

| Node | Interface | Address |
| --- | --- | --- |
| CLIENT | eth1 | 198.18.0.2/30 |
| R1 | Ethernet0/0 | 198.18.0.1/30 |
| R1 | Ethernet0/1 | 198.18.1.1/30 |
| SERVER | eth1 | 198.18.1.2/30 |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |

## Tasks

1. Observe actual receiver TOS and exact per-generation UDP sequence sets independently of router configuration.
2. Remove/restore marking while retaining complete data and control delivery.
3. Observe real selective ingress policing with fresh counter evidence and unpoliced controls, then recover full delivery.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `python3 /lab/q.py marked` | Fresh receiver-side UDP sequence and IP_RECVTOS observations must meet the exact marked contract while all four independent control datagrams arrive unmarked. |
| R1 | `show policy-map interface Ethernet0/1 output` | The forwarding router also reports actual packet marking in its attached egress policy, independently of receiver TOS evidence. |

## Transition: withdraw only actual egress marking

On **R1**:

```ios
configure terminal
interface Ethernet0/1
no service-policy output CML-MARK
end
```

- CLIENT: `python3 /lab/q.py unmarked` -- Fresh receiver-side UDP sequence and IP_RECVTOS observations must meet the exact unmarked contract while all four independent control datagrams arrive unmarked.

## Transition: restore receiver-observed EF marking

On **R1**:

```ios
configure terminal
interface Ethernet0/1
service-policy output CML-MARK
end
```

- CLIENT: `python3 /lab/q.py marked` -- Fresh receiver-side UDP sequence and IP_RECVTOS observations must meet the exact marked contract while all four independent control datagrams arrive unmarked.

## Transition: attach the selective data policer

On **R1**:

```ios
configure terminal
interface Ethernet0/0
service-policy input CML-POLICE
end
```

- R1: `show policy-map interface Ethernet0/0 input` -- Before the selected burst, the newly attached real policer has no historical exceeded packets.
- CLIENT: `python3 /lab/q.py limited` -- Fresh receiver-side UDP sequence and IP_RECVTOS observations must meet the exact limited contract while all four independent control datagrams arrive unmarked.
- R1: `show policy-map interface Ethernet0/0 input` -- Actual fresh conform/exceed packet counters distinguish policing drops from receiver timing or stale totals.

## Transition: restore complete marked data delivery

On **R1**:

```ios
configure terminal
interface Ethernet0/0
no service-policy input CML-POLICE
end
```

- CLIENT: `python3 /lab/q.py marked` -- Fresh receiver-side UDP sequence and IP_RECVTOS observations must meet the exact marked contract while all four independent control datagrams arrive unmarked.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Inspectable traffic fixture

The [UDP generation, receiver and TOS probe](../../examples/security/qos_probe.py) are embedded unchanged. Inspect `show policy-map interface`, `show class-map`, and `show access-lists CML-QOS-DATA` on R1. The HTTP counter fixture and its process disappear with the imported server node.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
