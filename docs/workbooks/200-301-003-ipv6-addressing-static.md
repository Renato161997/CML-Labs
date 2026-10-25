# IPv6 Addressing Static

## Scope and prerequisites

Requires IOL-XE. The shared /64 is directly connected; no IPv6 static route is needed. The link-local address has interface-local scope and is independent of the global address. This models addressing and Neighbor Discovery, not DHCPv6 or SLAAC.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Ethernet0/0 | `ipv6 address fe80::1 link-local` |
| R1 | Ethernet0/0 | `ipv6 address 2001:db8:12::1/64` |
| R2 | Ethernet0/0 | `ipv6 address fe80::2 link-local` |
| R2 | Ethernet0/0 | `ipv6 address 2001:db8:12::2/64` |

## Tasks

1. Identify statically configured global and link-local addresses.
2. Verify actual neighbor discovery without an IPv4 dependency.
3. Remove and restore only the global address while preserving the local link.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping ipv6 2001:db8:12::2 repeat 3` | The global-scope address is reachable. |
| R1 | `show ipv6 neighbors` | Neighbor Discovery resolves the directly connected peer. |
| R2 | `show ipv6 interface Ethernet0/0` | The explicitly configured link-local address is present. |

## Transition: global address removed

On **R2**:

```ios
configure terminal
interface Ethernet0/0
no ipv6 address 2001:db8:12::2/64
end
```

- R1: `ping ipv6 2001:db8:12::2 repeat 3` -- The removed global address no longer replies.
- R2: `show ipv6 interface Ethernet0/0` -- The link-local identity remains configured.

## Transition: global address restored

On **R2**:

```ios
configure terminal
interface Ethernet0/0
ipv6 address 2001:db8:12::2/64
end
```

- R1: `ping ipv6 2001:db8:12::2 repeat 3` -- The global-scope address is reachable.

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
 no ip address
 ipv6 enable
 ipv6 address fe80::1 link-local
 ipv6 address 2001:db8:12::1/64
 no shutdown
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
interface Ethernet0/0
 no ip address
 ipv6 enable
 ipv6 address fe80::2 link-local
 ipv6 address 2001:db8:12::2/64
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
