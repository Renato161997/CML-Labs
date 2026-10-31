# Dual Stack Campus With FHRP

## Scope and prerequisites

Four IOL nodes form a real redundant Layer2 campus with two gateway cores, an access switch and an independent client. IPv4 uses HSRPv2 group10 and virtual198.18.10.1. IPv6 uses separate group11 and the explicitly configured virtual link-local FE80::10; CLIENT has an interface-qualified static IPv6 route through that next hop. Checks identify the IPv6 group row explicitly rather than accepting the IPv4 Active row as IPv6 proof. Each core owns the same isolated training loopback service in each family, so this proves first-hop forwarding failover to an equivalent endpoint, not persistence of a stateful application. Shutting CORE1 Vlan10 keeps its Layer2 links present but transfers both first-hop roles to CORE2. Restoring it must preempt both roles. Withdrawing only the explicit client IPv6 service route breaks the IPv6 service while IPv4 service and both HSRP roles remain healthy; HA alone cannot correct a missing endpoint route. All traffic is isolated, with no external connector. Nominal RAM is4GiB. Syntax reference: https://www.cisco.com/c/en/us/support/docs/ip/hot-standby-router-protocol-hsrp/113216-ipv6-hsrp-00.html and https://www.cisco.com/c/en/us/td/docs/ios/ipv6/command/reference/ipv6_book/ipv6_17.html ; actual support is established only by the recorded image-specific traffic tests.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- CORE1 Ethernet0/0 <-> CORE2 Ethernet0/0
- CORE1 Ethernet0/1 <-> ACCESS Ethernet0/0
- CORE2 Ethernet0/1 <-> ACCESS Ethernet0/1
- CLIENT Ethernet0/0 <-> ACCESS Ethernet0/2

| Node | Interface | Address |
| --- | --- | --- |
| CORE1 | Vlan10 | `ip address 198.18.10.2 255.255.255.0` |
| CORE1 | Loopback0 | `ip address 192.0.2.80 255.255.255.255` |
| CORE1 | Vlan10 | `ipv6 address FE80::2 link-local` |
| CORE1 | Vlan10 | `ipv6 address 2001:DB8:10::2/64` |
| CORE1 | Loopback0 | `ipv6 address 2001:DB8:FFFF::80/128` |
| CORE2 | Vlan10 | `ip address 198.18.10.3 255.255.255.0` |
| CORE2 | Loopback0 | `ip address 192.0.2.80 255.255.255.255` |
| CORE2 | Vlan10 | `ipv6 address FE80::3 link-local` |
| CORE2 | Vlan10 | `ipv6 address 2001:DB8:10::3/64` |
| CORE2 | Loopback0 | `ipv6 address 2001:DB8:FFFF::80/128` |
| ACCESS | Vlan10 | `ip address 198.18.10.4 255.255.255.0` |
| CLIENT | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |
| CLIENT | Ethernet0/0 | `ipv6 address FE80::A link-local` |
| CLIENT | Ethernet0/0 | `ipv6 address 2001:DB8:10::10/64` |

## Tasks

1. Verify separate IPv4 and IPv6 HSRPv2 groups and actual endpoint traffic in both families.
2. Fail the preferred core SVI and require both virtual first hops and data paths to recover through the other core.
3. Restore preemption, isolate an IPv6-only endpoint route fault while IPv4 remains healthy, and recover both families.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CORE1 | `show standby brief` | CORE1 is the actual active gateway. |
| CORE1 | `show standby brief` | The independently numbered IPv6 HSRP group is actually active on CORE1. |
| CLIENT | `ping 198.18.10.1 repeat 3` | The actual first-hop virtual IP is reachable. |
| CLIENT | `ping 192.0.2.80 source Ethernet0/0 repeat 3` | The explicit endpoint route and the active first hop reach the isolated loopback service. |
| CLIENT | `ping ipv6 2001:DB8:FFFF::80 repeat 3` | The IPv6 endpoint actually forwards through its explicit virtual link-local next hop. |

## Transition: fail only the preferred gateway SVI

On **CORE1**:

```ios
configure terminal
interface Vlan10
shutdown
end
```

- CORE2: `show standby brief` -- CORE2 actually takes over the virtual gateway.
- CORE2: `show standby brief` -- The independently numbered IPv6 HSRP group is actually active on CORE2.
- CLIENT: `ping 198.18.10.1 repeat 3` -- The actual first-hop virtual IP is reachable.
- CLIENT: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The explicit endpoint route and the active first hop reach the isolated loopback service.
- CLIENT: `ping ipv6 2001:DB8:FFFF::80 repeat 3` -- The IPv6 endpoint actually forwards through its explicit virtual link-local next hop.

