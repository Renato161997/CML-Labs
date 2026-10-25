# Layer 2 Security Basics

## Scope and prerequisites

This focused Layer-2 security exercise verifies Root Guard, not every campus security control. ROOT is the intended VLAN 10 root. ACCESS Ethernet0/1 is the designated downstream boundary with Root Guard enabled. ROGUE initially has a worse bridge priority; changing it to zero generates real superior BPDUs. The upstream segment must keep forwarding while the offending downstream segment is blocked. Root Guard remains configured throughout recovery. Port security has a separate workbook; DHCP snooping/DAI are not claimed here.

Use licensed reference images for ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- ROOT Ethernet0/0 <-> ACCESS Ethernet0/0
- ACCESS Ethernet0/1 <-> ROGUE Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| ROOT | Vlan10 | `ip address 198.18.10.1 255.255.255.0` |
| ACCESS | Vlan10 | `ip address 198.18.10.2 255.255.255.0` |
| ROGUE | Vlan10 | `ip address 198.18.10.3 255.255.255.0` |

## Tasks

1. Place Root Guard on a designated downstream boundary, not the root-facing uplink.
2. Advertise a superior bridge priority and observe root-inconsistent blocking.
3. Restore the downstream priority and verify automatic recovery without disabling Root Guard.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| ACCESS | `show spanning-tree vlan 10` | The authorized upstream remains the root port. |
| ROGUE | `ping 198.18.10.1 repeat 3` | All three probes succeed. |
| ACCESS | `show spanning-tree inconsistentports` | No guarded port remains inconsistent. |

## Transition: superior downstream BPDUs

On **ROGUE**:

```ios
configure terminal
spanning-tree vlan 10 priority 0
end
```

- ACCESS: `show spanning-tree inconsistentports` -- The guarded downstream interface is root-inconsistent.
- ACCESS: `show spanning-tree vlan 10` -- The authorized upstream remains the root port.
- ROOT: `ping 198.18.10.2 repeat 3` -- All three probes succeed.
- ROGUE: `ping 198.18.10.1 repeat 3` -- The protected segment drops all three probes.

## Transition: legitimate downstream priority restored

On **ROGUE**:

```ios
configure terminal
spanning-tree vlan 10 priority 61440
end
```

- ACCESS: `show spanning-tree inconsistentports` -- No guarded port remains inconsistent.
- ACCESS: `show spanning-tree vlan 10` -- The authorized upstream remains the root port.
- ROGUE: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- ACCESS: `show running-config interface Ethernet0/1` -- The boundary protection remains enabled.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### ROOT

```ios
hostname ROOT
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
end
```

### ACCESS

```ios
hostname ACCESS
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
 spanning-tree guard root
 no shutdown
 exit
end
```

### ROGUE

```ios
hostname ROGUE
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
spanning-tree vlan 10 priority 61440
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
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

See [Cisco optional spanning-tree features](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst2960/software/release/12-2_53_se/configuration/guide/2960scg/swstpopt.html) for guard behavior. The live evidence above determines support on the tested virtual image.
