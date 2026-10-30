# Campus Two Tier Three Tier HA

## Scope and prerequisites

Four IOL-L2 reference switches implement an actual routed-access, two-tier collapsed-core campus. All interswitch links are routed no-switchport interfaces; OSPF area0 carries explicit access service loopbacks. Both distribution paths have equal cost and must appear in the actual RIB. The first fault removes one access uplink. The second shuts both DIST2 data links, modeling data-plane isolation without powering off its CML VM. Each fault must retain endpoint forwarding through the remaining path. Recovery must restore both ECMP next hops. The workbook contrasts a separate three-tier core conceptually; it does not claim to instantiate a third tier or measure physical HA timing. Nominal RAM is4GiB.

Use licensed reference images for ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- ACCESS1 Ethernet0/0 <-> DIST1 Ethernet0/0
- ACCESS1 Ethernet0/1 <-> DIST2 Ethernet0/0
- ACCESS2 Ethernet0/0 <-> DIST1 Ethernet0/1
- ACCESS2 Ethernet0/1 <-> DIST2 Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| DIST1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| DIST1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| DIST1 | Ethernet0/1 | `ip address 198.18.0.9 255.255.255.252` |
| DIST2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| DIST2 | Ethernet0/0 | `ip address 198.18.0.5 255.255.255.252` |
| DIST2 | Ethernet0/1 | `ip address 198.18.0.13 255.255.255.252` |
| ACCESS1 | Loopback0 | `ip address 192.0.2.11 255.255.255.255` |
| ACCESS1 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| ACCESS1 | Ethernet0/1 | `ip address 198.18.0.6 255.255.255.252` |
| ACCESS2 | Loopback0 | `ip address 192.0.2.12 255.255.255.255` |
| ACCESS2 | Ethernet0/0 | `ip address 198.18.0.10 255.255.255.252` |
| ACCESS2 | Ethernet0/1 | `ip address 198.18.0.14 255.255.255.252` |

## Tasks

1. Identify a two-tier collapsed distribution/core design with two routed access switches.
2. Verify actual OSPF ECMP and service-loopback forwarding across both distribution paths.
3. Remove an access uplink and then isolate an entire distribution node data plane, recovering the original paths.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| ACCESS1 | `show ip route 192.0.2.12` | Both equal-cost distribution next hops are actually installed. |
| ACCESS1 | `ping 192.0.2.12 source Loopback0 repeat 3` | The access service loopbacks exchange actual routed traffic. |
| ACCESS2 | `ping 192.0.2.11 source Loopback0 repeat 3` | The reverse access service path also forwards. |

## Transition: remove only one access uplink

On **ACCESS1**:

```ios
configure terminal
interface Ethernet0/0
shutdown
end
```

- ACCESS1: `show ip route 192.0.2.12` -- Only the surviving distribution path remains.
- ACCESS1: `ping 192.0.2.12 source Loopback0 repeat 3` -- The access service loopbacks exchange actual routed traffic.

## Transition: restore access ECMP

On **ACCESS1**:

```ios
configure terminal
interface Ethernet0/0
no shutdown
end
```

- ACCESS1: `show ip route 192.0.2.12` -- Both equal-cost distribution next hops are actually installed.
- ACCESS1: `ping 192.0.2.12 source Loopback0 repeat 3` -- The access service loopbacks exchange actual routed traffic.

## Transition: isolate the second distribution data plane

On **DIST2**:

```ios
configure terminal
interface range Ethernet0/0 - 1
shutdown
end
```

- ACCESS1: `show ip route 192.0.2.12` -- Only the surviving distribution path remains.
- ACCESS1: `ping 192.0.2.12 source Loopback0 repeat 3` -- The access service loopbacks exchange actual routed traffic.

## Transition: restore both distribution paths

On **DIST2**:

```ios
configure terminal
interface range Ethernet0/0 - 1
no shutdown
end
```

- ACCESS1: `show ip route 192.0.2.12` -- Both equal-cost distribution next hops are actually installed.
- ACCESS1: `ping 192.0.2.12 source Loopback0 repeat 3` -- The access service loopbacks exchange actual routed traffic.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### DIST1

```ios
hostname DIST1
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
vtp mode transparent
spanning-tree mode rapid-pvst
interface range Ethernet0/0 - 3
 shutdown
 exit
ip routing
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface Loopback0
 ip ospf 10 area 0
 exit
router ospf 10
 router-id 192.0.2.1
 passive-interface Loopback0
 exit
interface Ethernet0/0
 no switchport
 ip address 198.18.0.1 255.255.255.252
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 no shutdown
 exit
interface Ethernet0/1
 no switchport
 ip address 198.18.0.9 255.255.255.252
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 no shutdown
 exit
end
```

### DIST2

```ios
hostname DIST2
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
vtp mode transparent
spanning-tree mode rapid-pvst
interface range Ethernet0/0 - 3
 shutdown
 exit
ip routing
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface Loopback0
 ip ospf 10 area 0
 exit
router ospf 10
 router-id 192.0.2.2
 passive-interface Loopback0
 exit
interface Ethernet0/0
 no switchport
 ip address 198.18.0.5 255.255.255.252
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 no shutdown
 exit
interface Ethernet0/1
 no switchport
 ip address 198.18.0.13 255.255.255.252
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 no shutdown
 exit
end
```

### ACCESS1

```ios
hostname ACCESS1
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
vtp mode transparent
spanning-tree mode rapid-pvst
interface range Ethernet0/0 - 3
 shutdown
 exit
ip routing
interface Loopback0
 ip address 192.0.2.11 255.255.255.255
 no shutdown
 exit
interface Loopback0
 ip ospf 10 area 0
 exit
router ospf 10
 router-id 192.0.2.11
 passive-interface Loopback0
 exit
interface Ethernet0/0
 no switchport
 ip address 198.18.0.2 255.255.255.252
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 no shutdown
 exit
interface Ethernet0/1
 no switchport
 ip address 198.18.0.6 255.255.255.252
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 no shutdown
 exit
end
```

### ACCESS2

```ios
hostname ACCESS2
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
vtp mode transparent
spanning-tree mode rapid-pvst
interface range Ethernet0/0 - 3
 shutdown
 exit
ip routing
interface Loopback0
 ip address 192.0.2.12 255.255.255.255
 no shutdown
 exit
interface Loopback0
 ip ospf 10 area 0
 exit
router ospf 10
 router-id 192.0.2.12
 passive-interface Loopback0
 exit
interface Ethernet0/0
 no switchport
 ip address 198.18.0.10 255.255.255.252
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 no shutdown
 exit
interface Ethernet0/1
 no switchport
 ip address 198.18.0.14 255.255.255.252
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
