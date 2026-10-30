# VRF Lite Shared Services

## Scope and prerequisites

Four IOL-XE routers implement local VRF-Lite/shared-services routing with actual BGP route-target import on PE. There are no BGP neighbors and no MPLS provider core: the tested BGP behavior is local VPNv4 import, not a remote controller or a labeled WAN. BLUE, RED and SERVICES have distinct RDs; tenant RTs are10/20 and the shared-service RT is99. CE loopbacks use documentation addresses and every CE has an explicit return/default route. PE exports actual static customer routes; imported tenant routes are not re-originated as service exports. All three PE interfaces belong to their own VRF. Nominal RAM is4x1024MiB. The shared-service VRF imports each tenant return route, while the tenants import only the service RT. Removing the service import from BLUE must affect that tenant alone; RED access and tenant isolation remain healthy, then the original service path is restored.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- PE Ethernet0/0 <-> BLUE-CE Ethernet0/0
- PE Ethernet0/1 <-> RED-CE Ethernet0/0
- PE Ethernet0/2 <-> SERVICE-CE Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| PE | Ethernet0/0 | `ip address 198.18.10.1 255.255.255.252` |
| PE | Ethernet0/1 | `ip address 198.18.20.1 255.255.255.252` |
| PE | Ethernet0/2 | `ip address 198.18.99.1 255.255.255.252` |
| BLUE-CE | Ethernet0/0 | `ip address 198.18.10.2 255.255.255.252` |
| BLUE-CE | Loopback0 | `ip address 192.0.2.10 255.255.255.255` |
| RED-CE | Ethernet0/0 | `ip address 198.18.20.2 255.255.255.252` |
| RED-CE | Loopback0 | `ip address 198.51.100.20 255.255.255.255` |
| SERVICE-CE | Ethernet0/0 | `ip address 198.18.99.2 255.255.255.252` |
| SERVICE-CE | Loopback0 | `ip address 203.0.113.80 255.255.255.255` |
| SERVICE-CE | Loopback1 | `ip address 203.0.113.81 255.255.255.255` |

## Tasks

1. Verify separate tenant RIBs, real local VPNv4 route-target imports and sourced shared-service forwarding.
2. Prove tenant-to-tenant isolation and the absence of a global fallback route.
3. Change only the intended import or ingress policy, observe the corresponding data-plane effect and recover.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| PE | `show ip route vrf BLUE 203.0.113.80` | BLUE actually imports the service route through local VPNv4 route-target policy. |
| BLUE-CE | `ping 203.0.113.80 source Loopback0 repeat 3` | Actual sourced traffic reaches the permitted destination. |
| RED-CE | `ping 203.0.113.80 source Loopback0 repeat 3` | Actual sourced traffic reaches the permitted destination. |
| BLUE-CE | `ping 198.51.100.20 source Loopback0 repeat 3` | Actual sourced traffic cannot cross the intended policy boundary. |
| RED-CE | `ping 192.0.2.10 source Loopback0 repeat 3` | Actual sourced traffic cannot cross the intended policy boundary. |
| PE | `show ip route 203.0.113.80` | The global RIB has no fallback service route. |

## Transition: withdraw only BLUE shared-service import

On **PE**:

```ios
configure terminal
ip vrf BLUE
no route-target import 65000:99
end
```

- PE: `show ip route vrf BLUE 203.0.113.80` -- Only BLUE loses the imported service route.
- BLUE-CE: `ping 203.0.113.80 source Loopback0 repeat 3` -- Actual sourced traffic cannot cross the intended policy boundary.
- RED-CE: `ping 203.0.113.80 source Loopback0 repeat 3` -- Actual sourced traffic reaches the permitted destination.
- BLUE-CE: `ping 198.51.100.20 source Loopback0 repeat 3` -- Actual sourced traffic cannot cross the intended policy boundary.

## Transition: restore BLUE shared-service access

On **PE**:

```ios
configure terminal
ip vrf BLUE
route-target import 65000:99
end
```

- PE: `show ip route vrf BLUE 203.0.113.80` -- BLUE actually imports the service route through local VPNv4 route-target policy.
- BLUE-CE: `ping 203.0.113.80 source Loopback0 repeat 3` -- Actual sourced traffic reaches the permitted destination.
- RED-CE: `ping 203.0.113.80 source Loopback0 repeat 3` -- Actual sourced traffic reaches the permitted destination.
- BLUE-CE: `ping 198.51.100.20 source Loopback0 repeat 3` -- Actual sourced traffic cannot cross the intended policy boundary.
- RED-CE: `ping 192.0.2.10 source Loopback0 repeat 3` -- Actual sourced traffic cannot cross the intended policy boundary.
- PE: `show ip route 203.0.113.80` -- The global RIB has no fallback service route.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### PE

```ios
hostname PE
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
no logging console
ip vrf BLUE
 rd 65000:10
 route-target export 65000:10
 route-target import 65000:99
 exit
ip vrf RED
 rd 65000:20
 route-target export 65000:20
 route-target import 65000:99
 exit
ip vrf SERVICES
 rd 65000:99
 route-target export 65000:99
 route-target import 65000:10
 route-target import 65000:20
 exit
interface Ethernet0/0
 ip vrf forwarding BLUE
 ip address 198.18.10.1 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip vrf forwarding RED
 ip address 198.18.20.1 255.255.255.252
 no shutdown
 exit
interface Ethernet0/2
 ip vrf forwarding SERVICES
 ip address 198.18.99.1 255.255.255.252
 no shutdown
 exit
ip route vrf BLUE 192.0.2.10 255.255.255.255 198.18.10.2
ip route vrf RED 198.51.100.20 255.255.255.255 198.18.20.2
ip route vrf SERVICES 203.0.113.80 255.255.255.255 198.18.99.2
ip route vrf SERVICES 203.0.113.81 255.255.255.255 198.18.99.2
router bgp 65000
 bgp router-id 192.0.2.254
 no bgp default ipv4-unicast
 address-family ipv4 vrf BLUE
  redistribute static
 exit-address-family
 address-family ipv4 vrf RED
  redistribute static
 exit-address-family
 address-family ipv4 vrf SERVICES
  redistribute static
 exit-address-family
 exit
end
```

### BLUE-CE

```ios
hostname BLUE-CE
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
no logging console
interface Ethernet0/0
 ip address 198.18.10.2 255.255.255.252
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.10 255.255.255.255
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.10.1
end
```

### RED-CE

```ios
hostname RED-CE
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
no logging console
interface Ethernet0/0
 ip address 198.18.20.2 255.255.255.252
 no shutdown
 exit
interface Loopback0
 ip address 198.51.100.20 255.255.255.255
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.20.1
end
```

### SERVICE-CE

```ios
hostname SERVICE-CE
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
no logging console
interface Ethernet0/0
 ip address 198.18.99.2 255.255.255.252
 no shutdown
 exit
interface Loopback0
 ip address 203.0.113.80 255.255.255.255
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.99.1
interface Loopback1
 ip address 203.0.113.81 255.255.255.255
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

See [Cisco local route-target leaking between VRFs](https://www.cisco.com/c/en/us/support/docs/multiprotocol-label-switching-mpls/multiprotocol-label-switching-vpns-mpls-vpns/47807-routeleaking.html). The live packet tests determine support on this installed IOL-XE image.
