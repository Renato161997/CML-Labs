# EIGRP Troubleshooting

## Scope and prerequisites

Requires IOL-XE. This startup is deliberately broken: R1 uses AS 100 and R2 uses AS 200. No interface or addressing change is required.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Deliberately broken: EIGRP AS mismatch on R2; the link works but no routing adjacency forms. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Prove that directly connected IP reachability is insufficient for adjacency.
2. Diagnose the autonomous-system mismatch from both running configurations.
3. Repair only the incorrect process and verify learned endpoint routes.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip eigrp neighbors` | The repaired peer forms an adjacency. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |

## Initial fault and repair

EIGRP AS mismatch on R2; the link works but no routing adjacency forms.

Apply on R2:

```ios
configure terminal
no router eigrp 200
router eigrp 100
network 198.18.0.0 0.0.0.3
network 192.0.2.2 0.0.0.0
no auto-summary
end
```

Run baseline acceptance after the repair.

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
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
router eigrp 100
 network 198.18.0.0 0.0.0.3
 network 192.0.2.1 0.0.0.0
 no auto-summary
 exit
end
```

### R2

```ios
hostname R2
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
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
router eigrp 200
 network 198.18.0.0 0.0.0.3
 network 192.0.2.2 0.0.0.0
 no auto-summary
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
