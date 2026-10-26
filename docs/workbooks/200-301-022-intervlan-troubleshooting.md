# Inter-VLAN Routing Troubleshooting

## Scope and prerequisites

Requires four IOL reference nodes, nominally 4 GiB in total. SW1 is a Layer-2 switch with no routing SVIs; traffic between USERS and SERVICES must actually cross R1. A wrong tag on Ethernet0/0.20 can break the service VLAN despite apparently correct IP addresses and an up physical interface. Both clients have explicit return/default routes. All addresses and deliberate fault actions are isolated to this imported copy.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> SW1 Ethernet0/0
- USERS Ethernet0/0 <-> SW1 Ethernet0/1
- SERVICES Ethernet0/0 <-> SW1 Ethernet0/2

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Ethernet0/0.10 | `ip address 198.18.10.1 255.255.255.0` |
| R1 | Ethernet0/0.20 | `ip address 198.18.20.1 255.255.255.0` |
| USERS | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |
| SERVICES | Ethernet0/0 | `ip address 198.18.20.20 255.255.255.0` |

## Tasks

1. Trace actual inter-VLAN traffic between two independent clients.
2. Introduce a router encapsulation mismatch while leaving IP addressing and the physical trunk intact.
3. Restore the correct tag and verify forward and return traffic.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| USERS | `ping 198.18.10.1 repeat 3` | All three probes succeed. |
| USERS | `ping 198.18.20.20 repeat 3` | All three probes succeed. |
| SERVICES | `ping 198.18.10.10 repeat 3` | All three probes succeed. |

## Transition: incorrect service VLAN tag

On **R1**:

```ios
configure terminal
interface Ethernet0/0.20
encapsulation dot1Q 21
end
```

- R1: `show running-config interface Ethernet0/0.20` -- The fault is the actual subinterface tag, not a missing IP address.
- USERS: `ping 198.18.20.20 repeat 3` -- The protected segment drops all three probes.
- USERS: `ping 198.18.10.1 repeat 3` -- All three probes succeed.

## Transition: restore service VLAN tag

On **R1**:

```ios
configure terminal
interface Ethernet0/0.20
encapsulation dot1Q 20
end
```

- USERS: `ping 198.18.20.20 repeat 3` -- All three probes succeed.
- SERVICES: `ping 198.18.10.10 repeat 3` -- All three probes succeed.

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
interface Ethernet0/0
 no ip address
 no shutdown
 exit
interface Ethernet0/0.10
 encapsulation dot1Q 10
 ip address 198.18.10.1 255.255.255.0
 exit
interface Ethernet0/0.20
 encapsulation dot1Q 20
 ip address 198.18.20.1 255.255.255.0
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
interface range Ethernet0/0 - 3
 shutdown
 exit
vlan 10
 name USERS
 exit
vlan 20
 name SERVICES
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 no shutdown
 exit
interface Ethernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface Ethernet0/2
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
 no shutdown
 exit
end
```

### USERS

```ios
hostname USERS
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
 ip address 198.18.10.10 255.255.255.0
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.10.1
end
```

### SERVICES

```ios
hostname SERVICES
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
 ip address 198.18.20.20 255.255.255.0
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.20.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
