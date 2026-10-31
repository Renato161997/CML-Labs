# ENARSI Capstone: Dual-Tenant MPLS VPN Isolation

## Scope and prerequisites

Seven IOSv guests implement two actual MPLS L3VPNs with distinct RDs and route targets65000:10(BLUE) and65000:20(RED). Each tenant has a real CE at both sites. OSPF and LDP form the provider underlay; VPNv4 BGP carries labeled customer /32 routes, with explicit PE-CE static routes and extended communities. BLUE1 has an explicit attempted route toward RED2, and RED2 an attempted return toward BLUE1; the provider VRFs initially isolate them. Adding the RED import to PE1 BLUE must install the forward route but still fail a complete request/reply because PE2 RED lacks the BLUE return route. Adding that second import must make actual BLUE1-to-RED2 ICMP succeed. Both legitimate tenant services and the provider transport must remain healthy through the leak and repair stages. Removing each extra import must recover isolation; the provider core must lack global customer routes and show real labeled-byte forwarding. This is a seven-router software VPN policy exercise, not encryption, firewall state, carrier scale or a hardware throughput claim. Nominal RAM is3584MiB. The simulated reference images require the user own Cisco entitlement; none are redistributed.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- PE1 GigabitEthernet0/0 <-> P GigabitEthernet0/0
- P GigabitEthernet0/1 <-> PE2 GigabitEthernet0/0
- PE1 GigabitEthernet0/1 <-> BLUE1 GigabitEthernet0/0
- PE1 GigabitEthernet0/2 <-> RED1 GigabitEthernet0/0
- PE2 GigabitEthernet0/1 <-> BLUE2 GigabitEthernet0/0
- PE2 GigabitEthernet0/2 <-> RED2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| PE1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| PE1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| PE1 | GigabitEthernet0/1 | `ip address 198.18.11.1 255.255.255.252` |
| PE1 | GigabitEthernet0/2 | `ip address 198.18.12.1 255.255.255.252` |
| P | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| P | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| P | GigabitEthernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| PE2 | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| PE2 | GigabitEthernet0/0 | `ip address 198.18.1.2 255.255.255.252` |
| PE2 | GigabitEthernet0/1 | `ip address 198.18.21.1 255.255.255.252` |
| PE2 | GigabitEthernet0/2 | `ip address 198.18.22.1 255.255.255.252` |
| BLUE1 | Loopback0 | `ip address 192.0.2.11 255.255.255.255` |
| BLUE1 | GigabitEthernet0/0 | `ip address 198.18.11.2 255.255.255.252` |
| RED1 | Loopback0 | `ip address 192.0.2.21 255.255.255.255` |
| RED1 | GigabitEthernet0/0 | `ip address 198.18.12.2 255.255.255.252` |
| BLUE2 | Loopback0 | `ip address 192.0.2.12 255.255.255.255` |
| BLUE2 | GigabitEthernet0/0 | `ip address 198.18.21.2 255.255.255.252` |
| RED2 | Loopback0 | `ip address 192.0.2.22 255.255.255.255` |
| RED2 | GigabitEthernet0/0 | `ip address 198.18.22.2 255.255.255.252` |

## Tasks

1. Build two real MPLS L3VPN tenants over OSPF, LDP and VPNv4, proving same-tenant traffic and cross-tenant isolation.
2. Leak the forward tenant import and prove the new route is insufficient without a matching return path.
3. Leak the return import, observe actual unintended cross-tenant replies, then remove both leaks while preserving both legitimate VPN services.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| PE1 | `show mpls ldp neighbor` | The actual LDP transport neighbor is operational. |
| PE1 | `ping 192.0.2.3 source Loopback0 repeat 3` | Provider transport remains healthy independently of tenant import policy. |
| PE1 | `show ip bgp vpnv4 all summary` | VPNv4 is established and has received both tenant routes. |
| PE1 | `show ip route vrf BLUE 192.0.2.12` | The exact BLUE VRF imports the actual VPNv4 route. |
| PE1 | `show ip route vrf RED 192.0.2.22` | The exact RED VRF imports the actual VPNv4 route. |
| PE2 | `show ip route vrf BLUE 192.0.2.11` | The exact BLUE VRF imports the actual VPNv4 route. |
| PE2 | `show ip route vrf RED 192.0.2.21` | The exact RED VRF imports the actual VPNv4 route. |
| PE1 | `show ip route vrf BLUE 192.0.2.22` | The exact BLUE VRF has no route for the other tenant destination. |
| PE2 | `show ip route vrf RED 192.0.2.11` | The exact RED VRF has no route for the other tenant destination. |
| BLUE1 | `ping 192.0.2.12 source Loopback0 repeat 3` | Real BLUE1 traffic reaches the selected customer loopback. |
| RED1 | `ping 192.0.2.22 source Loopback0 repeat 3` | Real RED1 traffic reaches the selected customer loopback. |
| PE1 | `ping 192.0.2.3 source Loopback0 repeat 3` | Provider transport remains healthy independently of tenant import policy. |
| PE1 | `show mpls ldp neighbor` | The actual LDP transport neighbor is operational. |
| BLUE1 | `ping 192.0.2.22 source Loopback0 repeat 3` | Real BLUE1 traffic does not complete across the selected tenant boundary. |
| P | `show ip route 192.0.2.22` | The transit provider has no global customer-destination route. |
| P | `show mpls forwarding-table` | The provider core actually switches labeled payload bytes toward PE2. |

