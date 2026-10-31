# ENARSI Capstone: Inter-Area Routing and Selective BGP Export

## Scope and prerequisites

Four IOL-XE routers integrate an area10 customer, an area10/0 ABR, a border AS65000 and provider AS65001. The provider loopback198.19.0.80 is a real local service endpoint, not Internet access. Only that service /32 is redistributed into OSPF E1 with tag65001. The border exports the authorized customer192.0.2.1/32 through an explicit prefix allowlist; the customer also owns203.0.113.66/32, which must remain unexported. The provider ingress observer permits and counts actual alternate-source requests while their replies lack a return route. Expanding the allowlist must install the unapproved prefix in real provider BGP and make those round trips succeed. Removing it must withdraw only that return prefix, recover the failed alternate round trip and preserve authorized service. Each policy edit explicitly re-evaluates OSPF redistribution into BGP; it does not reset neighbor sessions. The lesson distinguishes routing admission from packet filtering and does not promise security from route absence, high availability, IPv6 coverage or complete exam readiness. Nominal RAM is4GiB.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- CUSTOMER Ethernet0/0 <-> ABR Ethernet0/0
- ABR Ethernet0/1 <-> BORDER Ethernet0/0
- BORDER Ethernet0/1 <-> PROVIDER Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| CUSTOMER | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| CUSTOMER | Loopback66 | `ip address 203.0.113.66 255.255.255.255` |
| CUSTOMER | Ethernet0/0 | `ip address 198.18.12.1 255.255.255.252` |
| ABR | Ethernet0/0 | `ip address 198.18.12.2 255.255.255.252` |
| ABR | Ethernet0/1 | `ip address 198.18.23.1 255.255.255.252` |
| BORDER | Ethernet0/0 | `ip address 198.18.23.2 255.255.255.252` |
| BORDER | Ethernet0/1 | `ip address 198.18.34.1 255.255.255.252` |
| PROVIDER | Loopback0 | `ip address 198.19.0.80 255.255.255.255` |
| PROVIDER | Ethernet0/0 | `ip address 198.18.34.2 255.255.255.252` |

## Tasks

1. Correlate two-area OSPF, selective eBGP redistribution and actual bidirectional service delivery.
2. Prove an unapproved source request reaches the service but lacks a provider return route; avoid calling route admission a packet firewall.
3. Broaden the export allowlist, observe the actual BGP route and successful alternate-source traffic, then restore the exact prefix policy and legitimate service.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| BORDER | `show ip route 192.0.2.1` | The customer prefix crosses the real area10/area0 boundary. |
| CUSTOMER | `show ip route 198.19.0.80` | Only the provider service is actually redistributed into OSPF as a tagged E1. |
| PROVIDER | `show ip route 192.0.2.1` | The provider actually installs the permitted return prefix. |
| PROVIDER | `show ip route 203.0.113.66` | The provider has no return route for the unapproved prefix. |
| CUSTOMER | `ping 198.19.0.80 source Loopback0 repeat 3` | The independent Loopback0 source completes real service round trips. |
| CUSTOMER | `ping 198.19.0.80 source Loopback66 repeat 3` | The independent Loopback66 source cannot complete round trips without the provider return route. |
| PROVIDER | `show access-lists OBSERVE` | The alternate-source request actually reaches the service link: return-route admission is not an ingress packet firewall. |

## Transition: broaden the customer export allowlist

On **BORDER**:

```ios
configure terminal
ip prefix-list CUSTOMERS seq 20 permit 203.0.113.66/32
router bgp 65000
no redistribute ospf 1
redistribute ospf 1 match internal external 1 external 2 route-map IGP-TO-BGP
end
```

- PROVIDER: `show ip route 203.0.113.66` -- The provider actually installs the permitted return prefix.
- CUSTOMER: `ping 198.19.0.80 source Loopback66 repeat 3` -- The independent Loopback66 source completes real service round trips.
- CUSTOMER: `ping 198.19.0.80 source Loopback0 repeat 3` -- The independent Loopback0 source completes real service round trips.
- CUSTOMER: `show ip route 198.19.0.80` -- Only the provider service is actually redistributed into OSPF as a tagged E1.
- PROVIDER: `show access-lists OBSERVE` -- The alternate-source request actually reaches the service link: return-route admission is not an ingress packet firewall.

