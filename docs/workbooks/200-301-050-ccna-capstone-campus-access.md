# CCNA Capstone Campus Access

## Scope and prerequisites

Four IOL reference nodes integrate VLAN access, an actual redundant STP triangle, HSRPv2 and an explicit endpoint host route. CORE1 and CORE2 each host192.0.2.80/32 on a separate loopback; this deliberately models a duplicated lab service identity behind the selected gateway, not an external application or a duplicate address on one Ethernet segment. The fault administratively isolates both CORE1 trunks; the CML VM itself remains running. CORE2 must become both root and active gateway, and the endpoint must still reach the VIP and loopback target. Recovery verifies preferred-role preemption. A separate endpoint-route withdrawal must fail only the service probe while the VIP remains healthy. Nominal RAM is4GiB.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- CORE1 Ethernet0/0 <-> CORE2 Ethernet0/0
- CORE1 Ethernet0/1 <-> ACCESS Ethernet0/0
- CORE2 Ethernet0/1 <-> ACCESS Ethernet0/1
- CLIENT Ethernet0/0 <-> ACCESS Ethernet0/2

| Node | Interface | Address |
| --- | --- | --- |
| CORE1 | Vlan10 | `ip address 198.18.10.2 255.255.255.0` |
| CORE1 | Loopback0 | `ip address 192.0.2.80 255.255.255.255` |
| CORE2 | Vlan10 | `ip address 198.18.10.3 255.255.255.0` |
| CORE2 | Loopback0 | `ip address 192.0.2.80 255.255.255.255` |
| ACCESS | Vlan10 | `ip address 198.18.10.4 255.255.255.0` |
| CLIENT | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |

## Tasks

1. Validate the real STP root/alternate topology and the active/standby HSRPv2 gateway.
2. Isolate both preferred-core uplinks, prove root and gateway failover and keep actual endpoint traffic working.
3. Recover the preferred roles, then distinguish an endpoint route failure from a healthy first hop.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CORE1 | `show standby brief` | CORE1 is the actual active gateway. |
| CORE2 | `show standby brief` | CORE2 is the actual standby behind the preferred core. |
| CORE1 | `show spanning-tree vlan 10` | CORE1 is the preferred actual STP root. |
| CLIENT | `ping 198.18.10.1 repeat 3` | The actual first-hop virtual IP is reachable. |
| CLIENT | `ping 192.0.2.80 source Ethernet0/0 repeat 3` | The explicit endpoint route and the active first hop reach the isolated loopback service. |
| ACCESS | `show spanning-tree vlan 10` | The redundant uplink is initially blocked. |

## Transition: isolate the preferred core data links

On **CORE1**:

```ios
configure terminal
interface range Ethernet0/0 - 1
shutdown
end
```

- CORE2: `show standby brief` -- CORE2 actually takes over the virtual gateway.
- CORE2: `show spanning-tree vlan 10` -- CORE2 becomes the visible root after the preferred core is isolated.
- ACCESS: `show spanning-tree vlan 10` -- Access forwards through the surviving core.
- CLIENT: `ping 198.18.10.1 repeat 3` -- The actual first-hop virtual IP is reachable.
- CLIENT: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The explicit endpoint route and the active first hop reach the isolated loopback service.

## Transition: restore preferred core roles

On **CORE1**:

```ios
configure terminal
interface range Ethernet0/0 - 1
no shutdown
end
```

- CORE1: `show standby brief` -- CORE1 is the actual active gateway.
- CORE2: `show standby brief` -- CORE2 is the actual standby behind the preferred core.
- CORE1: `show spanning-tree vlan 10` -- CORE1 is the preferred actual STP root.
- CLIENT: `ping 198.18.10.1 repeat 3` -- The actual first-hop virtual IP is reachable.
- CLIENT: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The explicit endpoint route and the active first hop reach the isolated loopback service.

## Transition: withdraw only the endpoint service route

On **CLIENT**:

```ios
configure terminal
no ip route 192.0.2.80 255.255.255.255 198.18.10.1
end
```

- CLIENT: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The endpoint cannot reach the service without its route.
- CLIENT: `ping 198.18.10.1 repeat 3` -- The actual first-hop virtual IP is reachable.
- CORE1: `show standby brief` -- CORE1 is the actual active gateway.

## Transition: restore the endpoint service route

On **CLIENT**:

```ios
configure terminal
ip route 192.0.2.80 255.255.255.255 198.18.10.1
end
```

- CLIENT: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The explicit endpoint route and the active first hop reach the isolated loopback service.
- CLIENT: `ping 198.18.10.1 repeat 3` -- The actual first-hop virtual IP is reachable.

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
 name CAMPUS
 exit
spanning-tree vlan 10 priority 4096
spanning-tree mode rapid-pvst
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
interface Vlan10
 ip address 198.18.10.2 255.255.255.0
 standby version 2
 standby 10 ip 198.18.10.1
 standby 10 priority 110
 standby 10 preempt
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.80 255.255.255.255
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
 name CAMPUS
 exit
spanning-tree vlan 10 priority 8192
spanning-tree mode rapid-pvst
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
interface Vlan10
 ip address 198.18.10.3 255.255.255.0
 standby version 2
 standby 10 ip 198.18.10.1
 standby 10 priority 100
 standby 10 preempt
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.80 255.255.255.255
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
 ip address 198.18.10.4 255.255.255.0
 no shutdown
 exit
spanning-tree mode rapid-pvst
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
interface Ethernet0/2
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
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
 ip address 198.18.10.10 255.255.255.0
 no shutdown
 exit
ip route 192.0.2.80 255.255.255.255 198.18.10.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