## Transition: leak only the forward tenant import

On **PE1**:

```ios
configure terminal
ip vrf BLUE
route-target import 65000:20
end
```

- PE1: `show ip route vrf BLUE 192.0.2.22` -- The exact BLUE VRF imports the actual VPNv4 route.
- PE2: `show ip route vrf RED 192.0.2.11` -- The exact RED VRF has no route for the other tenant destination.
- BLUE1: `ping 192.0.2.22 source Loopback0 repeat 3` -- Real BLUE1 traffic does not complete across the selected tenant boundary.
- BLUE1: `ping 192.0.2.12 source Loopback0 repeat 3` -- Real BLUE1 traffic reaches the selected customer loopback.
- RED1: `ping 192.0.2.22 source Loopback0 repeat 3` -- Real RED1 traffic reaches the selected customer loopback.
- PE1: `ping 192.0.2.3 source Loopback0 repeat 3` -- Provider transport remains healthy independently of tenant import policy.
- PE1: `show mpls ldp neighbor` -- The actual LDP transport neighbor is operational.

## Transition: leak the return tenant import

On **PE2**:

```ios
configure terminal
ip vrf RED
route-target import 65000:10
end
```

- PE2: `show ip route vrf RED 192.0.2.11` -- The exact RED VRF imports the actual VPNv4 route.
- BLUE1: `ping 192.0.2.22 source Loopback0 repeat 3` -- Real BLUE1 traffic reaches the selected customer loopback.
- BLUE1: `ping 192.0.2.12 source Loopback0 repeat 3` -- Real BLUE1 traffic reaches the selected customer loopback.
- RED1: `ping 192.0.2.22 source Loopback0 repeat 3` -- Real RED1 traffic reaches the selected customer loopback.
- PE1: `ping 192.0.2.3 source Loopback0 repeat 3` -- Provider transport remains healthy independently of tenant import policy.
- PE1: `show mpls ldp neighbor` -- The actual LDP transport neighbor is operational.
- P: `show ip route 192.0.2.22` -- The transit provider has no global customer-destination route.
- P: `show mpls forwarding-table` -- The provider core actually switches labeled payload bytes toward PE2.

## Transition: remove the forward leak

On **PE1**:

```ios
configure terminal
ip vrf BLUE
no route-target import 65000:20
end
```

- PE1: `show ip route vrf BLUE 192.0.2.22` -- The exact BLUE VRF has no route for the other tenant destination.
- BLUE1: `ping 192.0.2.22 source Loopback0 repeat 3` -- Real BLUE1 traffic does not complete across the selected tenant boundary.
- BLUE1: `ping 192.0.2.12 source Loopback0 repeat 3` -- Real BLUE1 traffic reaches the selected customer loopback.
- RED1: `ping 192.0.2.22 source Loopback0 repeat 3` -- Real RED1 traffic reaches the selected customer loopback.
- PE1: `ping 192.0.2.3 source Loopback0 repeat 3` -- Provider transport remains healthy independently of tenant import policy.
- PE1: `show mpls ldp neighbor` -- The actual LDP transport neighbor is operational.

## Transition: remove the return leak and verify full isolation

On **PE2**:

```ios
configure terminal
ip vrf RED
no route-target import 65000:10
end
```

- PE1: `show ip route vrf BLUE 192.0.2.12` -- The exact BLUE VRF imports the actual VPNv4 route.
- PE1: `show ip route vrf RED 192.0.2.22` -- The exact RED VRF imports the actual VPNv4 route.
- PE2: `show ip route vrf BLUE 192.0.2.11` -- The exact BLUE VRF imports the actual VPNv4 route.
- PE2: `show ip route vrf RED 192.0.2.21` -- The exact RED VRF imports the actual VPNv4 route.
- PE1: `show ip route vrf BLUE 192.0.2.22` -- The exact BLUE VRF has no route for the other tenant destination.
- PE2: `show ip route vrf RED 192.0.2.11` -- The exact RED VRF has no route for the other tenant destination.
- BLUE1: `ping 192.0.2.22 source Loopback0 repeat 3` -- Real BLUE1 traffic does not complete across the selected tenant boundary.
- BLUE1: `ping 192.0.2.12 source Loopback0 repeat 3` -- Real BLUE1 traffic reaches the selected customer loopback.
- RED1: `ping 192.0.2.22 source Loopback0 repeat 3` -- Real RED1 traffic reaches the selected customer loopback.
- PE1: `ping 192.0.2.3 source Loopback0 repeat 3` -- Provider transport remains healthy independently of tenant import policy.
- PE1: `show mpls ldp neighbor` -- The actual LDP transport neighbor is operational.
- P: `show ip route 192.0.2.22` -- The transit provider has no global customer-destination route.
- P: `show mpls forwarding-table` -- The provider core actually switches labeled payload bytes toward PE2.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### PE1

