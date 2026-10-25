# OSI TCP/IP Traffic Path

## Scope and prerequisites

Requires IOL-XE and IOL-L2 XE. Loopbacks represent the IP endpoints, and the intermediate switch forwards VLAN 10 without IP routing. A ping alone cannot explain which layer supplied ARP, the forwarding entry or the IP next hop: inspect the separate tables. This is a live protocol exercise, not a packet-level simulator of every OSI layer.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> SW1 Ethernet0/0
- R2 Ethernet0/0 <-> SW1 Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Trace the endpoint IP route separately from the Ethernet next hop.
2. Observe actual ARP resolution and switch MAC learning.
3. Separate local interface state, Ethernet forwarding and endpoint reachability.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |
| R1 | `show ip route 192.0.2.2` | The IP next hop is the peer transit address. |
| R1 | `show arp 198.18.0.2` | ARP has learned the transit peer MAC. |
| SW1 | `show mac address-table dynamic` | The bridge learns real source MACs on both access ports. |

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
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.2 255.255.255.255 198.18.0.2
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
 name TRANSIT
interface range Ethernet0/0 - 1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
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
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.1 255.255.255.255 198.18.0.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
