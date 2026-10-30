# FHRP Design HSRP VRRP

## Scope and prerequisites

Four IOL reference nodes compare two real IPv4 first-hop protocols on separate VLANs. HSRPv2 group10 prefers CORE1; VRRPv2 group20 prefers CORE2. A routed IOL endpoint has explicit service host routes through the corresponding VIPs. Each core hosts the same two isolated loopback identities, deliberately modeling service availability behind the selected gateway; this is not an external application or a duplicate IP on a shared Ethernet segment. Shutting one core trunk isolates both of its SVIs without powering off its CML VM. The surviving core must take both active roles and forward both endpoint probes. Recovery must restore the opposite preferred roles. This tests protocol behavior, not physical HA timing, stateful application failover or forwarding throughput. Nominal RAM is4GiB.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- CORE1 Ethernet0/0 <-> SW1 Ethernet0/0
- CORE2 Ethernet0/0 <-> SW1 Ethernet0/1
- CLIENT Ethernet0/0 <-> SW1 Ethernet0/2

| Node | Interface | Address |
| --- | --- | --- |
| CORE1 | Vlan10 | `ip address 198.18.10.2 255.255.255.0` |
| CORE1 | Loopback10 | `ip address 192.0.2.10 255.255.255.255` |
| CORE1 | Vlan20 | `ip address 198.18.20.2 255.255.255.0` |
| CORE1 | Loopback20 | `ip address 192.0.2.20 255.255.255.255` |
| CORE2 | Vlan10 | `ip address 198.18.10.3 255.255.255.0` |
| CORE2 | Loopback10 | `ip address 192.0.2.10 255.255.255.255` |
| CORE2 | Vlan20 | `ip address 198.18.20.3 255.255.255.0` |
| CORE2 | Loopback20 | `ip address 192.0.2.20 255.255.255.255` |
| CLIENT | Ethernet0/0.10 | `ip address 198.18.10.10 255.255.255.0` |
| CLIENT | Ethernet0/0.20 | `ip address 198.18.20.10 255.255.255.0` |

## Tasks

1. Compare actual HSRPv2 active/standby with VRRPv2 master/backup on separate VLANs.
2. Use opposite preferred cores and prove real traffic through both virtual gateways.
3. Isolate each core in turn and recover preferred roles with preemption.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CORE1 | `show standby brief` | The expected core is actually HSRP active. |
| CORE2 | `show vrrp brief` | The expected core has the actual VRRP Master role. |
| CORE1 | `show vrrp brief` | The expected core has the actual VRRP Backup role. |
| CLIENT | `ping 192.0.2.10 source Ethernet0/0.10 repeat 3` | The VLAN10 endpoint route reaches the isolated service through its first-hop VIP. |
| CLIENT | `ping 192.0.2.20 source Ethernet0/0.20 repeat 3` | The VLAN20 endpoint route reaches the isolated service through its first-hop VIP. |

## Transition: isolate the preferred HSRP core

On **CORE1**:

```ios
configure terminal
interface Ethernet0/0
shutdown
end
```

- CORE2: `show standby brief` -- The expected core is actually HSRP active.
- CORE2: `show vrrp brief` -- The expected core has the actual VRRP Master role.
- CLIENT: `ping 192.0.2.10 source Ethernet0/0.10 repeat 3` -- The VLAN10 endpoint route reaches the isolated service through its first-hop VIP.
- CLIENT: `ping 192.0.2.20 source Ethernet0/0.20 repeat 3` -- The VLAN20 endpoint route reaches the isolated service through its first-hop VIP.

## Transition: restore the preferred HSRP core

On **CORE1**:

```ios
configure terminal
interface Ethernet0/0
no shutdown
end
```

