# Rapid PVST Troubleshooting

## Scope and prerequisites

Requires three IOL-L2 reference switches. All trunks carry only VLAN 10 and use an explicit per-VLAN cost of 4. Distinct bridge priorities make the expected alternate port deterministic without relying on random virtual MAC addresses. An alternate BLK port is expected loop prevention; a successful ping alone cannot establish that the desired root policy is correct. This models logical STP behavior, not physical failure timing or throughput.

Use licensed reference images for ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SW1 Ethernet0/0 <-> SW2 Ethernet0/0
- SW1 Ethernet0/1 <-> SW3 Ethernet0/0
- SW2 Ethernet0/1 <-> SW3 Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| SW1 | Vlan10 | `ip address 198.18.10.1 255.255.255.0` |
| SW2 | Vlan10 | `ip address 198.18.10.2 255.255.255.0` |
| SW3 | Vlan10 | `ip address 198.18.10.3 255.255.255.0` |

## Tasks

1. Identify the root, designated, root-port and alternate roles in a real triangle.
2. Introduce an unintended lower bridge priority and diagnose the changed root even while IP connectivity survives.
3. Restore the intended priorities and verify both the root and the alternate blocked port.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| SW1 | `show spanning-tree vlan 10` | SW1 is the intended VLAN 10 root. |
| SW3 | `show spanning-tree vlan 10` | The redundant path is correctly blocked, not a failed link. |
| SW2 | `ping 198.18.10.3 repeat 3` | All three probes succeed. |

## Transition: unintended bridge wins election

On **SW3**:

```ios
configure terminal
spanning-tree vlan 10 priority 0
end
```

- SW3: `show spanning-tree vlan 10` -- SW3 has actually become root.
- SW1: `show spanning-tree vlan 10` -- SW1 now points toward the unintended root.
- SW2: `ping 198.18.10.3 repeat 3` -- All three probes succeed.

## Transition: restore intended root policy

On **SW3**:

```ios
configure terminal
spanning-tree vlan 10 priority 32768
end
```

- SW1: `show spanning-tree vlan 10` -- SW1 is the intended VLAN 10 root.
- SW3: `show spanning-tree vlan 10` -- The redundant path is correctly blocked, not a failed link.
- SW2: `ping 198.18.10.3 repeat 3` -- All three probes succeed.

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
 name LAB
 exit
spanning-tree vlan 10 priority 4096
interface Vlan10
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
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
 name LAB
 exit
spanning-tree vlan 10 priority 8192
interface Vlan10
 ip address 198.18.10.2 255.255.255.0
 no shutdown
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
end
```

### SW3

```ios
hostname SW3
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
 name LAB
 exit
spanning-tree vlan 10 priority 32768
interface Vlan10
 ip address 198.18.10.3 255.255.255.0
 no shutdown
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

See [Cisco optional spanning-tree features](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst2960/software/release/12-2_53_se/configuration/guide/2960scg/swstpopt.html) for guard behavior. The live evidence above determines support on the tested virtual image.