## Transition: restore the exact allowed customer prefix

On **BORDER**:

```ios
configure terminal
no ip prefix-list CUSTOMERS seq 20 permit 203.0.113.66/32
router bgp 65000
no redistribute ospf 1
redistribute ospf 1 match internal external 1 external 2 route-map IGP-TO-BGP
end
```

- BORDER: `show ip route 192.0.2.1` -- The customer prefix crosses the real area10/area0 boundary.
- CUSTOMER: `show ip route 198.19.0.80` -- Only the provider service is actually redistributed into OSPF as a tagged E1.
- PROVIDER: `show ip route 192.0.2.1` -- The provider actually installs the permitted return prefix.
- PROVIDER: `show ip route 203.0.113.66` -- The provider has no return route for the unapproved prefix.
- CUSTOMER: `ping 198.19.0.80 source Loopback0 repeat 3` -- The independent Loopback0 source completes real service round trips.
- CUSTOMER: `ping 198.19.0.80 source Loopback66 repeat 3` -- The independent Loopback66 source cannot complete round trips without the provider return route.
- PROVIDER: `show access-lists OBSERVE` -- The alternate-source request actually reaches the service link: return-route admission is not an ingress packet firewall.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### CUSTOMER

```ios
hostname CUSTOMER
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
 ip address 203.0.113.66 255.255.255.255
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
 ip ospf 1 area 10
 ip ospf network point-to-point
 exit
interface Loopback0
 ip ospf 1 area 10
 ip ospf network point-to-point
 exit
interface Loopback66
 ip ospf 1 area 10
 ip ospf network point-to-point
 exit
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
 exit
router ospf 1
 router-id 192.0.2.2
 passive-interface default
 no passive-interface Ethernet0/0
 no passive-interface Ethernet0/1
 exit
interface Ethernet0/0
 ip ospf 1 area 10
 ip ospf network point-to-point
 exit
interface Ethernet0/1
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
end
```

### BORDER

```ios
hostname BORDER
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
 ip address 198.18.23.2 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.34.1 255.255.255.252
 no shutdown
 exit
router ospf 1
 router-id 192.0.2.3
 passive-interface default
 no passive-interface Ethernet0/0
 exit
interface Ethernet0/0
 ip ospf 1 area 0
 ip ospf network point-to-point
 exit
ip prefix-list CUSTOMERS seq 10 permit 192.0.2.1/32
ip prefix-list PROVIDER-SERVICE permit 198.19.0.80/32
route-map IGP-TO-BGP permit 10
 match ip address prefix-list CUSTOMERS
 exit
route-map BGP-TO-IGP permit 10
 match ip address prefix-list PROVIDER-SERVICE
 set tag 65001
 exit
router ospf 1
 redistribute bgp 65000 metric 20 metric-type 1 subnets route-map BGP-TO-IGP
 exit
router bgp 65000
 bgp router-id 192.0.2.3
 neighbor 198.18.34.2 remote-as 65001
 neighbor 198.18.34.2 timers 3 9
 redistribute ospf 1 match internal external 1 external 2 route-map IGP-TO-BGP
 exit
end
```

### PROVIDER

```ios
hostname PROVIDER
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
 ip address 198.19.0.80 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.34.2 255.255.255.252
 no shutdown
 ip access-group OBSERVE in
 exit
ip access-list extended OBSERVE
 permit icmp host 203.0.113.66 host 198.19.0.80 echo
 permit ip any any
 exit
router bgp 65001
 bgp router-id 198.19.0.80
 network 198.19.0.80 mask 255.255.255.255
 neighbor 198.18.34.1 remote-as 65000
 neighbor 198.18.34.1 timers 3 9
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
