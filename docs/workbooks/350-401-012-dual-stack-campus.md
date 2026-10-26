# Dual Stack Campus

## Scope and prerequisites

Three IOL reference nodes form a dual-stack routed campus. Documentation IPv6 prefixes and benchmark IPv4 addresses are used. Router images act as observable endpoints and have explicit IPv4/IPv6 default routes. The fault is a global IPv6 forwarding change on CORE; it does not shut a physical link or claim to model wireless or FHRP.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- HOST10 Ethernet0/0 <-> CORE Ethernet0/0
- HOST20 Ethernet0/0 <-> CORE Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| CORE | Vlan10 | `ip address 198.18.10.1 255.255.255.0` |
| CORE | Vlan10 | `ipv6 address 2001:db8:10::1/64` |
| CORE | Vlan20 | `ip address 198.18.20.1 255.255.255.0` |
| CORE | Vlan20 | `ipv6 address 2001:db8:20::1/64` |
| HOST10 | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |
| HOST10 | Ethernet0/0 | `ipv6 address 2001:db8:10::10/64` |
| HOST20 | Ethernet0/0 | `ip address 198.18.20.20 255.255.255.0` |
| HOST20 | Ethernet0/0 | `ipv6 address 2001:db8:20::20/64` |

## Tasks

1. Verify independent IPv4 and IPv6 forwarding between real VLAN endpoints.
2. Disable only IPv6 forwarding and distinguish a responding gateway from a working routed path.
3. Restore IPv6 while checking that IPv4 remained available.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| HOST10 | `ping 198.18.20.20 repeat 3` | IPv4 crosses the routed VLAN boundary. |
| HOST10 | `ping ipv6 2001:db8:20::20 source Ethernet0/0 repeat 3` | IPv6 crosses the same routed VLAN boundary. |

## Transition: IPv6 forwarding disabled

On **CORE**:

```ios
configure terminal
no ipv6 unicast-routing
end
```

- HOST10: `ping 198.18.20.20 repeat 3` -- IPv4 crosses the routed VLAN boundary.
- HOST10: `ping ipv6 2001:db8:10::1 source Ethernet0/0 repeat 3` -- The local IPv6 gateway still responds.
- HOST10: `ping ipv6 2001:db8:20::20 source Ethernet0/0 repeat 3` -- IPv6 transit fails independently of IPv4.

## Transition: IPv6 forwarding restored

On **CORE**:

```ios
configure terminal
ipv6 unicast-routing
end
```

- HOST10: `ping 198.18.20.20 repeat 3` -- IPv4 crosses the routed VLAN boundary.
- HOST10: `ping ipv6 2001:db8:20::20 source Ethernet0/0 repeat 3` -- IPv6 crosses the same routed VLAN boundary.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### CORE

```ios
hostname CORE
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
vlan 10
 name USERS
 exit
vlan 20
 name SERVICES
 exit
ipv6 unicast-routing
interface Vlan10
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 ipv6 enable
 ipv6 address 2001:db8:10::1/64
 exit
interface Vlan20
 ip address 198.18.20.1 255.255.255.0
 no shutdown
 ipv6 enable
 ipv6 address 2001:db8:20::1/64
 exit
interface Ethernet0/0
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface Ethernet0/1
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
 no shutdown
 exit
end
```

### HOST10

```ios
hostname HOST10
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
 ip address 198.18.10.10 255.255.255.0
 no shutdown
 ipv6 enable
 ipv6 address 2001:db8:10::10/64
 exit
ip route 0.0.0.0 0.0.0.0 198.18.10.1
ipv6 route ::/0 2001:db8:10::1
end
```

### HOST20

```ios
hostname HOST20
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
 ip address 198.18.20.20 255.255.255.0
 no shutdown
 ipv6 enable
 ipv6 address 2001:db8:20::20/64
 exit
ip route 0.0.0.0 0.0.0.0 198.18.20.1
ipv6 route ::/0 2001:db8:20::1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
