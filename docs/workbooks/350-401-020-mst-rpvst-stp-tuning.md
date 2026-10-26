# MST RPVST STP Tuning

## Scope and prerequisites

Two IOL-L2 switches form one region with VLAN 10 in MST1 and VLAN 20 in MST2. The conversion is staged across both peers; intermediate steps verify configuration, not convergence or lossless interoperability. Final acceptance checks the actual roots and both VLAN data paths. This small topology teaches root/instance control, not redundant-path failure timing.

Use licensed reference images for ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SW1 Ethernet0/0 <-> SW2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| SW1 | Vlan10 | `ip address 192.0.2.1 255.255.255.0` |
| SW1 | Vlan20 | `ip address 198.51.100.1 255.255.255.0` |
| SW2 | Vlan10 | `ip address 192.0.2.2 255.255.255.0` |
| SW2 | Vlan20 | `ip address 198.51.100.2 255.255.255.0` |

## Tasks

1. Inspect a common MST region with distinct VLAN-to-instance mappings and roots.
2. Convert both peers to Rapid-PVST and establish the intended per-VLAN roots.
3. Restore MST and verify both instance roots and tagged VLAN traffic.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| SW1 | `show spanning-tree mst 1` | SW1 is the instance-1 root. |
| SW2 | `show spanning-tree mst 2` | SW2 is the instance-2 root. |
| SW1 | `ping 192.0.2.2 source Vlan10 repeat 3` | VLAN 10 crosses the inter-switch link. |
| SW1 | `ping 198.51.100.2 source Vlan20 repeat 3` | VLAN 20 crosses the inter-switch link. |

## Transition: first peer becomes Rapid-PVST

On **SW1**:

```ios
configure terminal
spanning-tree mode rapid-pvst
spanning-tree vlan 10 priority 4096
spanning-tree vlan 20 priority 32768
end
```

- SW1: `show spanning-tree summary` -- The first peer reports Rapid-PVST mode.

## Transition: second peer becomes Rapid-PVST

On **SW2**:

```ios
configure terminal
spanning-tree mode rapid-pvst
spanning-tree vlan 10 priority 32768
spanning-tree vlan 20 priority 4096
end
```

- SW1: `show spanning-tree vlan 10` -- SW1 is the Rapid-PVST VLAN-10 root.
- SW2: `show spanning-tree vlan 20` -- SW2 is the Rapid-PVST VLAN-20 root.
- SW1: `ping 192.0.2.2 source Vlan10 repeat 3` -- VLAN 10 crosses the inter-switch link.
- SW1: `ping 198.51.100.2 source Vlan20 repeat 3` -- VLAN 20 crosses the inter-switch link.

## Transition: first peer returns to MST

On **SW1**:

```ios
configure terminal
spanning-tree mode mst
spanning-tree mst 1 priority 4096
end
```

- SW1: `show spanning-tree summary` -- The first peer reports MST mode.

## Transition: second peer returns to MST

On **SW2**:

```ios
configure terminal
spanning-tree mode mst
spanning-tree mst 2 priority 4096
end
```

- SW1: `show spanning-tree mst 1` -- SW1 is the instance-1 root.
- SW2: `show spanning-tree mst 2` -- SW2 is the instance-2 root.
- SW1: `ping 192.0.2.2 source Vlan10 repeat 3` -- VLAN 10 crosses the inter-switch link.
- SW1: `ping 198.51.100.2 source Vlan20 repeat 3` -- VLAN 20 crosses the inter-switch link.

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
vlan 20
 exit
spanning-tree mst configuration
 name CMLREGION
 revision 1
 instance 1 vlan 10
 instance 2 vlan 20
 exit
spanning-tree mode mst
spanning-tree mst 1 priority 4096
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 no shutdown
 exit
interface Vlan10
 ip address 192.0.2.1 255.255.255.0
 no shutdown
 exit
interface Vlan20
 ip address 198.51.100.1 255.255.255.0
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
vlan 20
 exit
spanning-tree mst configuration
 name CMLREGION
 revision 1
 instance 1 vlan 10
 instance 2 vlan 20
 exit
spanning-tree mode mst
spanning-tree mst 2 priority 4096
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 no shutdown
 exit
interface Vlan10
 ip address 192.0.2.2 255.255.255.0
 no shutdown
 exit
interface Vlan20
 ip address 198.51.100.2 255.255.255.0
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
