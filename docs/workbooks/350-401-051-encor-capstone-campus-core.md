# ENCOR Capstone Campus Core

## Scope and prerequisites

Two IOSv gateway routers, one IOL-L2 access switch and a separate IOL-XE service router form a redundant campus. ACCESS is an explicitly modeled sourced SVI endpoint, not an independent workstation. Both cores advertise the campus /24 through separate OSPF uplinks to SERVICE; its loopback198.19.0.80 is a single actual remote endpoint, with a real OSPF return path. HSRP10 supplies the access next hop198.18.10.1, on the shared access VLAN. The initial untracked HSRP configuration is deliberately an incomplete resilience policy. Making only CORE1 OSPF uplink passive removes that adjacency and service route without shutting its physical link or LAN SVI. The virtual IP remains reachable/active on CORE1, the access service fails, and CORE2 independently reaches the same service. Attaching the already configured route-reachability object with decrement30 must lower CORE1 below the preempting CORE2 and recover actual sourced traffic; the access LAN stays operational. Restoring OSPF must recover the tracked route and preferred HSRP ownership. This proves prefix tracking and control-plane failure recovery, not IP SLA application probes, BFD, physical failure timing or stateful application continuity. Nominal RAM is3GiB.

Use licensed reference images for iol-xe, ioll2-xe, iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- CORE1 GigabitEthernet0/0 <-> ACCESS Ethernet0/0
- CORE2 GigabitEthernet0/0 <-> ACCESS Ethernet0/1
- CORE1 GigabitEthernet0/1 <-> SERVICE Ethernet0/0
- CORE2 GigabitEthernet0/1 <-> SERVICE Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| CORE1 | GigabitEthernet0/0 | `ip address 198.18.10.2 255.255.255.0` |
| CORE1 | GigabitEthernet0/1 | `ip address 198.18.12.1 255.255.255.252` |
| CORE2 | GigabitEthernet0/0 | `ip address 198.18.10.3 255.255.255.0` |
| CORE2 | GigabitEthernet0/1 | `ip address 198.18.23.1 255.255.255.252` |
| ACCESS | Vlan10 | `ip address 198.18.10.10 255.255.255.0` |
| SERVICE | Ethernet0/0 | `ip address 198.18.12.2 255.255.255.252` |
| SERVICE | Ethernet0/1 | `ip address 198.18.23.2 255.255.255.252` |
| SERVICE | Loopback0 | `ip address 198.19.0.80 255.255.255.255` |

## Tasks

1. Correlate the access LAN, HSRP active gateway, OSPF service routes and actual access-SVI traffic.
2. Lose only the active core OSPF adjacency while its LAN carrier and virtual gateway stay healthy; prove untracked HSRP does not repair upstream routing loss.
3. Apply real route-object tracking to transfer the first hop to the healthy core, then recover OSPF and preferred ownership.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CORE1 | `show ip route 198.19.0.80` | The selected core actually has a remote-service OSPF route. |
| CORE2 | `show ip route 198.19.0.80` | The selected core actually has a remote-service OSPF route. |
| CORE1 | `show standby brief` | CORE1 is the actual active gateway. |
| CORE1 | `show track 1` | The object tracks actual remote-prefix reachability, not local carrier alone. |
| ACCESS | `show interfaces Vlan10` | The access LAN remains operational independently of first-hop ownership. |
| ACCESS | `ping 198.18.10.1 source Vlan10 repeat 3` | The local virtual gateway remains actually reachable. |
| ACCESS | `ping 198.19.0.80 source Vlan10 repeat 3` | The access SVI source actually reaches the separate remote service through the selected virtual first hop. |

## Transition: lose upstream routing without dropping the LAN

On **CORE1**:

```ios
configure terminal
router ospf 1
passive-interface GigabitEthernet0/1
end
```

- CORE1: `show track 1` -- The object tracks actual remote-prefix reachability, not local carrier alone.
- CORE1: `show standby brief` -- CORE1 is the actual active gateway.
- ACCESS: `ping 198.18.10.1 source Vlan10 repeat 3` -- The local virtual gateway remains actually reachable.
- ACCESS: `ping 198.19.0.80 source Vlan10 repeat 3` -- The access SVI source loses remote service despite a reachable local virtual gateway.
- CORE2: `show ip route 198.19.0.80` -- The selected core actually has a remote-service OSPF route.
- CORE2: `ping 198.19.0.80 source GigabitEthernet0/0 repeat 3` -- The standby core independently reaches the same separate service.
- ACCESS: `show interfaces Vlan10` -- The access LAN remains operational independently of first-hop ownership.

