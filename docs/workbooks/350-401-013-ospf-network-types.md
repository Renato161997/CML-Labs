# OSPF Network Types

## Scope and prerequisites

Two IOL-XE routers use a shared Ethernet segment. Broadcast and point-to-point OSPF modes are compared on the same endpoints. An intermediate one-sided conversion checks only the changed local network type; it does not assume that mismatched network types always prevent adjacency. Matching final configurations must establish FULL adjacency and route loopback traffic. Election timing and physical failure convergence are outside scope.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Observe broadcast adjacency roles and a real routed endpoint path.
2. Convert both ends to point-to-point and inspect the changed operational role.
3. Restore broadcast mode and verify adjacency and forwarding.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip ospf interface Ethernet0/0` | The active OSPF interface reports BROADCAST. |
| R1 | `show ip ospf neighbor` | The adjacency is FULL with the expected network-type role. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |

## Transition: first peer becomes point-to-point

On **R1**:

```ios
configure terminal
interface Ethernet0/0
ip ospf network point-to-point
end
```

- R1: `show ip ospf interface Ethernet0/0` -- The active OSPF interface reports POINT_TO_POINT.

## Transition: second peer becomes point-to-point

On **R2**:

```ios
configure terminal
interface Ethernet0/0
ip ospf network point-to-point
end
```

- R1: `show ip ospf interface Ethernet0/0` -- The active OSPF interface reports POINT_TO_POINT.
- R1: `show ip ospf neighbor` -- The adjacency is FULL with the expected network-type role.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Three replies.

## Transition: first peer returns to broadcast

On **R1**:

```ios
configure terminal
interface Ethernet0/0
ip ospf network broadcast
end
```

- R1: `show ip ospf interface Ethernet0/0` -- The active OSPF interface reports BROADCAST.

## Transition: second peer returns to broadcast

On **R2**:

```ios
configure terminal
interface Ethernet0/0
ip ospf network broadcast
end
```

- R1: `show ip ospf interface Ethernet0/0` -- The active OSPF interface reports BROADCAST.
- R1: `show ip ospf neighbor` -- The adjacency is FULL with the expected network-type role.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Three replies.

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
router ospf 1
 router-id 192.0.2.1
 network 192.0.2.1 0.0.0.0 area 0
 network 198.18.0.0 0.0.0.3 area 0
 passive-interface Loopback0
 exit
interface Ethernet0/0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
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
router ospf 1
 router-id 192.0.2.2
 network 192.0.2.2 0.0.0.0 area 0
 network 198.18.0.0 0.0.0.3 area 0
 passive-interface Loopback0
 exit
interface Ethernet0/0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