```ios
hostname PE1
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 mpls ip
 exit
mpls label protocol ldp
mpls ldp router-id Loopback0 force
router ospf 1
 router-id 192.0.2.1
 network 192.0.2.1 0.0.0.0 area 0
 network 198.18.0.0 0.0.0.3 area 0
 exit
ip vrf BLUE
 rd 65000:110
 route-target both 65000:10
 exit
interface GigabitEthernet0/1
 ip vrf forwarding BLUE
 ip address 198.18.11.1 255.255.255.252
 no shutdown
 exit
ip route vrf BLUE 192.0.2.11 255.255.255.255 198.18.11.2
ip vrf RED
 rd 65000:120
 route-target both 65000:20
 exit
interface GigabitEthernet0/2
 ip vrf forwarding RED
 ip address 198.18.12.1 255.255.255.252
 no shutdown
 exit
ip route vrf RED 192.0.2.21 255.255.255.255 198.18.12.2
router bgp 65000
 bgp router-id 192.0.2.1
 no bgp default ipv4-unicast
 neighbor 192.0.2.3 remote-as 65000
 neighbor 192.0.2.3 update-source Loopback0
 address-family vpnv4
  neighbor 192.0.2.3 activate
  neighbor 192.0.2.3 send-community extended
 exit-address-family
 address-family ipv4 vrf BLUE
  redistribute static
 exit-address-family
 address-family ipv4 vrf RED
  redistribute static
 exit-address-family
 exit
end
```

### P

```ios
hostname P
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 mpls ip
 exit
interface GigabitEthernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 mpls ip
 exit
mpls label protocol ldp
mpls ldp router-id Loopback0 force
router ospf 1
 router-id 192.0.2.2
 network 192.0.2.2 0.0.0.0 area 0
 network 198.18.0.0 0.0.0.3 area 0
 network 198.18.1.0 0.0.0.3 area 0
 exit
end
```

### PE2

```ios
hostname PE2
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
interface Loopback0
 ip address 192.0.2.3 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 mpls ip
 exit
mpls label protocol ldp
mpls ldp router-id Loopback0 force
router ospf 1
 router-id 192.0.2.3
 network 192.0.2.3 0.0.0.0 area 0
 network 198.18.1.0 0.0.0.3 area 0
 exit
ip vrf BLUE
 rd 65000:310
 route-target both 65000:10
 exit
interface GigabitEthernet0/1
 ip vrf forwarding BLUE
 ip address 198.18.21.1 255.255.255.252
 no shutdown
 exit
ip route vrf BLUE 192.0.2.12 255.255.255.255 198.18.21.2
ip vrf RED
 rd 65000:320
 route-target both 65000:20
 exit
interface GigabitEthernet0/2
 ip vrf forwarding RED
 ip address 198.18.22.1 255.255.255.252
 no shutdown
 exit
ip route vrf RED 192.0.2.22 255.255.255.255 198.18.22.2
router bgp 65000
 bgp router-id 192.0.2.3
 no bgp default ipv4-unicast
 neighbor 192.0.2.1 remote-as 65000
 neighbor 192.0.2.1 update-source Loopback0
 address-family vpnv4
  neighbor 192.0.2.1 activate
  neighbor 192.0.2.1 send-community extended
 exit-address-family
 address-family ipv4 vrf BLUE
  redistribute static
 exit-address-family
 address-family ipv4 vrf RED
  redistribute static
 exit-address-family
 exit
end
```

### BLUE1

```ios
hostname BLUE1
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
interface Loopback0
 ip address 192.0.2.11 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.11.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.12 255.255.255.255 198.18.11.1
ip route 192.0.2.22 255.255.255.255 198.18.11.1
end
```

### RED1

```ios
hostname RED1
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
interface Loopback0
 ip address 192.0.2.21 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.12.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.22 255.255.255.255 198.18.12.1
end
```

### BLUE2

```ios
hostname BLUE2
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
interface Loopback0
 ip address 192.0.2.12 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.21.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.11 255.255.255.255 198.18.21.1
end
```

### RED2

```ios
hostname RED2
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
interface Loopback0
 ip address 192.0.2.22 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.22.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.21 255.255.255.255 198.18.22.1
ip route 192.0.2.11 255.255.255.255 198.18.22.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
