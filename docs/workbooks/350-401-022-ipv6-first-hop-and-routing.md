# IPv6 First Hop And Routing

## Scope and prerequisites

Three IOL-XE reference nodes integrate an actual SLAAC client and RA-derived default with a two-router OSPFv3 path. The CLIENT model is an IOS router configured with ipv6 address autoconfig default and no manually configured global address or default route. RA transmissions from CLIENT are suppressed. R1 advertises the LAN prefix and a30-second default-router lifetime every5seconds. IPv4-format OSPF router IDs are identifiers; no data interface is assigned an IPv4 address. A zero RA lifetime must remove the client default while its global address and local gateway remain usable and R1 still reaches R2. A separate transit-area mismatch must remove the service OSPF route while the client ND default and local gateway remain. This does not claim a particular desktop OS or physical first-hop security implementation. Nominal RAM is3GiB. Command background: https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/ipv6/command/ipv6-cr-book/ipv6-i1.html .

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- CLIENT Ethernet0/0 <-> R1 Ethernet0/0
- R1 Ethernet0/1 <-> R2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Ethernet0/1 | `ipv6 address 2001:db8:12::1/64` |
| R1 | Ethernet0/1 | `ipv6 address fe80::b link-local` |
| R1 | Ethernet0/0 | `ipv6 address 2001:db8:10::1/64` |
| R1 | Ethernet0/0 | `ipv6 address fe80::1 link-local` |
| R2 | Ethernet0/0 | `ipv6 address 2001:db8:12::2/64` |
| R2 | Ethernet0/0 | `ipv6 address fe80::c link-local` |
| R2 | Loopback0 | `ipv6 address 2001:db8:2::2/128` |
| CLIENT | Ethernet0/0 | `ipv6 address autoconfig default` |

## Tasks

1. Verify a real SLAAC prefix, an ND-derived default and a separate OSPFv3 service route.
2. Withdraw RA default-router lifetime while preserving on-link ND and upstream routing.
3. Break the transit OSPF area and distinguish that failure from a healthy first hop.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `show ipv6 interface Ethernet0/0` | The client actually acquires a global address from the RA prefix. |
| CLIENT | `show ipv6 route` | The actual ND-derived default points to the advertising first hop. |
| R1 | `show ipv6 ospf neighbor` | OSPFv3 has a real FULL transit adjacency. |
| R1 | `show ipv6 route ospf` | OSPFv3 actually installs the service loopback. |
| CLIENT | `ping ipv6 2001:db8:10::1 source Ethernet0/0 repeat 3` | The IPv6 endpoint probe actually succeeds. |
| CLIENT | `ping ipv6 2001:db8:2::2 source Ethernet0/0 repeat 3` | The IPv6 endpoint probe actually succeeds. |

## Transition: withdraw only the RA default-router lifetime

On **R1**:

```ios
configure terminal
interface Ethernet0/0
ipv6 nd ra lifetime 0
end
```

- CLIENT: `show ipv6 route` -- The router-advertisement default has actually been withdrawn.
- CLIENT: `show ipv6 interface Ethernet0/0` -- The client actually acquires a global address from the RA prefix.
- CLIENT: `ping ipv6 2001:db8:10::1 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe actually succeeds.
- CLIENT: `ping ipv6 2001:db8:2::2 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe fails during the controlled fault.
- R1: `show ipv6 ospf neighbor` -- OSPFv3 has a real FULL transit adjacency.
- R1: `ping ipv6 2001:db8:2::2 source Ethernet0/1 repeat 3` -- Upstream IPv6 routing remains healthy without the client default.

## Transition: restore the advertised default lifetime

On **R1**:

```ios
configure terminal
interface Ethernet0/0
ipv6 nd ra lifetime 30
end
```

- CLIENT: `show ipv6 route` -- The actual ND-derived default points to the advertising first hop.
- CLIENT: `ping ipv6 2001:db8:2::2 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe actually succeeds.

## Transition: mismatch only the remote transit OSPF area

On **R2**:

```ios
configure terminal
interface Ethernet0/0
no ipv6 ospf 10 area 0
ipv6 ospf 10 area 10
end
```

- R1: `show ipv6 route ospf` -- The service route is withdrawn after adjacency loss.
- CLIENT: `ping ipv6 2001:db8:2::2 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe fails during the controlled fault.
- CLIENT: `show ipv6 route` -- The actual ND-derived default points to the advertising first hop.
- CLIENT: `ping ipv6 2001:db8:10::1 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe actually succeeds.

## Transition: restore transit area agreement

On **R2**:

```ios
configure terminal
interface Ethernet0/0
no ipv6 ospf 10 area 10
ipv6 ospf 10 area 0
end
```

- R1: `show ipv6 ospf neighbor` -- OSPFv3 has a real FULL transit adjacency.
- R1: `show ipv6 route ospf` -- OSPFv3 actually installs the service loopback.
- CLIENT: `ping ipv6 2001:db8:2::2 source Ethernet0/0 repeat 3` -- The IPv6 endpoint probe actually succeeds.
- CLIENT: `show ipv6 route` -- The actual ND-derived default points to the advertising first hop.

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
ipv6 router ospf 10
 router-id 192.0.2.1
 passive-interface Ethernet0/0
 exit
interface Ethernet0/1
 no ip address
 ipv6 address 2001:db8:12::1/64
 no shutdown
 ipv6 address fe80::b link-local
 ipv6 ospf 10 area 0
 ipv6 ospf hello-interval 2
 ipv6 ospf dead-interval 8
 exit
interface Ethernet0/0
 no ip address
 ipv6 address 2001:db8:10::1/64
 no shutdown
 ipv6 address fe80::1 link-local
 ipv6 nd ra interval 5
 ipv6 nd ra lifetime 30
 ipv6 ospf 10 area 0
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
ipv6 unicast-routing
ipv6 router ospf 10
 router-id 192.0.2.2
 passive-interface Loopback0
 exit
interface Ethernet0/0
 no ip address
 ipv6 address 2001:db8:12::2/64
 no shutdown
 ipv6 address fe80::c link-local
 ipv6 ospf 10 area 0
 ipv6 ospf hello-interval 2
 ipv6 ospf dead-interval 8
 exit
interface Loopback0
 no ip address
 ipv6 address 2001:db8:2::2/128
 no shutdown
 ipv6 ospf 10 area 0
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
ipv6 unicast-routing
interface Ethernet0/0
 mac-address 0200.0000.1002
 no ip address
 ipv6 address autoconfig default
 ipv6 nd ra suppress all
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
