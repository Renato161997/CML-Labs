# CCNA Practical Checkpoint One

## Scope and prerequisites

Two IOL-L2 switches and two IOL-XE endpoints form this deliberately broken assessment: SW1 permits only VLAN20 while every access endpoint and both management SVIs use VLAN10. The first data-plane check must fail before the repair is applied. VTP transparent mode keeps the supplied VLAN database in day-0 configuration. Both VLANs already exist, the trunk is statically configured and endpoint routes are correct. Repair changes only SW1 allowed VLAN membership. All networks are isolated documentation/benchmark ranges; no external connector is needed.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Deliberately broken: SW1 excludes the user VLAN from the only inter-switch trunk. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SW1 Ethernet0/0 <-> SW2 Ethernet0/0
- SW1 Ethernet0/1 <-> CLIENT Ethernet0/0
- SW2 Ethernet0/1 <-> RTR Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| SW1 | Vlan10 | `ip address 192.0.2.11 255.255.255.0` |
| SW2 | Vlan10 | `ip address 192.0.2.12 255.255.255.0` |
| CLIENT | Ethernet0/0 | `ip address 192.0.2.2 255.255.255.0` |
| RTR | Ethernet0/0 | `ip address 192.0.2.1 255.255.255.0` |
| RTR | Loopback0 | `ip address 198.18.0.1 255.255.255.255` |

## Tasks

1. Diagnose a failed routed-endpoint ping without changing correct addressing or default routes.
2. Compare VLAN membership with the allowed VLAN on each end of the trunk.
3. Restore only the missing VLAN and verify access, management and routed traffic.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `ping 198.18.0.1 repeat 3` | The access VLAN, trunk, default route and return path carry actual packets. |
| SW1 | `show interfaces trunk` | The repaired trunk carries the user VLAN. |
| CLIENT | `ping 192.0.2.11 repeat 3` | Local switch management is reachable. |
| CLIENT | `ping 192.0.2.12 repeat 3` | Remote switch management crosses the repaired trunk. |

## Initial fault and repair

SW1 excludes the user VLAN from the only inter-switch trunk.

Apply on SW1:

```ios
configure terminal
interface Ethernet0/0
switchport trunk allowed vlan 10
end
```

Run baseline acceptance after the repair.

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
interface range Ethernet0/0 - 3
 shutdown
 exit
no logging console
vlan 10
 name USERS
 exit
vlan 20
 name UNUSED
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 20
 no shutdown
 exit
interface Ethernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface Vlan10
 ip address 192.0.2.11 255.255.255.0
 no shutdown
 exit
end
```

### SW2

```ios
hostname SW2
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
no logging console
vlan 10
 name USERS
 exit
vlan 20
 name UNUSED
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 no shutdown
 exit
interface Ethernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface Vlan10
 ip address 192.0.2.12 255.255.255.0
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
 ip address 192.0.2.2 255.255.255.0
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 192.0.2.1
end
```

### RTR

```ios
hostname RTR
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
 ip address 192.0.2.1 255.255.255.0
 no shutdown
 exit
interface Loopback0
 ip address 198.18.0.1 255.255.255.255
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
