# EtherChannel LACP

## Scope and prerequisites

Both ends actively negotiate LACP. Identical trunk settings are applied to the members and aggregate. The exercise tests membership and continuity, not aggregate throughput on performance-limited virtual switches.

Use licensed reference images for iosvl2 in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SW1 GigabitEthernet0/0 <-> SW2 GigabitEthernet0/0
- SW1 GigabitEthernet0/1 <-> SW2 GigabitEthernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| SW1 | Vlan10 | `ip address 192.0.2.1 255.255.255.192` |
| SW2 | Vlan10 | `ip address 192.0.2.2 255.255.255.192` |

## Tasks

1. Inspect LACP membership and distinguish a bundled port from an individual link.
2. Fail one member while retaining SVI reachability.
3. Restore both members and verify the aggregate is healthy.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| SW1 | `show etherchannel summary` | Both physical ports are bundled in an in-use Layer-2 port-channel. |
| SW2 | `ping 192.0.2.1 source Vlan10 repeat 3` | The SVI is reachable through the port-channel. |

## Transition: one member fails

On **SW1**:

```ios
configure terminal
interface GigabitEthernet0/0
shutdown
end
```

- SW1: `show etherchannel summary` -- Po1 remains in use with Gi0/1 bundled.
- SW2: `ping 192.0.2.1 source Vlan10 repeat 3` -- The SVI is reachable through the port-channel.

## Transition: member recovers

On **SW1**:

```ios
configure terminal
interface GigabitEthernet0/0
no shutdown
end
```

- SW1: `show etherchannel summary` -- Both physical ports are bundled in an in-use Layer-2 port-channel.
- SW2: `ping 192.0.2.1 source Vlan10 repeat 3` -- The SVI is reachable through the port-channel.

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
interface Vlan10
 ip address 192.0.2.1 255.255.255.192
 no shutdown
 exit
interface GigabitEthernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 1
 switchport trunk allowed vlan 10
 no shutdown
 exit
interface GigabitEthernet0/0
 channel-group 1 mode active
 lacp rate fast
 exit
interface GigabitEthernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 1
 switchport trunk allowed vlan 10
 no shutdown
 exit
interface GigabitEthernet0/1
 channel-group 1 mode active
 lacp rate fast
 exit
interface Port-channel1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
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
interface Vlan10
 ip address 192.0.2.2 255.255.255.192
 no shutdown
 exit
interface GigabitEthernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 1
 switchport trunk allowed vlan 10
 no shutdown
 exit
interface GigabitEthernet0/0
 channel-group 1 mode active
 lacp rate fast
 exit
interface GigabitEthernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 1
 switchport trunk allowed vlan 10
 no shutdown
 exit
interface GigabitEthernet0/1
 channel-group 1 mode active
 lacp rate fast
 exit
interface Port-channel1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 no shutdown
 exit
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
