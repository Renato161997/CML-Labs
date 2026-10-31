# Small Office Full Stack

## Scope and prerequisites

This four-node office integrates an IOSv edge router, IOSvL2 access switch, IOL-XE DHCP client and a separate routed service. The router-on-a-stick client VLAN10 carries198.18.10.0/24, DHCP offers only100 and its default router, and CLIENT uses a DHCP-dependent static default. The WAN198.18.0.0/30 leads to SERVER loopback192.0.2.80. SERVER deliberately has no private-client return route, so a successful client probe plus an observed ICMP PAT entry proves real source translation. Removing only the inside NAT role and clearing disposable translations must break the remote client service while preserving the local gateway and GW-to-service reachability. Restoring it must recreate working PAT. A separate trunk-pruning fault must instead break client gateway reachability while the WAN remains healthy. Recovery requires actual lease, default, local and remote traffic, translation and absent private return route. This compact full-stack exercise covers L2, DHCP, routing and PAT; it does not instantiate DNS, WiFi, a stateful firewall or an Internet connection. Nominal RAM is3328MiB.

Use licensed reference images for iol-xe, iosv, iosvl2 in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- GW GigabitEthernet0/0 <-> SW GigabitEthernet0/0
- CLIENT Ethernet0/0 <-> SW GigabitEthernet0/1
- GW GigabitEthernet0/1 <-> SERVER Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| GW | GigabitEthernet0/1 | `ip address 198.18.0.1 255.255.255.252` |
| GW | GigabitEthernet0/0.10 | `ip address 198.18.10.1 255.255.255.0` |
| CLIENT | Ethernet0/0 | `ip address dhcp` |
| SERVER | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| SERVER | Loopback0 | `ip address 192.0.2.80 255.255.255.255` |

## Tasks

1. Correlate VLAN access/trunk forwarding, a real DHCP lease/default route and actual PAT-dependent remote service.
2. Break only NAT classification while retaining client gateway and WAN service controls.
3. Recover NAT, prune only the client VLAN from the trunk, then restore the complete office path.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `show ip interface brief` | The office client actually acquires the only available DHCP lease. |
| CLIENT | `show ip route 0.0.0.0` | The DHCP-dependent static default resolves to the actual advertised gateway. |
| CLIENT | `ping 198.18.10.1 repeat 3` | All three probes succeed. |
| CLIENT | `ping 192.0.2.80 repeat 3` | All three probes succeed. |
| GW | `show ip nat translations` | An actual client ICMP translation uses the WAN address, not a configured NAT string. |
| SERVER | `show ip route 198.18.10.100` | The service has no route back to the private client; successful replies depend on actual PAT. |

## Transition: remove only client source translation

On **GW**:

```ios
configure terminal
interface GigabitEthernet0/0.10
no ip nat inside
exit
do clear ip nat translation *
end
```

- CLIENT: `ping 192.0.2.80 repeat 3` -- The protected segment drops all three probes.
- CLIENT: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- GW: `ping 192.0.2.80 repeat 3` -- All three probes succeed.
- SERVER: `show ip route 198.18.10.100` -- The service has no route back to the private client; successful replies depend on actual PAT.

## Transition: recover actual source translation

On **GW**:

```ios
configure terminal
interface GigabitEthernet0/0.10
ip nat inside
end
```

- CLIENT: `show ip interface brief` -- The office client actually acquires the only available DHCP lease.
- CLIENT: `show ip route 0.0.0.0` -- The DHCP-dependent static default resolves to the actual advertised gateway.
- CLIENT: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- CLIENT: `ping 192.0.2.80 repeat 3` -- All three probes succeed.
- GW: `show ip nat translations` -- An actual client ICMP translation uses the WAN address, not a configured NAT string.
- SERVER: `show ip route 198.18.10.100` -- The service has no route back to the private client; successful replies depend on actual PAT.

## Transition: prune only the office VLAN

On **SW**:

```ios
configure terminal
interface GigabitEthernet0/0
switchport trunk allowed vlan 20
end
```

- CLIENT: `ping 198.18.10.1 repeat 3` -- The protected segment drops all three probes.
- SERVER: `ping 198.18.0.1 repeat 3` -- All three probes succeed.
- CLIENT: `show ip interface brief` -- The office client actually acquires the only available DHCP lease.

## Transition: recover the office trunk

On **SW**:

```ios
configure terminal
interface GigabitEthernet0/0
switchport trunk allowed vlan 10
end
```

- CLIENT: `show ip interface brief` -- The office client actually acquires the only available DHCP lease.
- CLIENT: `show ip route 0.0.0.0` -- The DHCP-dependent static default resolves to the actual advertised gateway.
- CLIENT: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- CLIENT: `ping 192.0.2.80 repeat 3` -- All three probes succeed.
- GW: `show ip nat translations` -- An actual client ICMP translation uses the WAN address, not a configured NAT string.
- SERVER: `show ip route 198.18.10.100` -- The service has no route back to the private client; successful replies depend on actual PAT.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### GW

```ios
hostname GW
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
interface GigabitEthernet0/1
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 ip nat outside
 exit
interface GigabitEthernet0/0
 no ip address
 no shutdown
 exit
interface GigabitEthernet0/0.10
 encapsulation dot1Q 10
 ip address 198.18.10.1 255.255.255.0
 ip nat inside
 exit
ip dhcp excluded-address 198.18.10.1 198.18.10.99
ip dhcp excluded-address 198.18.10.101 198.18.10.254
ip dhcp pool OFFICE
 network 198.18.10.0 255.255.255.0
 default-router 198.18.10.1
 exit
ip access-list standard OFFICE-NAT
 permit 198.18.10.0 0.0.0.255
 exit
ip nat inside source list OFFICE-NAT interface GigabitEthernet0/1 overload
ip route 0.0.0.0 0.0.0.0 198.18.0.2
end
```

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
vlan 10
 name OFFICE
 exit
interface GigabitEthernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
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
ip route 0.0.0.0 0.0.0.0 dhcp
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
interface Loopback0
 ip address 192.0.2.80 255.255.255.255
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
