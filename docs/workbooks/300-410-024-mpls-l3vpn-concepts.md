# MPLS L3VPN Concepts

## Scope and prerequisites

Distinct per-PE route distinguishers share one explicit import/export route target. Five IOSv guests implement a real small MPLS L3VPN, not GRE renamed as MPLS. VPNv4 convergence has an explicit bounded wait because the initial BGP TCP attempt can precede OSPF reachability; a process-up indication is never accepted as a route. PE-CE static routes supply customer prefixes, OSPF supplies provider loopbacks, LDP supplies transport labels and VPNv4 BGP carries labeled VPN routes with route-target communities. The transit P router must lack the customer /32 in its global routing table yet switch actual labeled bytes. Route-target withdrawal must remove only the imported VPN route while transport stays healthy. All interfaces are isolated and all addresses educational. Nominal RAM is 5x512 MiB. This is software forwarding and protocol validation, not hardware throughput, carrier design scale or entitlement to redistribute IOSv. Cisco lists MPLS L3VPN among IOSv features: https://developer.cisco.com/docs/modeling-labs/iosv/ .

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- PE1 GigabitEthernet0/0 <-> P GigabitEthernet0/0
- P GigabitEthernet0/1 <-> PE2 GigabitEthernet0/0
- PE1 GigabitEthernet0/1 <-> CE1 GigabitEthernet0/0
- PE2 GigabitEthernet0/1 <-> CE2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| PE1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| PE1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| PE1 | GigabitEthernet0/1 | `ip address 198.18.10.1 255.255.255.252` |
| P | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| P | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| P | GigabitEthernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| PE2 | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| PE2 | GigabitEthernet0/0 | `ip address 198.18.1.2 255.255.255.252` |
| PE2 | GigabitEthernet0/1 | `ip address 198.18.20.1 255.255.255.252` |
| CE1 | Loopback0 | `ip address 192.0.2.10 255.255.255.255` |
| CE1 | GigabitEthernet0/0 | `ip address 198.18.10.2 255.255.255.252` |
| CE2 | Loopback0 | `ip address 192.0.2.20 255.255.255.255` |
| CE2 | GigabitEthernet0/0 | `ip address 198.18.20.2 255.255.255.252` |

## Tasks

1. Establish actual OSPF transport, LDP labels and VPNv4 BGP between provider edge routers.
2. Carry real customer loopback traffic while the transit router has no global customer route.
3. Remove only the import route target, observe VPN failure with healthy provider transport, and restore it.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| PE1 | `show mpls ldp neighbor` | The actual transport LDP peer is operational. |
| PE1 | `ping 192.0.2.3 source Loopback0 repeat 3` | Provider transport reachability survives the VPN import fault. |
| PE1 | `show ip bgp vpnv4 all summary` | VPNv4 BGP is established and has actually received the remote customer prefix. |
| PE1 | `show ip route vrf CUST 192.0.2.20` | The customer route is imported through VPNv4 BGP. |
| CE1 | `ping 192.0.2.20 source Loopback0 repeat 3` | The actual customer data plane crosses the labeled core. |
| P | `show ip route 192.0.2.20` | The provider transit router has no global customer-destination route. |
| P | `show mpls forwarding-table` | Actual labeled bytes are switched toward the remote PE. |

## Transition: withdraw only the customer import target

On **PE1**:

```ios
configure terminal
ip vrf CUST
no route-target import 65000:10
end
```

- PE1: `show ip route vrf CUST 192.0.2.20` -- The target customer route is no longer imported.
- CE1: `ping 192.0.2.20 source Loopback0 repeat 3` -- The actual customer data plane fails after selective route-target withdrawal.
- PE1: `ping 192.0.2.3 source Loopback0 repeat 3` -- Provider transport reachability survives the VPN import fault.
- PE1: `show mpls ldp neighbor` -- The actual transport LDP peer is operational.

## Transition: restore the customer import target

On **PE1**:

```ios
configure terminal
ip vrf CUST
route-target import 65000:10
end
```

- PE1: `show ip route vrf CUST 192.0.2.20` -- The customer route is imported through VPNv4 BGP.
- CE1: `ping 192.0.2.20 source Loopback0 repeat 3` -- The actual customer data plane crosses the labeled core.
- P: `show ip route 192.0.2.20` -- The provider transit router has no global customer-destination route.
- P: `show mpls forwarding-table` -- Actual labeled bytes are switched toward the remote PE.
- PE1: `ping 192.0.2.3 source Loopback0 repeat 3` -- Provider transport reachability survives the VPN import fault.

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
ip vrf CUST
 rd 65000:1
 route-target both 65000:10
 exit
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 mpls ip
 exit
interface GigabitEthernet0/1
 ip vrf forwarding CUST
 ip address 198.18.10.1 255.255.255.252
 no shutdown
 exit
mpls label protocol ldp
mpls ldp router-id Loopback0 force
router ospf 1
 router-id 192.0.2.1
 network 192.0.2.1 0.0.0.0 area 0
 network 198.18.0.0 0.0.0.3 area 0
 exit
ip route vrf CUST 192.0.2.10 255.255.255.255 198.18.10.2
router bgp 65000
 bgp router-id 192.0.2.1
 no bgp default ipv4-unicast
 neighbor 192.0.2.3 remote-as 65000
 neighbor 192.0.2.3 update-source Loopback0
 address-family vpnv4
  neighbor 192.0.2.3 activate
  neighbor 192.0.2.3 send-community extended
 exit-address-family
 address-family ipv4 vrf CUST
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
ip vrf CUST
 rd 65000:3
 route-target both 65000:10
 exit
interface Loopback0
 ip address 192.0.2.3 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 mpls ip
 exit
interface GigabitEthernet0/1
 ip vrf forwarding CUST
 ip address 198.18.20.1 255.255.255.252
 no shutdown
 exit
mpls label protocol ldp
mpls ldp router-id Loopback0 force
router ospf 1
 router-id 192.0.2.3
 network 192.0.2.3 0.0.0.0 area 0
 network 198.18.1.0 0.0.0.3 area 0
 exit
ip route vrf CUST 192.0.2.20 255.255.255.255 198.18.20.2
router bgp 65000
 bgp router-id 192.0.2.3
 no bgp default ipv4-unicast
 neighbor 192.0.2.1 remote-as 65000
 neighbor 192.0.2.1 update-source Loopback0
 address-family vpnv4
  neighbor 192.0.2.1 activate
  neighbor 192.0.2.1 send-community extended
 exit-address-family
 address-family ipv4 vrf CUST
  redistribute static
 exit-address-family
 exit
end
```

### CE1

```ios
hostname CE1
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
interface Loopback0
 ip address 192.0.2.10 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.10.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.20 255.255.255.255 198.18.10.1
end
```

### CE2

```ios
hostname CE2
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
interface Loopback0
 ip address 192.0.2.20 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.20.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.10 255.255.255.255 198.18.20.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
