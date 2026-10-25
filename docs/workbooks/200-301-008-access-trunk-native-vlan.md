# Access Trunk Native VLAN

## Scope and prerequisites

Native VLAN 99 carries no user SVI. VLANs 10 and 20 are tagged, with separate /26 endpoint subnets. Removing VLAN 20 from one allowed list must break only that VLAN.

Use licensed reference images for iosvl2 in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SW1 GigabitEthernet0/0 <-> SW2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| SW1 | Vlan10 | `ip address 192.0.2.1 255.255.255.192` |
| SW1 | Vlan20 | `ip address 192.0.2.65 255.255.255.192` |
| SW2 | Vlan10 | `ip address 192.0.2.2 255.255.255.192` |
| SW2 | Vlan20 | `ip address 192.0.2.66 255.255.255.192` |

## Tasks

1. Identify the native VLAN and allowed VLAN list.
2. Verify both tagged user VLANs across the trunk.
3. Prune only VLAN 20, prove the resulting failure, then restore it.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| SW1 | `show interfaces trunk` | Gi0/0 is an 802.1Q trunk with native VLAN 99. |
| SW2 | `ping 192.0.2.1 source Vlan10 repeat 3` | VLAN 10 crosses the trunk. |
| SW2 | `ping 192.0.2.65 source Vlan20 repeat 3` | VLAN 20 crosses the trunk. |

## Transition: prune service VLAN

On **SW1**:

```ios
configure terminal
interface GigabitEthernet0/0
switchport trunk allowed vlan 10,99
end
```

- SW2: `ping 192.0.2.65 source Vlan20 repeat 3` -- The pruned VLAN no longer forwards.

## Transition: restore service VLAN

On **SW1**:

```ios
configure terminal
interface GigabitEthernet0/0
switchport trunk allowed vlan 10,20,99
end
```

- SW2: `ping 192.0.2.65 source Vlan20 repeat 3` -- VLAN 20 crosses the trunk.

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
vlan 10
 name USERS
vlan 20
 name SERVICES
vlan 99
 name NATIVE
interface GigabitEthernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,99
 no shutdown
 exit
interface Vlan10
 ip address 192.0.2.1 255.255.255.192
 no shutdown
 exit
interface Vlan20
 ip address 192.0.2.65 255.255.255.192
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
vlan 10
 name USERS
vlan 20
 name SERVICES
vlan 99
 name NATIVE
interface GigabitEthernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 99
 switchport trunk allowed vlan 10,20,99
 no shutdown
 exit
interface Vlan10
 ip address 192.0.2.2 255.255.255.192
 no shutdown
 exit
interface Vlan20
 ip address 192.0.2.66 255.255.255.192
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
