# Route Redistribution Tags

## Scope and prerequisites

Requires three IOL-XE nodes with a single redistribution boundary. The control prefix 203.0.113.9/32 intentionally points to Null0 and is used only to test route policy; it is never presented as a reachable service. Both internal and external OSPF routes are explicitly eligible for EIGRP export, so the denial is not an accidental default exclusion. Route maps preserve origin policy using tags 100/200 and explicitly deny control tag 999. The exercise measures tag filtering and retagging, not loop freedom under multiple ASBRs. The real loopback endpoints remain reachable during the selective policy change.

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

1. Inspect actual route tags after OSPF/EIGRP redistribution and verify real endpoint forwarding.
2. Change the control prefix tag to pass the explicit export gate and observe downstream retagging.
3. Restore the denied tag and verify selective withdrawal without breaking the real endpoints.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip ospf neighbor` | The OSPF adjacency is FULL. |
| R2 | `show ip eigrp neighbors` | The EIGRP neighbor is actually present. |
| R1 | `show ip route 192.0.2.3` | The EIGRP-origin route carries its OSPF export tag. |
| R3 | `show ip route 192.0.2.1` | The OSPF-origin route carries its EIGRP export tag. |
| R2 | `show ip route 203.0.113.9` | The control prefix reaches the boundary with the denied input tag. |
| R3 | `show ip route 203.0.113.9` | The tag-filtered control prefix is absent from EIGRP. |
| R1 | `ping 192.0.2.3 source Loopback0 repeat 3` | The real endpoints forward traffic across the redistribution boundary. |

## Transition: permit the control prefix by changing its input tag

On **R1**:

```ios
configure terminal
router ospf 1
no redistribute static
exit
route-map STATIC-EXPORT permit 10
no set tag
set tag 998
exit
router ospf 1
redistribute static subnets route-map STATIC-EXPORT
end
```

- R2: `show ip route 203.0.113.9` -- The boundary observes the changed input tag.
- R3: `show ip route 203.0.113.9` -- EIGRP receives the permitted prefix with the export-policy tag.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The real endpoints forward traffic across the redistribution boundary.

## Transition: restore the denied input tag

On **R1**:

```ios
configure terminal
router ospf 1
no redistribute static
exit
route-map STATIC-EXPORT permit 10
no set tag
set tag 999
exit
router ospf 1
redistribute static subnets route-map STATIC-EXPORT
end
```

- R2: `show ip route 203.0.113.9` -- The denied input tag is restored.
- R3: `show ip route 203.0.113.9` -- The tag-filtered control prefix is absent from EIGRP.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The real endpoints forward traffic across the redistribution boundary.

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
 ip ospf network point-to-point
 exit
ip route 203.0.113.9 255.255.255.255 Null0
route-map STATIC-EXPORT permit 10
 set tag 999
 exit
router ospf 1
 router-id 192.0.2.1
 network 198.18.12.0 0.0.0.3 area 0
 network 192.0.2.1 0.0.0.0 area 0
 redistribute static subnets route-map STATIC-EXPORT
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
 ip ospf network point-to-point
 exit
interface Ethernet0/1
 ip address 198.18.23.1 255.255.255.252
 no shutdown
 exit
route-map O2E deny 10
 match tag 999
 exit
route-map O2E deny 20
 match tag 200
 exit
route-map O2E permit 30
 set tag 100
 exit
route-map E2O deny 10
 match tag 100
 exit
route-map E2O permit 20
 set tag 200
 exit
router ospf 1
 router-id 192.0.2.2
 network 198.18.12.0 0.0.0.3 area 0
 network 192.0.2.2 0.0.0.0 area 0
 redistribute eigrp 100 subnets route-map E2O
 exit
router eigrp 100
 network 198.18.23.0 0.0.0.3
 no auto-summary
 default-metric 10000 100 255 1 1500
 redistribute ospf 1 match internal external 1 external 2 route-map O2E
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
router eigrp 100
 network 198.18.23.0 0.0.0.3
 network 192.0.2.3 0.0.0.0
 no auto-summary
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

[Cisco redistribution and tagging reference](https://www.cisco.com/c/en/us/support/docs/ip/enhanced-interior-gateway-routing-protocol-eigrp/8606-redist.html). The single-ASBR scope of this workbook is narrower than a multiple-boundary redistribution design.
