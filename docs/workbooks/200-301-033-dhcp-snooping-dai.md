# DHCP Snooping And DAI

## Scope and prerequisites

Requires IOSvL2 plus three IOL-XE nodes, nominally 3.75 GiB. Cisco documents DHCP snooping and Dynamic ARP Inspection for IOSvL2; this scenario still requires its own observed pass. Only the DHCP server port is trusted. Option 82 insertion is disabled for this direct, non-relayed DHCP setup. SPOOFER deliberately duplicates the first client lease on a different untrusted port, starts administratively down and is activated only during the controlled fault. No external connector is present. DAI stays enabled throughout; clearing statistics affects only this disposable one-VLAN switch.

Use licensed reference images for iol-xe, iosvl2 in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SERVER Ethernet0/0 <-> SW1 GigabitEthernet0/0
- CLIENT Ethernet0/0 <-> SW1 GigabitEthernet0/1
- SPOOFER Ethernet0/0 <-> SW1 GigabitEthernet0/2

| Node | Interface | Address |
| --- | --- | --- |
| SERVER | Ethernet0/0 | `ip address 198.18.10.1 255.255.255.0` |
| CLIENT | Ethernet0/0 | `ip address dhcp` |
| SPOOFER | Ethernet0/0 | `ip address 198.18.10.100 255.255.255.0` |

## Tasks

1. Inspect a real trusted-server DHCP lease and its switch binding.
2. Activate an isolated static-IP impersonator on another untrusted access port.
3. Observe DAI drops while the legitimate client keeps forwarding, then remove the impersonator and retest with fresh ARP.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `show ip interface brief` | The legitimate client actually holds the first DHCP lease. |
| SW1 | `show ip dhcp snooping binding` | The real DHCP lease is bound to the legitimate client port. |
| CLIENT | `ping 198.18.10.1 repeat 3` | All three probes succeed. |

## Transition: fresh baseline counters

On **SW1**:

```ios
clear ip arp inspection statistics
```

- SW1: `show ip arp inspection statistics vlan 10` -- The Forwarded/Dropped table contains no dropped ARP packets.
- SW1: `show ip dhcp snooping binding` -- The real DHCP lease is bound to the legitimate client port.

## Transition: static address impersonation

On **SPOOFER**:

```ios
configure terminal
interface Ethernet0/0
no shutdown
end
```

- SPOOFER: `ping 198.18.10.1 repeat 3` -- The protected segment drops all three probes.
- SW1: `show ip arp inspection statistics vlan 10` -- The Forwarded/Dropped table records actual DHCP-binding-related ARP drops.
- SW1: `show interfaces status` -- The offending port remains physically connected; filtering is not a link shutdown.
- CLIENT: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- SW1: `show ip dhcp snooping binding` -- The real DHCP lease is bound to the legitimate client port.

## Transition: remove impersonating endpoint

On **SPOOFER**:

```ios
configure terminal
interface Ethernet0/0
shutdown
end
```

- SPOOFER: `show ip interface brief` -- The deliberate impersonator has been stopped.

## Transition: prepare legitimate ARP measurement

On **SW1**:

```ios
clear ip arp inspection statistics
```

- SW1: `show ip arp inspection statistics vlan 10` -- The Forwarded/Dropped table contains no dropped ARP packets.
- SW1: `show ip dhcp snooping binding` -- The real DHCP lease is bound to the legitimate client port.

## Transition: fresh legitimate ARP

On **CLIENT**:

```ios
clear arp-cache
```

- CLIENT: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- SW1: `show ip arp inspection statistics vlan 10` -- Fresh ARP from the bound client is actually permitted, measured in the DHCP Permits table.
- SW1: `show ip arp inspection statistics vlan 10` -- The Forwarded/Dropped table contains no dropped ARP packets.
- SW1: `show ip dhcp snooping binding` -- The real DHCP lease is bound to the legitimate client port.
- SW1: `show running-config | include ip arp inspection vlan` -- DAI remains enabled after recovery.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

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
interface range GigabitEthernet0/0 - 3
 shutdown
 exit
vlan 10
 name CLIENTS
 exit
ip dhcp snooping
ip dhcp snooping vlan 10
no ip dhcp snooping information option
ip arp inspection vlan 10
interface GigabitEthernet0/0
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 ip dhcp snooping trust
 ip arp inspection trust
 no shutdown
 exit
interface GigabitEthernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface GigabitEthernet0/2
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
end
```

### SERVER

```ios
hostname SERVER
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
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 exit
ip dhcp excluded-address 198.18.10.1 198.18.10.99
ip dhcp pool CLIENTS
 network 198.18.10.0 255.255.255.0
 default-router 198.18.10.1
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
 ip address dhcp
 no shutdown
 exit
end
```

### SPOOFER

```ios
hostname SPOOFER
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
 ip address 198.18.10.100 255.255.255.0
 no shutdown
 shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

Platform capability reference: [Cisco IOSvL2](https://developer.cisco.com/docs/modeling-labs/iosvl2/). [Cisco DAI configuration and monitoring](https://www.cisco.com/c/en/us/td/docs/switches/lan/c9000/sec-crypto/fhs-sisf/fhs-and-sisf-configuration-guide/dynamic-arp-inspection.html) explains binding checks; consult the live evidence for this specific IOS image.