- CORE1: `show standby brief` -- The expected core is actually HSRP active.
- CORE2: `show vrrp brief` -- The expected core has the actual VRRP Master role.
- CORE1: `show vrrp brief` -- The expected core has the actual VRRP Backup role.
- CLIENT: `ping 192.0.2.10 source Ethernet0/0.10 repeat 3` -- The VLAN10 endpoint route reaches the isolated service through its first-hop VIP.
- CLIENT: `ping 192.0.2.20 source Ethernet0/0.20 repeat 3` -- The VLAN20 endpoint route reaches the isolated service through its first-hop VIP.

## Transition: isolate the preferred VRRP core

On **CORE2**:

```ios
configure terminal
interface Ethernet0/0
shutdown
end
```

- CORE1: `show standby brief` -- The expected core is actually HSRP active.
- CORE1: `show vrrp brief` -- The expected core has the actual VRRP Master role.
- CLIENT: `ping 192.0.2.10 source Ethernet0/0.10 repeat 3` -- The VLAN10 endpoint route reaches the isolated service through its first-hop VIP.
- CLIENT: `ping 192.0.2.20 source Ethernet0/0.20 repeat 3` -- The VLAN20 endpoint route reaches the isolated service through its first-hop VIP.

## Transition: restore the preferred VRRP core

On **CORE2**:

```ios
configure terminal
interface Ethernet0/0
no shutdown
end
```

- CORE1: `show standby brief` -- The expected core is actually HSRP active.
- CORE2: `show vrrp brief` -- The expected core has the actual VRRP Master role.
- CORE1: `show vrrp brief` -- The expected core has the actual VRRP Backup role.
- CLIENT: `ping 192.0.2.10 source Ethernet0/0.10 repeat 3` -- The VLAN10 endpoint route reaches the isolated service through its first-hop VIP.
- CLIENT: `ping 192.0.2.20 source Ethernet0/0.20 repeat 3` -- The VLAN20 endpoint route reaches the isolated service through its first-hop VIP.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### CORE1

```ios
hostname CORE1
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
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Vlan10
 ip address 198.18.10.2 255.255.255.0
 no shutdown
 exit
interface Vlan10
 standby version 2
 standby 10 ip 198.18.10.1
 standby 10 priority 110
 standby 10 preempt
 exit
interface Loopback10
 ip address 192.0.2.10 255.255.255.255
 no shutdown
 exit
interface Vlan20
 ip address 198.18.20.2 255.255.255.0
 no shutdown
 exit
interface Vlan20
 vrrp 20 ip 198.18.20.1
 vrrp 20 priority 100
 vrrp 20 preempt
 exit
interface Loopback20
 ip address 192.0.2.20 255.255.255.255
 no shutdown
 exit
end
```

### CORE2

```ios
hostname CORE2
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
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Vlan10
 ip address 198.18.10.3 255.255.255.0
 no shutdown
 exit
interface Vlan10
 standby version 2
 standby 10 ip 198.18.10.1
 standby 10 priority 100
 standby 10 preempt
 exit
interface Loopback10
 ip address 192.0.2.10 255.255.255.255
 no shutdown
 exit
interface Vlan20
 ip address 198.18.20.3 255.255.255.0
 no shutdown
 exit
interface Vlan20
 vrrp 20 ip 198.18.20.1
 vrrp 20 priority 110
 vrrp 20 preempt
 exit
interface Loopback20
 ip address 192.0.2.20 255.255.255.255
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
interface range Ethernet0/0 - 3
 shutdown
 exit
vlan 10
 exit
vlan 20
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 spanning-tree vlan 10 cost 4
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
interface Ethernet0/0.10
 encapsulation dot1Q 10
 ip address 198.18.10.10 255.255.255.0
 no shutdown
 exit
ip route 192.0.2.10 255.255.255.255 198.18.10.1
interface Ethernet0/0.20
 encapsulation dot1Q 20
 ip address 198.18.20.10 255.255.255.0
 no shutdown
 exit
ip route 192.0.2.20 255.255.255.255 198.18.20.1
interface Ethernet0/0
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
