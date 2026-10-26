# OSPF Stub And NSSA

## Scope and prerequisites

Requires three IOL-XE nodes. R2 is the area 0/10 ABR; R3 exports only its loopback through an explicit connected-route map. A stub area cannot host this ASBR export, so the exercise removes redistribution before converting both ends. The withdrawal is evidence of removing that export, not proof that a stub silently accepts an ASBR and filters it. The stub default and matching adjacency are checked separately. The complete NSSA baseline is restored at the end.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R2 Ethernet0/1 <-> R3 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.12.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.12.2 255.255.255.252` |
| R2 | Ethernet0/1 | `ip address 198.18.23.1 255.255.255.252` |
| R3 | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| R3 | Ethernet0/0 | `ip address 198.18.23.2 255.255.255.252` |

## Tasks

1. Observe NSSA Type-7 export and actual ABR Type-5 translation.
2. Remove the ASBR export before converting the area to a stub, then verify its default route.
3. Restore matching NSSA settings and external redistribution, verifying forwarding again.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R3 | `show ip ospf neighbor` | The leaf and ABR agree on the area type and form a FULL adjacency. |
| R2 | `show ip ospf database nssa-external` | The NSSA carries the exported loopback in an actual Type-7 LSA. |
| R1 | `show ip ospf database external` | The ABR translates the NSSA export into a Type-5 LSA outside area 10. |
| R2 | `show ip route ospf` | The ABR installs an NSSA external route. |
| R1 | `show ip route ospf` | The normal area installs the translated external route. |
| R1 | `ping 192.0.2.3 source Loopback0 repeat 3` | The exported loopback is reachable with a working return route. |

## Transition: withdraw the NSSA export before conversion

On **R3**:

```ios
configure terminal
router ospf 1
no redistribute connected
end
```

- R1: `show ip route 192.0.2.3` -- The destination prefix is absent from this RIB.

## Transition: convert ABR to stub

On **R2**:

```ios
configure terminal
router ospf 1
no area 10 nssa
area 10 stub
end
```

- R2: `show running-config | section router ospf` -- The ABR is configured for a stub area; the peer still needs conversion.

## Transition: convert leaf to matching stub

On **R3**:

```ios
configure terminal
router ospf 1
no area 10 nssa
area 10 stub
end
```

- R3: `show ip ospf neighbor` -- The leaf and ABR agree on the area type and form a FULL adjacency.
- R3: `show ip route 0.0.0.0` -- The stub receives the actual ABR default route.
- R1: `show ip route 192.0.2.3` -- The destination prefix is absent from this RIB.

## Transition: restore ABR NSSA mode

On **R2**:

```ios
configure terminal
router ospf 1
no area 10 stub
area 10 nssa
end
```

- R2: `show running-config | section router ospf` -- The ABR is back in NSSA mode; the peer still needs restoration.

## Transition: restore matching leaf NSSA mode

On **R3**:

```ios
configure terminal
router ospf 1
no area 10 stub
area 10 nssa
end
```

- R3: `show ip ospf neighbor` -- The leaf and ABR agree on the area type and form a FULL adjacency.
- R1: `show ip route 192.0.2.3` -- The destination prefix is absent from this RIB.

## Transition: restore controlled NSSA export

On **R3**:

```ios
configure terminal
router ospf 1
redistribute connected subnets route-map EXPORT-LOOP
end
```

- R2: `show ip ospf database nssa-external` -- The NSSA carries the exported loopback in an actual Type-7 LSA.
- R1: `show ip ospf database external` -- The ABR translates the NSSA export into a Type-5 LSA outside area 10.
- R2: `show ip route ospf` -- The ABR installs an NSSA external route.
- R1: `show ip route ospf` -- The normal area installs the translated external route.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The exported loopback is reachable with a working return route.

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
 ip address 198.18.12.1 255.255.255.252
 no shutdown
 exit
router ospf 1
 router-id 192.0.2.1
 network 198.18.12.0 0.0.0.3 area 0
 network 192.0.2.1 0.0.0.0 area 0
 exit
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
 ip address 198.18.12.2 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.23.1 255.255.255.252
 no shutdown
 exit
router ospf 1
 router-id 192.0.2.2
 network 198.18.12.0 0.0.0.3 area 0
 network 198.18.23.0 0.0.0.3 area 10
 network 192.0.2.2 0.0.0.0 area 0
 area 10 nssa
 exit
end
```

### R3

```ios
hostname R3
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
 ip address 192.0.2.3 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.23.2 255.255.255.252
 no shutdown
 exit
ip prefix-list EXPORT-LOOP permit 192.0.2.3/32
route-map EXPORT-LOOP permit 10
 match ip address prefix-list EXPORT-LOOP
 exit
router ospf 1
 router-id 192.0.2.3
 network 198.18.23.0 0.0.0.3 area 10
 area 10 nssa
 redistribute connected subnets route-map EXPORT-LOOP
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

[Cisco protocol reference](https://www.cisco.com/c/en/us/support/docs/ip/open-shortest-path-first-ospf/6208-nssa.html). Actual support and executed checks are recorded in the live results.