## Transition: connect first-hop priority to actual route health

On **CORE1**:

```ios
configure terminal
interface GigabitEthernet0/0
standby 10 track 1 decrement 30
end
```

- CORE1: `show track 1` -- The object tracks actual remote-prefix reachability, not local carrier alone.
- CORE2: `show standby brief` -- CORE2 actually takes over the virtual gateway.
- ACCESS: `ping 198.18.10.1 source Vlan10 repeat 3` -- The local virtual gateway remains actually reachable.
- ACCESS: `ping 198.19.0.80 source Vlan10 repeat 3` -- The access SVI source actually reaches the separate remote service through the selected virtual first hop.
- ACCESS: `show interfaces Vlan10` -- The access LAN remains operational independently of first-hop ownership.

## Transition: recover the preferred routed gateway

On **CORE1**:

```ios
configure terminal
router ospf 1
no passive-interface GigabitEthernet0/1
end
```

- CORE1: `show ip route 198.19.0.80` -- The selected core actually has a remote-service OSPF route.
- CORE2: `show ip route 198.19.0.80` -- The selected core actually has a remote-service OSPF route.
- CORE1: `show standby brief` -- CORE1 is the actual active gateway.
- CORE1: `show track 1` -- The object tracks actual remote-prefix reachability, not local carrier alone.
- ACCESS: `show interfaces Vlan10` -- The access LAN remains operational independently of first-hop ownership.
- ACCESS: `ping 198.18.10.1 source Vlan10 repeat 3` -- The local virtual gateway remains actually reachable.
- ACCESS: `ping 198.19.0.80 source Vlan10 repeat 3` -- The access SVI source actually reaches the separate remote service through the selected virtual first hop.

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
interface GigabitEthernet0/0
 ip address 198.18.10.2 255.255.255.0
 no shutdown
 standby version 2
 standby 10 ip 198.18.10.1
 standby 10 priority 110
 standby 10 preempt
 exit
interface GigabitEthernet0/1
 ip address 198.18.12.1 255.255.255.252
 no shutdown
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 exit
router ospf 1
 router-id 192.0.2.1
 passive-interface default
 no passive-interface GigabitEthernet0/1
 network 198.18.12.0 0.0.0.3 area 0
 network 198.18.10.0 0.0.0.255 area 0
 exit
track 1 ip route 198.19.0.80 255.255.255.255 reachability
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
interface GigabitEthernet0/0
 ip address 198.18.10.3 255.255.255.0
 no shutdown
 standby version 2
 standby 10 ip 198.18.10.1
 standby 10 priority 100
 standby 10 preempt
 exit
interface GigabitEthernet0/1
 ip address 198.18.23.1 255.255.255.252
 no shutdown
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 exit
router ospf 1
 router-id 192.0.2.2
 passive-interface default
 no passive-interface GigabitEthernet0/1
 network 198.18.23.0 0.0.0.3 area 0
 network 198.18.10.0 0.0.0.255 area 0
 exit
track 1 ip route 198.19.0.80 255.255.255.255 reachability
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
ip routing
vlan 10
 name CAMPUS
 exit
interface Ethernet0/0
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface Ethernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface Vlan10
 ip address 198.18.10.10 255.255.255.0
 no shutdown
 exit
ip route 198.19.0.80 255.255.255.255 198.18.10.1
end
```

### SERVICE

```ios
hostname SERVICE
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
 ip address 198.18.12.2 255.255.255.252
 no shutdown
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 exit
interface Ethernet0/1
 ip address 198.18.23.2 255.255.255.252
 no shutdown
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 exit
interface Loopback0
 ip address 198.19.0.80 255.255.255.255
 no shutdown
 exit
router ospf 1
 router-id 192.0.2.80
 passive-interface Loopback0
 network 198.18.12.0 0.0.0.3 area 0
 network 198.18.23.0 0.0.0.3 area 0
 network 198.19.0.80 0.0.0.0 area 0
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
