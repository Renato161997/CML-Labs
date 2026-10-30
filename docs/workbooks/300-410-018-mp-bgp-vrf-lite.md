# MP-BGP VRF Lite

## Scope and prerequisites

Three IOSv reference routers implement two PEs and an actual OSPF/LDP provider transit. Each PE contains RED and BLUE VRFs with overlapping customer loopback addresses. Unique per-PE/per-VRF RDs and separate route targets preserve both VPNv4 identities. Local VRF loopbacks model customer prefixes; no CE devices are instantiated. This extends the VRF-Lite namespace concept with real MP-BGP VPNv4 and labeled transport rather than claiming VRF-Lite alone carries VPN labels. Actual per-VRF traffic succeeds while P lacks the customer IP route and counts labeled bytes. Removing only BLUE import must withdraw that RIB entry before its negative probe; RED, LDP and provider reachability remain healthy. Recovery must restore both namespaces. This does not model a full carrier deployment or hardware scale. Nominal RAM is1536MiB.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- PE1 GigabitEthernet0/0 <-> P GigabitEthernet0/0
- P GigabitEthernet0/1 <-> PE2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| PE1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| PE1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| PE1 | Loopback10 | `ip address 203.0.113.1 255.255.255.255` |
| PE1 | Loopback20 | `ip address 203.0.113.1 255.255.255.255` |
| P | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| P | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| P | GigabitEthernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| PE2 | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| PE2 | GigabitEthernet0/0 | `ip address 198.18.1.2 255.255.255.252` |
| PE2 | Loopback10 | `ip address 203.0.113.2 255.255.255.255` |
| PE2 | Loopback20 | `ip address 203.0.113.2 255.255.255.255` |

## Tasks

1. Separate VRF-local addressing from MP-BGP VPNv4 transport and route-target import.
2. Carry the same customer addresses in two real independent VRFs across labeled transport.
3. Withdraw only BLUE import, keep RED and provider transport healthy, then recover BLUE.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| PE1 | `show mpls ldp neighbor` | Actual transport LDP is operational. |
| PE1 | `show ip route vrf RED 203.0.113.2` | The overlapping service is imported in the correct RED VRF. |
| PE1 | `show ip route vrf BLUE 203.0.113.2` | The overlapping service is imported in the correct BLUE VRF. |
| PE1 | `ping vrf RED 203.0.113.2 source Loopback10 repeat 3` | The RED namespace actually forwards across the provider transport. |
| PE1 | `ping vrf BLUE 203.0.113.2 source Loopback20 repeat 3` | The BLUE namespace actually forwards across the provider transport. |
| P | `show ip route 203.0.113.2` | The provider router has no global route for either overlapping customer service. |
| P | `show mpls forwarding-table` | Actual labeled bytes are switched toward the remote PE. |

## Transition: withdraw only BLUE route-target import

On **PE1**:

```ios
configure terminal
ip vrf BLUE
no route-target import 65000:20
end
```

- PE1: `show ip route vrf BLUE 203.0.113.2` -- The BLUE service has actually left its VRF RIB.
- PE1: `ping vrf BLUE 203.0.113.2 source Loopback20 repeat 3` -- The BLUE namespace has lost only its imported service.
- PE1: `show ip route vrf RED 203.0.113.2` -- The overlapping service is imported in the correct RED VRF.
- PE1: `ping vrf RED 203.0.113.2 source Loopback10 repeat 3` -- The RED namespace actually forwards across the provider transport.
- PE1: `ping 192.0.2.3 source Loopback0 repeat 3` -- Provider loopback transport is unaffected.
- P: `show ip route 203.0.113.2` -- The provider router has no global route for either overlapping customer service.

## Transition: restore BLUE import without leaking to global

On **PE1**:

```ios
configure terminal
ip vrf BLUE
route-target import 65000:20
end
```

- PE1: `show ip route vrf BLUE 203.0.113.2` -- The overlapping service is imported in the correct BLUE VRF.
- PE1: `ping vrf BLUE 203.0.113.2 source Loopback20 repeat 3` -- The BLUE namespace actually forwards across the provider transport.
- PE1: `ping vrf RED 203.0.113.2 source Loopback10 repeat 3` -- The RED namespace actually forwards across the provider transport.
- P: `show ip route 203.0.113.2` -- The provider router has no global route for either overlapping customer service.
- P: `show mpls forwarding-table` -- Actual labeled bytes are switched toward the remote PE.

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
ip vrf RED
 rd 65000:110
 route-target both 65000:10
 exit
interface Loopback10
 ip vrf forwarding RED
 ip address 203.0.113.1 255.255.255.255
 exit
ip vrf BLUE
 rd 65000:120
 route-target both 65000:20
 exit
interface Loopback20
 ip vrf forwarding BLUE
 ip address 203.0.113.1 255.255.255.255
 exit
router bgp 65000
 bgp router-id 192.0.2.1
 no bgp default ipv4-unicast
 neighbor 192.0.2.3 remote-as 65000
 neighbor 192.0.2.3 update-source Loopback0
 address-family vpnv4
 neighbor 192.0.2.3 activate
 neighbor 192.0.2.3 send-community extended
 exit-address-family
 address-family ipv4 vrf RED
 network 203.0.113.1 mask 255.255.255.255
 exit-address-family
 address-family ipv4 vrf BLUE
 network 203.0.113.1 mask 255.255.255.255
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
ip vrf RED
 rd 65000:310
 route-target both 65000:10
 exit
interface Loopback10
 ip vrf forwarding RED
 ip address 203.0.113.2 255.255.255.255
 exit
ip vrf BLUE
 rd 65000:320
 route-target both 65000:20
 exit
interface Loopback20
 ip vrf forwarding BLUE
 ip address 203.0.113.2 255.255.255.255
 exit
router bgp 65000
 bgp router-id 192.0.2.3
 no bgp default ipv4-unicast
 neighbor 192.0.2.1 remote-as 65000
 neighbor 192.0.2.1 update-source Loopback0
 address-family vpnv4
 neighbor 192.0.2.1 activate
 neighbor 192.0.2.1 send-community extended
 exit-address-family
 address-family ipv4 vrf RED
 network 203.0.113.2 mask 255.255.255.255
 exit-address-family
 address-family ipv4 vrf BLUE
 network 203.0.113.2 mask 255.255.255.255
 exit-address-family
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
