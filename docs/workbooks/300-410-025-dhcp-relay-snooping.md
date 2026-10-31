# DHCP Relay Snooping

## Scope and prerequisites

An IOSvL2 access switch, IOL-XE DHCP client, separate relay and remote DHCP server exercise actual DHCP forwarding. The client VLAN is198.18.10.0/24, the server transport is198.18.0.0/30, the helper targets0.2, and the server has an explicit route back to the client VLAN. Only100 is leasable. The relay-facing access port is the trusted trusted relay-uplink boundary; option82 insertion is disabled to isolate port trust from option82/giaddr policy. Removing snooping trust alone must not invalidate already-working IP traffic. Resetting the client DHCP configuration then requires a fresh eligible relay path: the client must stay unassigned across two independent unanswered router-probe windows, with an actual buffered DHCPDISCOVER event immediately followed by the switch decision that the eligible output-port set is empty and the packet is dropped. On the observed image, removing the only trusted uplink stops request forwarding before a new server reply can be required; the exercise does not claim that a DHCPOFFER was received and dropped. The tested image did not advance its aggregate drop statistic, so that counter is not treated as authoritative packet evidence. Packet debugging is enabled only for this isolated controlled fault, buffered with console logging disabled, and explicitly turned off during repair. Restoring only the switch trust must recover lease/binding and bidirectional routed traffic. This tests a single-switch relay trust boundary, not rogue-server authentication, DHCPv6 or a production NAC deployment. Nominal RAM is3840MiB. Packet-debug and drop-log syntax: https://www.cisco.com/c/en/us/support/docs/ip/dynamic-host-configuration-protocol-dhcp-dhcpv6/217055-operate-and-troubleshoot-dhcp-snooping.html .

Use licensed reference images for iol-xe, iosvl2 in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- CLIENT Ethernet0/0 <-> SW GigabitEthernet0/1
- RELAY Ethernet0/0 <-> SW GigabitEthernet0/0
- RELAY Ethernet0/1 <-> SERVER Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| RELAY | Ethernet0/0 | `ip address 198.18.10.1 255.255.255.0` |
| RELAY | Ethernet0/1 | `ip address 198.18.0.1 255.255.255.252` |
| SERVER | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| CLIENT | Ethernet0/0 | `ip address dhcp` |

## Tasks

1. Acquire a remote-server DHCP lease through an actual helper and correlate the resulting snooping binding.
2. Remove only the trusted relay-facing switch port, keep an existing lease working, then reset only client DHCP acquisition.
3. Observe sustained failed reacquisition and actual snooping packet-drop decisions, restore trust and recover the same routed client service.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `show ip interface brief` | The client actually receives its remote-subnet DHCP lease through the relay. |
| SW | `show ip dhcp snooping binding` | The actual relayed lease binds the client MAC/address/VLAN and this access-switch ingress. |
| CLIENT | `ping 198.18.10.1 repeat 3` | All three probes succeed. |
| CLIENT | `ping 198.18.0.2 repeat 3` | All three probes succeed. |
| SERVER | `ping 198.18.10.100 repeat 3` | All three probes succeed. |

## Transition: remove only relay-facing snooping trust

On **SW**:

```ios
configure terminal
interface GigabitEthernet0/0
no ip dhcp snooping trust
exit
do debug ip dhcp snooping packet
end
```

- CLIENT: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- CLIENT: `ping 198.18.0.2 repeat 3` -- All three probes succeed.

## Transition: force fresh acquisition through the untrusted reply port

On **CLIENT**:

```ios
configure terminal
interface Ethernet0/0
shutdown
no ip address dhcp
ip address dhcp
no shutdown
end
```

- RELAY: `ping 198.18.10.100 repeat 5 timeout 2` -- An independent router observes a complete unanswered client window while reacquisition is blocked.
- CLIENT: `show ip interface brief` -- The new DHCP acquisition remains unassigned with the server-reply port untrusted.
- RELAY: `ping 198.18.10.100 repeat 5 timeout 2` -- An independent router observes a complete unanswered client window while reacquisition is blocked.
- SW: `show running-config interface GigabitEthernet0/0` -- The relay-facing VLAN10 port has no trust exception during the measured failure.
- SW: `show logging | include DHCPDISCOVER|output port set` -- A fresh DHCPDISCOVER is followed by the actual switch decision to drop it because no eligible trusted output port remains.
- CLIENT: `show ip interface brief` -- The new DHCP acquisition remains unassigned with the server-reply port untrusted.

## Transition: restore the legitimate reply boundary

On **SW**:

```ios
configure terminal
interface GigabitEthernet0/0
ip dhcp snooping trust
exit
do undebug all
end
```

- CLIENT: `show ip interface brief` -- The client actually receives its remote-subnet DHCP lease through the relay.
- SW: `show ip dhcp snooping binding` -- The actual relayed lease binds the client MAC/address/VLAN and this access-switch ingress.
- CLIENT: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- CLIENT: `ping 198.18.0.2 repeat 3` -- All three probes succeed.
- SERVER: `ping 198.18.10.100 repeat 3` -- All three probes succeed.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### SW

```ios
hostname SW
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
vtp mode transparent
spanning-tree mode rapid-pvst
no logging console
logging buffered 64000 debugging
vlan 10
 name RELAY-CLIENTS
 exit
ip dhcp snooping
ip dhcp snooping vlan 10
no ip dhcp snooping information option
interface GigabitEthernet0/0
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 ip dhcp snooping trust
 no shutdown
 exit
interface GigabitEthernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
end
```

### RELAY

```ios
hostname RELAY
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
 ip helper-address 198.18.0.2
 exit
interface Ethernet0/1
 ip address 198.18.0.1 255.255.255.252
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
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
ip route 198.18.10.0 255.255.255.0 198.18.0.1
ip dhcp excluded-address 198.18.10.1 198.18.10.99
ip dhcp excluded-address 198.18.10.101 198.18.10.254
ip dhcp pool REMOTE-CLIENTS
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
 mac-address 0200.0000.1002
 ip address dhcp
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