## Transition: recover both preferred first hops

On **CORE1**:

```ios
configure terminal
interface Vlan10
no shutdown
end
```

- CORE1: `show standby brief` -- CORE1 is the actual active gateway.
- CORE1: `show standby brief` -- The independently numbered IPv6 HSRP group is actually active on CORE1.
- CLIENT: `ping 198.18.10.1 repeat 3` -- The actual first-hop virtual IP is reachable.
- CLIENT: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The explicit endpoint route and the active first hop reach the isolated loopback service.
- CLIENT: `ping ipv6 2001:DB8:FFFF::80 repeat 3` -- The IPv6 endpoint actually forwards through its explicit virtual link-local next hop.

## Transition: isolate an IPv6 endpoint route fault

On **CLIENT**:

```ios
configure terminal
no ipv6 route 2001:DB8:FFFF::80/128 Ethernet0/0 FE80::10
end
```

- CLIENT: `ping ipv6 2001:DB8:FFFF::80 repeat 3` -- The IPv6 endpoint loses only the selected IPv6 service after its explicit next-hop route is withdrawn.
- CLIENT: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The explicit endpoint route and the active first hop reach the isolated loopback service.
- CORE1: `show standby brief` -- CORE1 is the actual active gateway.
- CORE1: `show standby brief` -- The independently numbered IPv6 HSRP group is actually active on CORE1.

## Transition: restore the selected IPv6 service route

On **CLIENT**:

```ios
configure terminal
ipv6 route 2001:DB8:FFFF::80/128 Ethernet0/0 FE80::10
end
```

- CORE1: `show standby brief` -- CORE1 is the actual active gateway.
- CORE1: `show standby brief` -- The independently numbered IPv6 HSRP group is actually active on CORE1.
- CLIENT: `ping 198.18.10.1 repeat 3` -- The actual first-hop virtual IP is reachable.
- CLIENT: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The explicit endpoint route and the active first hop reach the isolated loopback service.
- CLIENT: `ping ipv6 2001:DB8:FFFF::80 repeat 3` -- The IPv6 endpoint actually forwards through its explicit virtual link-local next hop.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### CORE1

```ios
hostname CORE1
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
vlan 10
 name CAMPUS
 exit
spanning-tree vlan 10 priority 4096
spanning-tree mode rapid-pvst
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Vlan10
 ip address 198.18.10.2 255.255.255.0
 standby version 2
 standby 10 ip 198.18.10.1
 standby 10 priority 110
 standby 10 preempt
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.80 255.255.255.255
 no shutdown
 exit

ipv6 unicast-routing
interface Vlan10
 ipv6 address FE80::2 link-local
 ipv6 address 2001:DB8:10::2/64
 standby 11 ipv6 FE80::10
 standby 11 priority 110
 standby 11 preempt
 exit
interface Loopback0
 ipv6 address 2001:DB8:FFFF::80/128
 exitend
```

### CORE2

```ios
hostname CORE2
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
vlan 10
 name CAMPUS
 exit
spanning-tree vlan 10 priority 8192
spanning-tree mode rapid-pvst
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Vlan10
 ip address 198.18.10.3 255.255.255.0
 standby version 2
 standby 10 ip 198.18.10.1
 standby 10 priority 100
 standby 10 preempt
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.80 255.255.255.255
 no shutdown
 exit

ipv6 unicast-routing
interface Vlan10
 ipv6 address FE80::3 link-local
 ipv6 address 2001:DB8:10::3/64
 standby 11 ipv6 FE80::10
 standby 11 priority 100
 standby 11 preempt
 exit
interface Loopback0
 ipv6 address 2001:DB8:FFFF::80/128
 exitend
```

### ACCESS

```ios
hostname ACCESS
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
vlan 10
 name LAB
 exit
spanning-tree vlan 10 priority 32768
interface Vlan10
 ip address 198.18.10.4 255.255.255.0
 no shutdown
 exit
spanning-tree mode rapid-pvst
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/2
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
end
```

### CLIENT

```ios
hostname CLIENT
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
interface Ethernet0/0
 ip address 198.18.10.10 255.255.255.0
 no shutdown
 exit
ip route 192.0.2.80 255.255.255.255 198.18.10.1

ipv6 unicast-routing
interface Ethernet0/0
 ipv6 address FE80::A link-local
 ipv6 address 2001:DB8:10::10/64
 exit
ipv6 route 2001:DB8:FFFF::80/128 Ethernet0/0 FE80::10
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
