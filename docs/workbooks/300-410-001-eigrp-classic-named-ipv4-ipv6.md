# EIGRP Classic Named IPv4 IPv6

## Scope and prerequisites

Requires IOL-XE. The autonomous-system number must match in each address family even though the configuration styles differ. A successful IPv4 adjacency does not prove IPv6 is working.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Loopback0 | `ipv6 address 2001:db8:1::1/128` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Ethernet0/0 | `ipv6 address 2001:db8:12::1/64` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Loopback0 | `ipv6 address 2001:db8:2::2/128` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Ethernet0/0 | `ipv6 address 2001:db8:12::2/64` |

## Tasks

1. Compare classic configuration on R1 with named address families on R2.
2. Verify independent IPv4 and IPv6 adjacencies and learned routes.
3. Prove both address families forward between the endpoint loopbacks.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip eigrp neighbors` | Classic IPv4 peers with the named IPv4 address family. |
| R1 | `show ipv6 eigrp neighbors` | IPv6 has an independently established adjacency. |
| R1 | `show ipv6 route eigrp` | The remote IPv6 endpoint is learned dynamically. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |
| R1 | `ping ipv6 2001:db8:2::2 source Loopback0 repeat 3` | IPv6 endpoint forwarding succeeds. |

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
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface Loopback0
 ipv6 address 2001:db8:1::1/128
 exit
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 ipv6 address 2001:db8:12::1/64
 exit
router eigrp 100
 network 198.18.0.0 0.0.0.3
 network 192.0.2.1 0.0.0.0
 passive-interface Loopback0
 no auto-summary
 exit
ipv6 router eigrp 100
 eigrp router-id 192.0.2.1
 no shutdown
 exit
interface Ethernet0/0
 ipv6 eigrp 100
 exit
interface Loopback0
 ipv6 eigrp 100
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
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface Loopback0
 ipv6 address 2001:db8:2::2/128
 exit
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 ipv6 address 2001:db8:12::2/64
 exit
router eigrp LAB
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 192.0.2.2
  network 198.18.0.0 0.0.0.3
  network 192.0.2.2 0.0.0.0
  af-interface Loopback0
   passive-interface
  exit-af-interface
 exit-address-family
 address-family ipv6 unicast autonomous-system 100
  eigrp router-id 192.0.2.2
  af-interface Ethernet0/0
   no shutdown
  exit-af-interface
  af-interface Loopback0
   passive-interface
   no shutdown
  exit-af-interface
  no shutdown
 exit-address-family
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
