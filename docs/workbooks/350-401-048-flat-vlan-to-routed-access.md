# Flat VLAN To Routed Access

## Scope and prerequisites

Three IOL reference nodes start with VLAN10 stretched from the endpoint access switch to a distribution SVI. An explicit endpoint default models client gateway configuration; no DHCP option behavior is claimed. The access SVI suppresses ICMP redirects so the intermediate same-interface forwarding does not change endpoint routing implicitly. Migration first points the endpoint to the existing access SVI, then deliberately interrupts the service while changing both uplink ends to no-switchport IPv4 transit. The distribution SVI is shut, a return route is installed, and the access default moves to transit. Actual interface mode, client forwarding and reverse source-loopback traffic prove the migrated design. A missing distribution return route must break the service while the local access gateway remains healthy. Separate documented rollback steps restore the original Layer2 baseline and endpoint gateway. This is a maintenance-window exercise, not a zero-downtime migration claim. Nominal RAM is3GiB.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- DIST Ethernet0/0 <-> ACCESS Ethernet0/0
- CLIENT Ethernet0/0 <-> ACCESS Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| DIST | Vlan10 | `ip address 198.18.10.1 255.255.255.0` |
| DIST | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| ACCESS | Vlan10 | `ip address 198.18.10.2 255.255.255.0` |
| CLIENT | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |

## Tasks

1. Record a working stretched client VLAN with the gateway on distribution.
2. Move the endpoint gateway to access and convert the interswitch trunk to an actual routed transit.
3. Prove the new return route, isolate its failure, then execute a complete rollback.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `ping 198.18.10.1 repeat 3` | The initial distribution gateway is reachable. |
| CLIENT | `ping 192.0.2.1 source Ethernet0/0 repeat 3` | The client reaches the distribution loopback with a valid return path. |
| ACCESS | `show interfaces Ethernet0/0 switchport` | The initial uplink is a real Layer2 trunk. |

## Transition: move the endpoint default to access

On **CLIENT**:

```ios
configure terminal
no ip route 0.0.0.0 0.0.0.0 198.18.10.1
ip route 0.0.0.0 0.0.0.0 198.18.10.2
end
```

- CLIENT: `ping 198.18.10.2 repeat 3` -- The local access gateway remains reachable.
- CLIENT: `ping 192.0.2.1 source Ethernet0/0 repeat 3` -- The client reaches the distribution loopback with a valid return path.

## Transition: open the deliberate migration interruption

On **DIST**:

```ios
configure terminal
interface Ethernet0/0
shutdown
end
```

- CLIENT: `ping 192.0.2.1 repeat 3` -- The planned uplink interruption is visible to the service.
- CLIENT: `ping 198.18.10.2 repeat 3` -- The local access gateway remains reachable.

## Transition: convert the distribution uplink

On **DIST**:

```ios
configure terminal
interface Ethernet0/0
no switchport
ip address 198.18.0.1 255.255.255.252
no shutdown
exit
interface Vlan10
shutdown
exit
ip route 198.18.10.0 255.255.255.0 198.18.0.2
end
```

- DIST: `show interfaces Ethernet0/0 switchport` -- The interswitch interface is actually routed rather than a VLAN trunk.

## Transition: convert access and restore routed forwarding

On **ACCESS**:

```ios
configure terminal
interface Ethernet0/0
shutdown
no switchport
ip address 198.18.0.2 255.255.255.252
no shutdown
exit
no ip route 0.0.0.0 0.0.0.0 198.18.10.1
ip route 0.0.0.0 0.0.0.0 198.18.0.1
end
```

- ACCESS: `show interfaces Ethernet0/0 switchport` -- The interswitch interface is actually routed rather than a VLAN trunk.
- CLIENT: `ping 198.18.10.2 repeat 3` -- The local access gateway remains reachable.
- CLIENT: `ping 192.0.2.1 source Ethernet0/0 repeat 3` -- The client reaches the distribution loopback with a valid return path.
- DIST: `ping 198.18.10.10 source Loopback0 repeat 3` -- The distribution return route and endpoint reply path both work.

## Transition: withdraw only the distribution return route

On **DIST**:

```ios
configure terminal
no ip route 198.18.10.0 255.255.255.0 198.18.0.2
end
```

- CLIENT: `ping 192.0.2.1 repeat 3` -- The missing return path breaks end-to-end forwarding.
- CLIENT: `ping 198.18.10.2 repeat 3` -- The local access gateway remains reachable.

## Transition: restore the routed return path

On **DIST**:

```ios
configure terminal
ip route 198.18.10.0 255.255.255.0 198.18.0.2
end
```

- CLIENT: `ping 192.0.2.1 source Ethernet0/0 repeat 3` -- The client reaches the distribution loopback with a valid return path.

## Transition: rollback access to the VLAN trunk

On **ACCESS**:

```ios
configure terminal
interface Ethernet0/0
shutdown
no ip address
switchport
switchport trunk encapsulation dot1q
switchport mode trunk
switchport trunk allowed vlan 10,20
no shutdown
exit
no ip route 0.0.0.0 0.0.0.0 198.18.0.1
ip route 0.0.0.0 0.0.0.0 198.18.10.1
end
```

- CLIENT: `ping 198.18.10.2 repeat 3` -- The local access gateway remains reachable.

## Transition: rollback distribution to the original SVI

On **DIST**:

```ios
configure terminal
interface Ethernet0/0
shutdown
no ip address
switchport
switchport trunk encapsulation dot1q
switchport mode trunk
switchport trunk allowed vlan 10,20
no shutdown
exit
no ip route 198.18.10.0 255.255.255.0 198.18.0.2
interface Vlan10
no shutdown
end
```

- CLIENT: `ping 192.0.2.1 source Ethernet0/0 repeat 3` -- The client reaches the distribution loopback with a valid return path.

## Transition: restore the original endpoint gateway

On **CLIENT**:

```ios
configure terminal
no ip route 0.0.0.0 0.0.0.0 198.18.10.2
ip route 0.0.0.0 0.0.0.0 198.18.10.1
end
```

- CLIENT: `ping 192.0.2.1 source Ethernet0/0 repeat 3` -- The client reaches the distribution loopback with a valid return path.
- CLIENT: `ping 198.18.10.1 repeat 3` -- The initial flat-VLAN gateway is restored.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### DIST

```ios
hostname DIST
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
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Vlan10
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
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
ip routing
vlan 10
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface Vlan10
 ip address 198.18.10.2 255.255.255.0
 no shutdown
 no ip redirects
 exit
ip route 0.0.0.0 0.0.0.0 198.18.10.1
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
