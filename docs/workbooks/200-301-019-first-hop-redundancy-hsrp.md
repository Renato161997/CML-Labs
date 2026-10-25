# First Hop Redundancy HSRP

## Scope and prerequisites

Requires IOL-L2 XE switches and an IOL-XE client. The failure shuts the L3 SVI, not the switch: the client can still cross SW1 at Layer 2 to reach SW2. This does not test total chassis loss. IOSvL2 was not selected for this exercise because one SVI remained down in the observed cold-start tests.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SW1 Ethernet0/0 <-> SW2 Ethernet0/0
- CLIENT Ethernet0/0 <-> SW1 Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| SW1 | Vlan10 | `ip address 198.18.10.2 255.255.255.0` |
| SW2 | Vlan10 | `ip address 198.18.10.3 255.255.255.0` |
| CLIENT | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |

## Tasks

1. Explain virtual addressing, priority and preemption.
2. Fail only the active SVI while keeping Layer-2 transit alive.
3. Verify standby takeover and gateway continuity, then restore the preferred active peer.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| SW1 | `show interfaces trunk` | The shared VLAN crosses an operational dot1q trunk. |
| SW1 | `show standby brief` | SW1 is the active gateway. |
| SW2 | `show standby brief` | SW2 is initially standby. |
| CLIENT | `ping 198.18.10.1 repeat 3` | The client reaches the virtual gateway. |

## Transition: active SVI failure

On **SW1**:

```ios
configure terminal
interface Vlan10
shutdown
end
```

- SW2: `show standby brief` -- SW2 takes over as active.
- CLIENT: `ping 198.18.10.1 repeat 3` -- The client reaches the virtual gateway.

## Transition: preferred gateway recovers

On **SW1**:

```ios
configure terminal
interface Vlan10
no shutdown
end
```

- SW1: `show standby brief` -- SW1 is the active gateway.
- CLIENT: `ping 198.18.10.1 repeat 3` -- The client reaches the virtual gateway.

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
ip routing
vlan 10
 name CLIENTS
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 1
 switchport trunk allowed vlan 10
 no shutdown
 exit
interface Vlan10
 ip address 198.18.10.2 255.255.255.0
 no shutdown
 standby 10 ip 198.18.10.1
 standby 10 priority 110
 standby 10 preempt
 exit
interface Ethernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
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
ip routing
vlan 10
 name CLIENTS
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 1
 switchport trunk allowed vlan 10
 no shutdown
 exit
interface Vlan10
 ip address 198.18.10.3 255.255.255.0
 no shutdown
 standby 10 ip 198.18.10.1
 standby 10 priority 100
 standby 10 preempt
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
 ip address 198.18.10.10 255.255.255.0
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.10.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
