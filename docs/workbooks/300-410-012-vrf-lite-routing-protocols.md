# VRF Lite Routing Protocols

## Scope and prerequisites

Requires IOL-XE. Separate physical links and OSPF processes carry RED and BLUE. Both VRFs deliberately reuse the same transit and endpoint IP addresses. No route leaking or MPLS is configured; reachability is always qualified by VRF.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R1 Ethernet0/1 <-> R2 Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Loopback10 | `ip address 203.0.113.1 255.255.255.255` |
| R1 | Ethernet0/1 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Loopback20 | `ip address 203.0.113.1 255.255.255.255` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Loopback10 | `ip address 203.0.113.2 255.255.255.255` |
| R2 | Ethernet0/1 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Loopback20 | `ip address 203.0.113.2 255.255.255.255` |

## Tasks

1. Trace independent OSPF adjacencies inside two VRFs.
2. Reuse overlapping addressing without leaking routes.
3. Verify each VRF forwards and the global table does not.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip route vrf RED ospf` | RED learns its remote endpoint. |
| R1 | `show ip route vrf BLUE ospf` | BLUE separately learns the overlapping endpoint. |
| R1 | `ping vrf RED 203.0.113.2 source Loopback10 repeat 3` | RED forwards through its own link. |
| R1 | `ping vrf BLUE 203.0.113.2 source Loopback20 repeat 3` | BLUE forwards through the other link. |
| R1 | `show ip route 203.0.113.2` | The overlapping endpoint is absent from the global routing table. |

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
ip vrf RED
 rd 65000:1
 exit
interface Ethernet0/0
 ip vrf forwarding RED
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
interface Loopback10
 ip vrf forwarding RED
 ip address 203.0.113.1 255.255.255.255
 exit
router ospf 10 vrf RED
 router-id 192.0.2.1
 network 198.18.0.0 0.0.0.3 area 0
 network 203.0.113.1 0.0.0.0 area 0
 passive-interface Loopback10
 exit
ip vrf BLUE
 rd 65000:2
 exit
interface Ethernet0/1
 ip vrf forwarding BLUE
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
interface Loopback20
 ip vrf forwarding BLUE
 ip address 203.0.113.1 255.255.255.255
 exit
router ospf 20 vrf BLUE
 router-id 198.51.100.1
 network 198.18.0.0 0.0.0.3 area 0
 network 203.0.113.1 0.0.0.0 area 0
 passive-interface Loopback20
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
ip vrf RED
 rd 65000:1
 exit
interface Ethernet0/0
 ip vrf forwarding RED
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Loopback10
 ip vrf forwarding RED
 ip address 203.0.113.2 255.255.255.255
 exit
router ospf 10 vrf RED
 router-id 192.0.2.2
 network 198.18.0.0 0.0.0.3 area 0
 network 203.0.113.2 0.0.0.0 area 0
 passive-interface Loopback10
 exit
ip vrf BLUE
 rd 65000:2
 exit
interface Ethernet0/1
 ip vrf forwarding BLUE
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Loopback20
 ip vrf forwarding BLUE
 ip address 203.0.113.2 255.255.255.255
 exit
router ospf 20 vrf BLUE
 router-id 198.51.100.2
 network 198.18.0.0 0.0.0.3 area 0
 network 203.0.113.2 0.0.0.0 area 0
 passive-interface Loopback20
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
