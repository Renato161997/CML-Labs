# OSPF Summarization Filtering

## Scope and prerequisites

Three IOL-XE nodes model areas0 and10 with R2 as the ABR. Two host routes are represented by192.0.2.0/24. An outbound area prefix-list denies that range and its more-specifics while permitting other inter-area prefixes. Positive controls distinguish selective Type3 export from a failed adjacency or lost transit link. The route table and real endpoint probes are checked; this is not a convergence-time benchmark.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R2 Ethernet0/1 <-> R3 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 203.0.113.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.12.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 203.0.113.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.12.2 255.255.255.252` |
| R2 | Ethernet0/1 | `ip address 198.18.23.1 255.255.255.252` |
| R3 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R3 | Loopback1 | `ip address 192.0.2.2 255.255.255.255` |
| R3 | Ethernet0/0 | `ip address 198.18.23.2 255.255.255.252` |

## Tasks

1. Inspect an actual inter-area aggregate and forward to both represented endpoints.
2. Filter only the endpoint aggregate/member set at the ABR area boundary.
3. Prove that transit reachability and intra-area endpoint routes remain healthy, then restore export.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R2 | `show ip ospf neighbor` | The area0 adjacency is FULL. |
| R2 | `show ip ospf neighbor` | The area10 adjacency is FULL. |
| R1 | `show ip route 192.0.2.1` | The ABR exports one aggregate for the endpoint prefixes. |
| R1 | `ping 192.0.2.1 source Loopback0 repeat 3` | The sampled data path works. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | The sampled data path works. |

## Transition: filter endpoint Type3 export

On **R2**:

```ios
configure terminal
ip prefix-list AREA10-OUT seq 5 deny 192.0.2.0/24 le 32
ip prefix-list AREA10-OUT seq 10 permit 0.0.0.0/0 le 32
router ospf 1
area 10 filter-list prefix AREA10-OUT out
end
```

- R1: `show ip route 192.0.2.1` -- The filtered endpoint aggregate is absent.
- R1: `ping 192.0.2.1 source Loopback0 repeat 3` -- The sampled data path is withdrawn.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The sampled data path is withdrawn.
- R1: `ping 198.18.23.2 source Loopback0 repeat 3` -- The sampled data path works.
- R2: `ping 192.0.2.1 source Loopback0 repeat 3` -- The ABR still forwards to the intra-area endpoint.

## Transition: restore endpoint Type3 export

On **R2**:

```ios
configure terminal
router ospf 1
no area 10 filter-list prefix AREA10-OUT out
end
```

- R2: `show ip ospf neighbor` -- The area0 adjacency is FULL.
- R2: `show ip ospf neighbor` -- The area10 adjacency is FULL.
- R1: `show ip route 192.0.2.1` -- The ABR exports one aggregate for the endpoint prefixes.
- R1: `ping 192.0.2.1 source Loopback0 repeat 3` -- The sampled data path works.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The sampled data path works.

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
 ip address 203.0.113.1 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.12.1 255.255.255.252
 no shutdown
 exit
router ospf 1
 router-id 203.0.113.1
 passive-interface Loopback0
 network 198.18.12.0 0.0.0.3 area 0
 network 203.0.113.1 0.0.0.0 area 0
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
 ip address 203.0.113.2 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.12.2 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.23.1 255.255.255.252
 no shutdown
 exit
router ospf 1
 router-id 203.0.113.2
 passive-interface Loopback0
 network 198.18.12.0 0.0.0.3 area 0
 network 198.18.23.0 0.0.0.3 area 10
 network 203.0.113.2 0.0.0.0 area 0
 area 10 range 192.0.2.0 255.255.255.0 advertise
 exit
end
```

### R3

```ios
hostname R3
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
interface Loopback1
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.23.2 255.255.255.252
 no shutdown
 exit
router ospf 1
 router-id 203.0.113.3
 passive-interface Loopback0
 network 198.18.23.0 0.0.0.3 area 10
 network 192.0.2.0 0.0.0.3 area 10
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
