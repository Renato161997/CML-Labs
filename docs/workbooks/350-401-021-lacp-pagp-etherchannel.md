# LACP PAgP EtherChannel

## Scope and prerequisites

Two IOL-L2 reference switches use two physical members. Each protocol conversion removes the old memberships and logical interface before recreating the bundle, avoiding an invalid mixed-protocol configuration. An intermediate mismatch is checked as non-bundled; no particular traffic outcome is claimed for standalone/suspended members. The complete matching configurations must negotiate and forward before the stage passes. No aggregated-throughput claim is made.

Use licensed reference images for ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SW1 Ethernet0/0 <-> SW2 Ethernet0/0
- SW1 Ethernet0/1 <-> SW2 Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| SW1 | Vlan10 | `ip address 192.0.2.1 255.255.255.0` |
| SW2 | Vlan10 | `ip address 192.0.2.2 255.255.255.0` |

## Tasks

1. Verify an actual desirable/auto PAgP bundle and its data path.
2. Convert both peers to active/passive LACP, explicitly observing the protocol mismatch between stages.
3. Restore PAgP and verify both members and forwarding.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| SW1 | `show etherchannel summary` | Both links are actually bundled using PAgP. |
| SW1 | `ping 192.0.2.2 source Vlan10 repeat 3` | The SVI data path crosses the negotiated bundle. |

## Transition: first peer changes to LACP

On **SW1**:

```ios
configure terminal
interface range Ethernet0/0 - 1
no channel-group 1
exit
no interface Port-channel1
interface range Ethernet0/0 - 1
channel-protocol lacp
channel-group 1 mode active
exit
interface Port-channel1
switchport trunk encapsulation dot1q
switchport mode trunk
switchport trunk allowed vlan 10,20
no shutdown
end
```

- SW1: `show etherchannel summary` -- The changed peer reports its new protocol without a usable negotiated bundle.

## Transition: second peer changes to LACP

On **SW2**:

```ios
configure terminal
interface range Ethernet0/0 - 1
no channel-group 1
exit
no interface Port-channel1
interface range Ethernet0/0 - 1
channel-protocol lacp
channel-group 1 mode passive
exit
interface Port-channel1
switchport trunk encapsulation dot1q
switchport mode trunk
switchport trunk allowed vlan 10,20
no shutdown
end
```

- SW1: `show etherchannel summary` -- Both links are actually bundled using LACP.
- SW1: `ping 192.0.2.2 source Vlan10 repeat 3` -- The SVI data path crosses the negotiated bundle.

## Transition: first peer restores PAgP

On **SW1**:

```ios
configure terminal
interface range Ethernet0/0 - 1
no channel-group 1
exit
no interface Port-channel1
interface range Ethernet0/0 - 1
channel-protocol pagp
channel-group 1 mode desirable
exit
interface Port-channel1
switchport trunk encapsulation dot1q
switchport mode trunk
switchport trunk allowed vlan 10,20
no shutdown
end
```

- SW1: `show etherchannel summary` -- The changed peer reports its new protocol without a usable negotiated bundle.

## Transition: second peer restores PAgP

On **SW2**:

```ios
configure terminal
interface range Ethernet0/0 - 1
no channel-group 1
exit
no interface Port-channel1
interface range Ethernet0/0 - 1
channel-protocol pagp
channel-group 1 mode auto
exit
interface Port-channel1
switchport trunk encapsulation dot1q
switchport mode trunk
switchport trunk allowed vlan 10,20
no shutdown
end
```

- SW1: `show etherchannel summary` -- Both links are actually bundled using PAgP.
- SW1: `ping 192.0.2.2 source Vlan10 repeat 3` -- The SVI data path crosses the negotiated bundle.

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
vlan 10
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 no shutdown
 exit
interface Ethernet0/0
 channel-protocol pagp
 channel-group 1 mode desirable
 exit
interface Ethernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 no shutdown
 exit
interface Ethernet0/1
 channel-protocol pagp
 channel-group 1 mode desirable
 exit
interface Port-channel1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 no shutdown
 exit
interface Vlan10
 ip address 192.0.2.1 255.255.255.0
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
vlan 10
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 no shutdown
 exit
interface Ethernet0/0
 channel-protocol pagp
 channel-group 1 mode auto
 exit
interface Ethernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 no shutdown
 exit
interface Ethernet0/1
 channel-protocol pagp
 channel-group 1 mode auto
 exit
interface Port-channel1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 no shutdown
 exit
interface Vlan10
 ip address 192.0.2.2 255.255.255.0
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
