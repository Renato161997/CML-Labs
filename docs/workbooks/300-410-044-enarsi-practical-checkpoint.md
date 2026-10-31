# ENARSI Practical: Routing, DNS and Source Policy

## Scope and prerequisites

Three IOL-XE nodes provide a deliberately broken two-stage assessment. ABR uses area10 on its service link while SERVICE uses area20; no adjacency can form. A separate outbound ICMP rule also denies the authorized CLIENT Loopback0 source instead of the intended unauthorized Loopback66. The first repair must restore inter-area routing, but service traffic from the authorized source must still fail, resolve its actual DNS name and hit the exact ACL deny. A separate transit-source probe must reach the same service. The second repair changes only that ACL source selector, recovers authorized named-service traffic and still denies the unauthorized loopback with a measured counter. No user workstation, Internet DNS or production address is used. This practical checkpoint covers interacting OSPF, DNS and source-policy faults, not the entire exam blueprint. Nominal RAM is3GiB.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Deliberately broken: The service-facing OSPF area is mismatched and the source ACL denies the authorized loopback; the baseline checks intentionally diagnose both before the staged repairs. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- CLIENT Ethernet0/0 <-> ABR Ethernet0/0
- ABR Ethernet0/1 <-> SERVICE Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| CLIENT | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| CLIENT | Loopback66 | `ip address 192.0.2.66 255.255.255.255` |
| CLIENT | Ethernet0/0 | `ip address 198.18.12.1 255.255.255.252` |
| ABR | Ethernet0/0 | `ip address 198.18.12.2 255.255.255.252` |
| ABR | Ethernet0/1 | `ip address 198.18.23.1 255.255.255.252` |
| SERVICE | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| SERVICE | Ethernet0/0 | `ip address 198.18.23.2 255.255.255.252` |

## Tasks

1. Diagnose an OSPF area mismatch using working direct IP controls and missing remote service routes.
2. Repair the IGP, then distinguish successful DNS and healthy transit-source traffic from a source-specific service ACL failure.
3. Correct the ACL selector while preserving the unauthorized-source denial and verify its actual packet counter.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| ABR | `ping 198.18.23.2 source Ethernet0/1 repeat 3` | Direct IP connectivity works despite the OSPF area mismatch. |
| CLIENT | `show ip route 192.0.2.3` | The remote service route is absent. |
| SERVICE | `show ip ospf interface Ethernet0/0` | The service-side link has the deliberately wrong area. |

## Transition: repair the mismatched OSPF area

On **SERVICE**:

```ios
configure terminal
interface Ethernet0/0
ip ospf 1 area 10
end
```

- CLIENT: `show ip route 192.0.2.3` -- The service actually appears as an inter-area OSPF route.
- CLIENT: `ping service.example.test source Loopback0 repeat 3` -- The DNS-named service does not reply to the policy-selected source.
- CLIENT: `show hosts` -- The actual lab DNS lookup resolves the service address.
- CLIENT: `ping 192.0.2.3 source Ethernet0/0 repeat 3` -- A separate transit source proves that the same service and return path remain healthy.
- ABR: `show access-lists EXAM` -- The exact selected source rule counts real denied requests.

## Transition: correct the authorized-source policy selector

On **ABR**:

```ios
configure terminal
ip access-list extended EXAM
no 10
10 deny icmp host 192.0.2.66 host 192.0.2.3 echo
end
```

- CLIENT: `show ip route 192.0.2.3` -- The service actually appears as an inter-area OSPF route.
- CLIENT: `ping service.example.test source Loopback0 repeat 3` -- The DNS-named service replies to the authorized source.
- CLIENT: `show hosts` -- The actual lab DNS lookup resolves the service address.
- CLIENT: `ping 192.0.2.3 source Ethernet0/0 repeat 3` -- A separate transit source proves that the same service and return path remain healthy.
- CLIENT: `ping service.example.test source Loopback66 repeat 3` -- The DNS-named service does not reply to the policy-selected source.
- ABR: `show access-lists EXAM` -- The exact selected source rule counts real denied requests.
- ABR: `ping 198.18.23.2 source Ethernet0/1 repeat 3` -- Direct IP connectivity works despite the OSPF area mismatch.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

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
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface Loopback66
 ip address 192.0.2.66 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.12.1 255.255.255.252
 no shutdown
 exit
router ospf 1
 router-id 192.0.2.1
 passive-interface default
 no passive-interface Ethernet0/0
 no passive-interface Loopback0
 no passive-interface Loopback66
 exit
interface Ethernet0/0
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
interface Loopback0
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
interface Loopback66
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
ip domain lookup
ip name-server 198.18.23.2
end
```

### ABR

```ios
hostname ABR
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
 exit
interface Ethernet0/1
 ip address 198.18.23.1 255.255.255.252
 no shutdown
 ip access-group EXAM out
 exit
router ospf 1
 router-id 192.0.2.2
 passive-interface default
 no passive-interface Ethernet0/0
 no passive-interface Ethernet0/1
 exit
interface Ethernet0/0
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
interface Ethernet0/1
 ip ospf 1 area 10
 ip ospf network point-to-point
 exit
ip access-list extended EXAM
 10 deny icmp host 192.0.2.1 host 192.0.2.3 echo
 20 permit ip any any
 exit
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
interface Loopback0
 ip address 192.0.2.3 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.23.2 255.255.255.252
 no shutdown
 exit
router ospf 1
 router-id 192.0.2.3
 passive-interface default
 no passive-interface Ethernet0/0
 no passive-interface Loopback0
 exit
interface Ethernet0/0
 ip ospf 1 area 20
 ip ospf network point-to-point
 exit
interface Loopback0
 ip ospf 1 area 10
 ip ospf network point-to-point
 exit
ip dns server
ip host service.example.test 192.0.2.3
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
