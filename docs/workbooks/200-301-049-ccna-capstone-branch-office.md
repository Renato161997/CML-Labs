# CCNA Capstone Branch Office

## Scope and prerequisites

Five isolated guests integrate VLAN access/trunking, DHCP address acquisition, local DNS, PAT and a guest ingress policy. The ISP is a local router loopback, not Internet access. IOSv routers stand in for endpoints: their IP address is acquired by DHCP, while gateway and DNS are explicit model configuration; no DHCP-supplied-route/client-OS behavior is claimed. The guest ACL permits DHCP bootstrap, blocks the user subnet and permits the remaining guest traffic. The data-plane negative target is the user VLAN gateway so no guessed dynamic host address is required. A single-VLAN pruning fault must leave user DNS/PAT working. Nominal memory is 4x512+768 MiB; performance and physical WLAN behavior are outside scope.

Use licensed reference images for iosv, iosvl2 in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- EDGE GigabitEthernet0/0 <-> ISP GigabitEthernet0/0
- EDGE GigabitEthernet0/1 <-> SW1 GigabitEthernet0/0
- SW1 GigabitEthernet0/1 <-> USER GigabitEthernet0/0
- SW1 GigabitEthernet0/2 <-> GUEST GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| EDGE | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| EDGE | GigabitEthernet0/1.10 | `ip address 198.18.10.1 255.255.255.0` |
| EDGE | GigabitEthernet0/1.20 | `ip address 198.18.20.1 255.255.255.0` |
| ISP | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| ISP | Loopback0 | `ip address 203.0.113.80 255.255.255.255` |
| USER | GigabitEthernet0/0 | `ip address dhcp` |
| GUEST | GigabitEthernet0/0 | `ip address dhcp` |

## Tasks

1. Build VLAN-separated DHCP clients behind router-on-a-stick and an explicit guest ACL.
2. Resolve a local test name and prove PAT to an isolated ISP that has no internal return routes.
3. Prune only the guest VLAN, preserve user service, then restore guest forwarding without losing segmentation.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| SW1 | `show vlan brief` | Both named VLANs from day-0 configuration exist and are active. |
| USER | `show ip interface brief` | The endpoint has an actual lease in its own VLAN. |
| GUEST | `show ip interface brief` | The endpoint has an actual lease in its own VLAN. |
| USER | `ping app.example.test repeat 3` | Local DNS resolution and actual NAT/PAT forwarding reach the isolated ISP loopback. |
| GUEST | `ping app.example.test repeat 3` | Local DNS resolution and actual NAT/PAT forwarding reach the isolated ISP loopback. |
| GUEST | `ping 198.18.20.1 repeat 3` | The guest gateway remains reachable. |
| GUEST | `ping 198.18.10.1 repeat 3` | The guest cannot reach the user-subnet gateway. |
| EDGE | `show access-lists GUEST-IN` | The intended segmentation rule counts the actual denied probe. |
| EDGE | `show ip nat translations` | Actual translations map internal endpoint traffic to the outside interface. |
| ISP | `show ip route 198.18.10.0` | The ISP has no customer-subnet route; return traffic depends on PAT. |

## Transition: prune only the guest VLAN

On **SW1**:

```ios
configure terminal
interface GigabitEthernet0/0
switchport trunk allowed vlan 10
end
```

- GUEST: `ping 198.18.20.1 repeat 3` -- Pruned guest frames cannot reach their gateway.
- USER: `ping app.example.test repeat 3` -- Local DNS resolution and actual NAT/PAT forwarding reach the isolated ISP loopback.

## Transition: restore guest trunk membership

On **SW1**:

```ios
configure terminal
interface GigabitEthernet0/0
switchport trunk allowed vlan 10,20
end
```

- GUEST: `ping 198.18.20.1 repeat 3` -- The guest gateway remains reachable.
- GUEST: `ping app.example.test repeat 3` -- Local DNS resolution and actual NAT/PAT forwarding reach the isolated ISP loopback.
- GUEST: `ping 198.18.10.1 repeat 3` -- The guest cannot reach the user-subnet gateway.
- EDGE: `show access-lists GUEST-IN` -- The intended segmentation rule counts the actual denied probe.
- USER: `ping app.example.test repeat 3` -- Local DNS resolution and actual NAT/PAT forwarding reach the isolated ISP loopback.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### EDGE

```ios
hostname EDGE
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
ip dhcp excluded-address 198.18.10.1 198.18.10.9
ip dhcp excluded-address 198.18.20.1 198.18.20.9
ip dhcp pool USERS
 network 198.18.10.0 255.255.255.0
 default-router 198.18.10.1
 dns-server 198.18.10.1
 exit
ip dhcp pool GUESTS
 network 198.18.20.0 255.255.255.0
 default-router 198.18.20.1
 dns-server 198.18.20.1
 exit
ip dns server
ip host app.example.test 203.0.113.80
ip access-list standard NAT-SOURCES
 permit 198.18.10.0 0.0.0.255
 permit 198.18.20.0 0.0.0.255
 exit
ip access-list extended GUEST-IN
 permit udp any eq 68 any eq 67
 deny ip 198.18.20.0 0.0.0.255 198.18.10.0 0.0.0.255
 permit ip 198.18.20.0 0.0.0.255 any
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.1 255.255.255.252
 ip nat outside
 no shutdown
 exit
interface GigabitEthernet0/1
 no ip address
 no shutdown
 exit
interface GigabitEthernet0/1.10
 encapsulation dot1Q 10
 ip address 198.18.10.1 255.255.255.0
 ip nat inside
 exit
interface GigabitEthernet0/1.20
 encapsulation dot1Q 20
 ip address 198.18.20.1 255.255.255.0
 ip nat inside
 ip access-group GUEST-IN in
 exit
ip nat inside source list NAT-SOURCES interface GigabitEthernet0/0 overload
ip route 0.0.0.0 0.0.0.0 198.18.0.2
end
```

### ISP

```ios
hostname ISP
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Loopback0
 ip address 203.0.113.80 255.255.255.255
 no shutdown
 exit
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
no logging console
vlan 10
 name USERS
 exit
vlan 20
 name GUESTS
 exit
interface GigabitEthernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 spanning-tree portfast trunk
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
 switchport access vlan 20
 spanning-tree portfast
 no shutdown
 exit
end
```

### USER

```ios
hostname USER
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
ip domain lookup
ip name-server 198.18.10.1
interface GigabitEthernet0/0
 ip address dhcp
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.10.1
end
```

### GUEST

```ios
hostname GUEST
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
ip domain lookup
ip name-server 198.18.20.1
interface GigabitEthernet0/0
 ip address dhcp
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.20.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
