# Wrong Administrative Distance

## Scope and prerequisites

Requires two IOL-XE nodes. OSPF runs only over the primary /30; a second link carries distance-250 backup routes. The fault changes only R1 administrative preference, not link health or OSPF configuration. A successful ping can hide this policy error, so fresh receiver ACL counters prove which link actually carried requests. Replies may remain asymmetric. This is an administrative-distance exercise, not a physical-link failover or throughput test.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R1 Ethernet0/1 <-> R2 Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Ethernet0/1 | `ip address 198.18.1.2 255.255.255.252` |

## Tasks

1. Verify that OSPF wins over a genuinely floating static route.
2. Lower the static administrative distance and diagnose the changed RIB and real request ingress path.
3. Restore the distance without resetting the healthy OSPF adjacency.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip ospf neighbor` | The OSPF adjacency remains FULL. |
| R1 | `show ip route 192.0.2.2` | OSPF wins over the intended distance-250 backup. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | The destination still responds, despite the changed request path. |

## Transition: observe preferred OSPF path

On **R2**:

```ios
clear access-list counters AD-PRIMARY
clear access-list counters AD-SECONDARY
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The destination still responds, despite the changed request path.
- R2: `show access-lists AD-PRIMARY` -- Fresh request counters identify AD-PRIMARY as used.
- R2: `show access-lists AD-SECONDARY` -- Fresh request counters identify AD-SECONDARY as unused.

## Transition: incorrect static preference

On **R1**:

```ios
configure terminal
no ip route 192.0.2.2 255.255.255.255 198.18.1.2 250
ip route 192.0.2.2 255.255.255.255 198.18.1.2 5
end
```

- R1: `show ip route 192.0.2.2` -- The incorrect distance-5 static route preempts OSPF.
- R1: `show ip ospf neighbor` -- The OSPF adjacency remains FULL.

## Transition: observe unintended backup usage

On **R2**:

```ios
clear access-list counters AD-PRIMARY
clear access-list counters AD-SECONDARY
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The destination still responds, despite the changed request path.
- R2: `show access-lists AD-PRIMARY` -- Fresh request counters identify AD-PRIMARY as unused.
- R2: `show access-lists AD-SECONDARY` -- Fresh request counters identify AD-SECONDARY as used.

## Transition: restore floating preference

On **R1**:

```ios
configure terminal
no ip route 192.0.2.2 255.255.255.255 198.18.1.2 5
ip route 192.0.2.2 255.255.255.255 198.18.1.2 250
end
```

- R1: `show ip route 192.0.2.2` -- OSPF wins over the intended distance-250 backup.
- R1: `show ip ospf neighbor` -- The OSPF adjacency remains FULL.

## Transition: observe restored primary path

On **R2**:

```ios
clear access-list counters AD-PRIMARY
clear access-list counters AD-SECONDARY
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The destination still responds, despite the changed request path.
- R2: `show access-lists AD-PRIMARY` -- Fresh request counters identify AD-PRIMARY as used.
- R2: `show access-lists AD-SECONDARY` -- Fresh request counters identify AD-SECONDARY as unused.

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
interface Ethernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.2 255.255.255.255 198.18.1.2 250
router ospf 1
 router-id 192.0.2.1
 network 198.18.0.0 0.0.0.3 area 0
 network 192.0.2.1 0.0.0.0 area 0
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
interface Ethernet0/1
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.1 255.255.255.255 198.18.1.1 250
router ospf 1
 router-id 192.0.2.2
 network 198.18.0.0 0.0.0.3 area 0
 network 192.0.2.2 0.0.0.0 area 0
 exit
ip access-list extended AD-PRIMARY
 permit icmp host 192.0.2.1 host 192.0.2.2
 permit ip any any
 exit
interface Ethernet0/0
 ip access-group AD-PRIMARY in
 exit
ip access-list extended AD-SECONDARY
 permit icmp host 192.0.2.1 host 192.0.2.2
 permit ip any any
 exit
interface Ethernet0/1
 ip access-group AD-SECONDARY in
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
