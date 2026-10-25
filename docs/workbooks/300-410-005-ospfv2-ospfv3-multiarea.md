# OSPFv2 OSPFv3 Multiarea

## Scope and prerequisites

Requires IOL-XE. R2 is the ABR for two independent OSPF processes: OSPFv2 carries IPv4 and OSPFv3 carries IPv6. Documentation prefixes are used throughout; no redistribution between protocols is configured.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R2 Ethernet0/1 <-> R3 Ethernet0/0

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
| R2 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| R2 | Ethernet0/1 | `ipv6 address 2001:db8:23::2/64` |
| R3 | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| R3 | Loopback0 | `ipv6 address 2001:db8:3::3/128` |
| R3 | Ethernet0/0 | `ip address 198.18.1.2 255.255.255.252` |
| R3 | Ethernet0/0 | `ipv6 address 2001:db8:23::3/64` |

## Tasks

1. Identify the ABR between backbone area 0 and area 10.
2. Compare IPv4 and IPv6 inter-area routes.
3. Prove bidirectional endpoint forwarding in both address families.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip route ospf` | OSPFv2 installs an inter-area route. |
| R1 | `show ipv6 route ospf` | OSPFv3 separately installs its inter-area route. |
| R1 | `ping 192.0.2.3 source Loopback0 repeat 3` | Three replies. |
| R1 | `ping ipv6 2001:db8:3::3 source Loopback0 repeat 3` | IPv6 forwards through the ABR. |

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
 ip ospf 1 area 0
 ipv6 ospf 10 area 0
 exit
router ospf 1
 router-id 192.0.2.1
 passive-interface Loopback0
 exit
ipv6 router ospf 10
 router-id 192.0.2.1
 passive-interface Loopback0
 exit
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 ipv6 address 2001:db8:12::1/64
 ip ospf 1 area 0
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
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface Loopback0
 ipv6 address 2001:db8:2::2/128
 ip ospf 1 area 0
 ipv6 ospf 10 area 0
 exit
router ospf 1
 router-id 192.0.2.2
 passive-interface Loopback0
 exit
ipv6 router ospf 10
 router-id 192.0.2.2
 passive-interface Loopback0
 exit
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 ipv6 address 2001:db8:12::2/64
 ip ospf 1 area 0
 ipv6 ospf 10 area 0
 exit
interface Ethernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 ipv6 address 2001:db8:23::2/64
 ip ospf 1 area 10
 ipv6 ospf 10 area 10
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
ipv6 unicast-routing
interface Loopback0
 ip address 192.0.2.3 255.255.255.255
 no shutdown
 exit
interface Loopback0
 ipv6 address 2001:db8:3::3/128
 ip ospf 1 area 10
 ipv6 ospf 10 area 10
 exit
router ospf 1
 router-id 192.0.2.3
 passive-interface Loopback0
 exit
ipv6 router ospf 10
 router-id 192.0.2.3
 passive-interface Loopback0
 exit
interface Ethernet0/0
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 ipv6 address 2001:db8:23::3/64
 ip ospf 1 area 10
 ipv6 ospf 10 area 10
 exit
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
