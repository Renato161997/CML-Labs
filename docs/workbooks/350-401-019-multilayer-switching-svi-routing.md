# Multilayer Switching SVI Routing

## Scope and prerequisites

Three IOL reference nodes model a multilayer switch and two routed endpoints. CORE owns both gateway SVIs; the endpoints have explicit default routes. Local gateway replies do not prove inter-VLAN forwarding. The fault changes only global IPv4 forwarding. This tests software forwarding and SVI behavior, not TCAM capacity or hardware throughput.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- HOST10 Ethernet0/0 <-> CORE Ethernet0/0
- HOST20 Ethernet0/0 <-> CORE Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| CORE | Vlan10 | `ip address 198.18.10.1 255.255.255.0` |
| CORE | Vlan20 | `ip address 198.18.20.1 255.255.255.0` |
| HOST10 | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |
| HOST20 | Ethernet0/0 | `ip address 198.18.20.20 255.255.255.0` |

## Tasks

1. Verify actual traffic between independent clients in separate VLANs.
2. Disable global routing while preserving both local SVI gateways.
3. Restore forwarding and verify the full return path.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| HOST10 | `ping 198.18.20.20 repeat 3` | IPv4 crosses the routed VLAN boundary. |
| HOST20 | `ping 198.18.10.10 repeat 3` | All three probes succeed. |

## Transition: disable inter-VLAN routing

On **CORE**:

```ios
configure terminal
no ip routing
end
```

- HOST10: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- HOST20: `ping 198.18.20.1 repeat 3` -- All three probes succeed.
- HOST10: `ping 198.18.20.20 repeat 3` -- The protected segment drops all three probes.

## Transition: restore inter-VLAN routing

On **CORE**:

```ios
configure terminal
ip routing
end
```

- HOST10: `ping 198.18.20.20 repeat 3` -- IPv4 crosses the routed VLAN boundary.
- HOST20: `ping 198.18.10.10 repeat 3` -- All three probes succeed.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### CORE

```ios
hostname CORE
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
 name USERS
 exit
vlan 20
 name SERVICES
 exit
interface Vlan10
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 exit
interface Vlan20
 ip address 198.18.20.1 255.255.255.0
 no shutdown
 exit
interface Ethernet0/0
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface Ethernet0/1
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
 no shutdown
 exit
end
```

### HOST10

```ios
hostname HOST10
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

### HOST20

```ios
hostname HOST20
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
 ip address 198.18.20.20 255.255.255.0
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.20.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
