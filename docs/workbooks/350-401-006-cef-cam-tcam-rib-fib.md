# CEF CAM TCAM RIB FIB

## Scope and prerequisites

Two IOL-XE routers communicate through an IOL-L2 switch in VLAN10. The first fault removes a static route; the second uses an ingress ICMP classifier on R2. Separate positive controls prevent a healthy CAM or RIB from being mistaken for successful end-to-end forwarding. CAM aging is fixed at600seconds for the short exercise. TCAM is discussed as the physical implementation of classifiers: virtual IOL does not expose physical ASIC allocation, TCAM capacity or hardware forwarding performance, and none is claimed as tested.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> SW Ethernet0/0
- R2 Ethernet0/0 <-> SW Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Correlate a successful flow with distinct RIB, software CEF and learned CAM evidence.
2. Withdraw only the destination route while leaving learned L2 connectivity intact.
3. Apply an ingress packet filter with healthy route tables and observe real deny counters.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |
| R1 | `show ip route 192.0.2.2` | The RIB contains the endpoint static route. |
| R1 | `show ip cef 192.0.2.2 detail` | CEF resolves the expected next hop and egress interface. |
| SW | `show mac address-table dynamic` | The switch has learned both endpoint MACs on VLAN10. |

## Transition: withdraw only the RIB route

On **R1**:

```ios
configure terminal
no ip route 192.0.2.2 255.255.255.255 198.18.0.2
end
```

- R1: `show ip route 192.0.2.2` -- The destination is absent from the RIB.
- R1: `show ip cef 192.0.2.2 detail` -- CEF has no usable destination forwarding entry.
- SW: `show mac address-table dynamic` -- The switch has learned both endpoint MACs on VLAN10.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- All three probes fail while the route is removed.

## Transition: restore the endpoint route

On **R1**:

```ios
configure terminal
ip route 192.0.2.2 255.255.255.255 198.18.0.2
end
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Three replies.
- R1: `show ip route 192.0.2.2` -- The RIB contains the endpoint static route.
- R1: `show ip cef 192.0.2.2 detail` -- CEF resolves the expected next hop and egress interface.
- SW: `show mac address-table dynamic` -- The switch has learned both endpoint MACs on VLAN10.

## Transition: filter endpoint ICMP on receive

On **R2**:

```ios
configure terminal
ip access-list extended ENDPOINT-FILTER
deny icmp host 192.0.2.1 host 192.0.2.2
permit ip any any
exit
interface Ethernet0/0
ip access-group ENDPOINT-FILTER in
end
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- All three probes are blocked while the RIB, CEF and CAM remain healthy.
- R1: `show ip route 192.0.2.2` -- The RIB contains the endpoint static route.
- R1: `show ip cef 192.0.2.2 detail` -- CEF resolves the expected next hop and egress interface.
- SW: `show mac address-table dynamic` -- The switch has learned both endpoint MACs on VLAN10.
- R2: `show access-lists ENDPOINT-FILTER` -- The classifier counts the actual dropped probes.

## Transition: restore unfiltered forwarding

On **R2**:

```ios
configure terminal
interface Ethernet0/0
no ip access-group ENDPOINT-FILTER in
end
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Three replies.
- R1: `show ip route 192.0.2.2` -- The RIB contains the endpoint static route.
- R1: `show ip cef 192.0.2.2 detail` -- CEF resolves the expected next hop and egress interface.
- SW: `show mac address-table dynamic` -- The switch has learned both endpoint MACs on VLAN10.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### R1

```ios
hostname R1
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
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.2 255.255.255.255 198.18.0.2
end
```

### R2

```ios
hostname R2
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
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.1 255.255.255.255 198.18.0.1
end
```

### SW

```ios
hostname SW
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
mac address-table aging-time 600 vlan 10
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
