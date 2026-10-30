# IPv6 Only Mini Campus

## Scope and prerequisites

Four IOL reference nodes implement two access VLANs and an IPv6-only routed data plane. IOL routers stand in for endpoints and use explicit static IPv6 addresses and default routes; this exercise does not claim SLAAC or Linux-client behavior. No data interface receives an IPv4 address. The switch trunk and connected IPv6 routes are separate failure domains: pruning VLAN20 leaves the router subinterface and connected prefix present while actual inter-VLAN traffic fails. Recovery must restore both directions and the real ND entry. The second fault removes only CLIENT-A default routing while its on-link gateway remains reachable. This is an isolated virtual reference, not an IPv6 Internet or throughput test. Nominal RAM is4GiB.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> SW1 Ethernet0/0
- CLIENT-A Ethernet0/0 <-> SW1 Ethernet0/1
- CLIENT-B Ethernet0/0 <-> SW1 Ethernet0/2

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Ethernet0/0.10 | `ipv6 address 2001:db8:10::1/64` |
| R1 | Ethernet0/0.10 | `ipv6 address fe80::10 link-local` |
| R1 | Ethernet0/0.20 | `ipv6 address 2001:db8:20::1/64` |
| R1 | Ethernet0/0.20 | `ipv6 address fe80::20 link-local` |
| CLIENT-A | Ethernet0/0 | `ipv6 address 2001:db8:10::10/64` |
| CLIENT-B | Ethernet0/0 | `ipv6 address 2001:db8:20::20/64` |

## Tasks

1. Trace real IPv6-only router-on-a-stick forwarding and resolved neighbors across two VLANs.
2. Prune one VLAN and distinguish a still-installed connected route from a broken Layer2 path.
3. Remove and restore an endpoint default route while keeping its on-link gateway healthy.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip interface brief` | The named data interface has no IPv4 address. |
| R1 | `show ip interface brief` | The named data interface has no IPv4 address. |
| R1 | `show ip interface brief` | The named data interface has no IPv4 address. |
| CLIENT-A | `show ip interface brief` | The named data interface has no IPv4 address. |
| CLIENT-B | `show ip interface brief` | The named data interface has no IPv4 address. |
| CLIENT-A | `ping ipv6 2001:db8:20::20 source Ethernet0/0 repeat 3` | The IPv6 endpoint probe actually succeeds. |
| CLIENT-B | `ping ipv6 2001:db8:10::10 source Ethernet0/0 repeat 3` | The IPv6 endpoint probe actually succeeds. |
| R1 | `show ipv6 neighbors` | The router has a resolved neighbor on the actual service subinterface. |

## Transition: prune only the IPv6 service VLAN

On **SW1**:

```ios
configure terminal
interface Ethernet0/0
switchport trunk allowed vlan 10
end
```

- CLIENT-A: `ping ipv6 2001:db8:20::20 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe fails during the controlled fault.
- CLIENT-A: `ping ipv6 2001:db8:10::1 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe actually succeeds.
- R1: `show ipv6 route connected` -- The service prefix remains connected despite the broken trunk membership.

## Transition: restore IPv6 trunk membership

On **SW1**:

```ios
configure terminal
interface Ethernet0/0
switchport trunk allowed vlan 10,20
end
```

- CLIENT-A: `ping ipv6 2001:db8:20::20 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe actually succeeds.
- CLIENT-B: `ping ipv6 2001:db8:10::10 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe actually succeeds.
- R1: `show ipv6 neighbors` -- The router has a resolved neighbor on the actual service subinterface.

## Transition: withdraw only the endpoint IPv6 default

On **CLIENT-A**:

```ios
configure terminal
no ipv6 route ::/0 2001:db8:10::1
end
```

- CLIENT-A: `ping ipv6 2001:db8:20::20 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe fails during the controlled fault.
- CLIENT-A: `ping ipv6 2001:db8:10::1 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe actually succeeds.

## Transition: restore the endpoint IPv6 default

On **CLIENT-A**:

```ios
configure terminal
ipv6 route ::/0 2001:db8:10::1
end
```

- CLIENT-A: `ping ipv6 2001:db8:20::20 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe actually succeeds.
- CLIENT-B: `ping ipv6 2001:db8:10::10 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe actually succeeds.
- R1: `show ipv6 neighbors` -- The router has a resolved neighbor on the actual service subinterface.

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
ipv6 unicast-routing
interface Ethernet0/0
 no shutdown
 exit
interface Ethernet0/0.10
 encapsulation dot1Q 10
 no ip address
 ipv6 address 2001:db8:10::1/64
 no shutdown
 ipv6 address fe80::10 link-local
 exit
interface Ethernet0/0.20
 encapsulation dot1Q 20
 no ip address
 ipv6 address 2001:db8:20::1/64
 no shutdown
 ipv6 address fe80::20 link-local
 exit
end
```

### SW1

```ios
hostname SW1
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
 name USERS
 exit
vlan 20
 name SERVICES
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface Ethernet0/2
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
 no shutdown
 exit
end
```

### CLIENT-A

```ios
hostname CLIENT-A
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
ipv6 unicast-routing
interface Ethernet0/0
 no ip address
 ipv6 address 2001:db8:10::10/64
 no shutdown
 exit
ipv6 route ::/0 2001:db8:10::1
end
```

### CLIENT-B

```ios
hostname CLIENT-B
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
ipv6 unicast-routing
interface Ethernet0/0
 no ip address
 ipv6 address 2001:db8:20::20/64
 no shutdown
 exit
ipv6 route ::/0 2001:db8:20::1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
