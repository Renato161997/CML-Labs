# eBGP And iBGP Basics

## Scope and prerequisites

Three IOL-XE routers form AS65001 and AS65002. R1 has no route to the external transit subnet, so preserving R3 next-hop on the internal advertisement makes its received endpoint path inaccessible. Route reception alone is insufficient: the RIB and actual source-loopback traffic must both work. Soft outbound refresh is explicit; no TCP session reset or full Internet table is modeled.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R2 Ethernet0/1 <-> R3 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.12.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.12.2 255.255.255.252` |
| R2 | Ethernet0/1 | `ip address 198.18.23.1 255.255.255.252` |
| R3 | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| R3 | Ethernet0/0 | `ip address 198.18.23.2 255.255.255.252` |

## Tasks

1. Follow the same endpoint routes across an internal and external BGP session.
2. Withdraw next-hop-self without resetting either session and inspect a received but unusable path.
3. Restore the next hop and the actual end-to-end flow.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip route 192.0.2.3` | The iBGP route has a usable internal next hop. |
| R3 | `show ip route 192.0.2.1` | The opposite endpoint is installed through eBGP. |
| R1 | `ping 192.0.2.3 source Loopback0 repeat 3` | The endpoint flow crosses iBGP and eBGP. |

## Transition: preserve the unreachable external next hop

On **R2**:

```ios
configure terminal
router bgp 65001
no neighbor 198.18.12.1 next-hop-self
end
clear ip bgp 198.18.12.1 soft out
```

- R2: `show ip bgp summary | include 198.18.23.2` -- The external peer remains established with one received endpoint.
- R1: `show ip bgp 192.0.2.3` -- The received path identifies the inaccessible external next hop.
- R1: `show ip route 192.0.2.3` -- The unusable BGP path is not installed.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The endpoint flow fails despite a received BGP path.

## Transition: restore an internally reachable next hop

On **R2**:

```ios
configure terminal
router bgp 65001
neighbor 198.18.12.1 next-hop-self
end
clear ip bgp 198.18.12.1 soft out
```

- R1: `show ip route 192.0.2.3` -- The iBGP route has a usable internal next hop.
- R3: `show ip route 192.0.2.1` -- The opposite endpoint is installed through eBGP.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The endpoint flow crosses iBGP and eBGP.

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
interface Ethernet0/0
 ip address 198.18.12.1 255.255.255.252
 no shutdown
 exit
router bgp 65001
 bgp router-id 192.0.2.1
 network 192.0.2.1 mask 255.255.255.255
 neighbor 198.18.12.2 remote-as 65001
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
interface Ethernet0/0
 ip address 198.18.12.2 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.23.1 255.255.255.252
 no shutdown
 exit
router bgp 65001
 bgp router-id 192.0.2.2
 neighbor 198.18.12.1 remote-as 65001
 neighbor 198.18.12.1 next-hop-self
 neighbor 198.18.23.2 remote-as 65002
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
 ip address 192.0.2.3 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.23.2 255.255.255.252
 no shutdown
 exit
router bgp 65002
 bgp router-id 192.0.2.3
 network 192.0.2.3 mask 255.255.255.255
 neighbor 198.18.23.1 remote-as 65001
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
