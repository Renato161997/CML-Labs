# OSPF EIGRP Redistribution

## Scope and prerequisites

One IOL-XE boundary connects an OSPF domain and EIGRP100. Exact endpoint prefix-lists constrain both export directions; unrelated routes cannot feed back across the boundary. The EIGRP default seed metric is required for the imported OSPF route, while the reverse EIGRP-to-OSPF E1 export remains observable. This is a one-boundary metric exercise, not evidence of multi-ASBR loop freedom.

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

1. Redistribute only the two explicitly allowed endpoint prefixes across one ASBR.
2. Remove the EIGRP seed metric and refresh its OSPF redistribution.
3. Verify one-way route withdrawal with healthy internal controls, then restore the metric.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R3 | `show ip route 192.0.2.1` | The foreign endpoint is installed as an external EIGRP route. |
| R1 | `show ip route ospf` | OSPF installs the selectively redistributed EIGRP endpoint as E1. |
| R3 | `ping 192.0.2.1 source Loopback0 repeat 3` | The endpoint flow crosses both routing domains. |

## Transition: withdraw the EIGRP seed metric

On **R2**:

```ios
configure terminal
router eigrp 100
no default-metric
no redistribute ospf 1
redistribute ospf 1 route-map LEFT-ONLY
end
```

- R3: `show ip route 192.0.2.1` -- The external endpoint is no longer eligible.
- R1: `show ip route ospf` -- OSPF installs the selectively redistributed EIGRP endpoint as E1.
- R3: `ping 192.0.2.1 source Loopback0 repeat 3` -- The endpoint flow fails without the foreign endpoint route.
- R3: `ping 192.0.2.2 source Loopback0 repeat 3` -- The native EIGRP domain and its return path still work.

## Transition: restore the seed metric and export

On **R2**:

```ios
configure terminal
router eigrp 100
default-metric 100000 100 255 1 1500
no redistribute ospf 1
redistribute ospf 1 route-map LEFT-ONLY
end
```

- R3: `show ip route 192.0.2.1` -- The foreign endpoint is installed as an external EIGRP route.
- R1: `show ip route ospf` -- OSPF installs the selectively redistributed EIGRP endpoint as E1.
- R3: `ping 192.0.2.1 source Loopback0 repeat 3` -- The endpoint flow crosses both routing domains.

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
 router-id 203.0.113.1
 passive-interface Loopback0
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
ip prefix-list LEFT-ONLY seq 5 permit 192.0.2.1/32
ip prefix-list RIGHT-ONLY seq 5 permit 192.0.2.3/32
route-map LEFT-ONLY permit 10
 match ip address prefix-list LEFT-ONLY
 exit
route-map RIGHT-ONLY permit 10
 match ip address prefix-list RIGHT-ONLY
 exit
router ospf 1
 router-id 203.0.113.2
 passive-interface Loopback0
 network 198.18.12.0 0.0.0.3 area 0
 network 192.0.2.2 0.0.0.0 area 0
 redistribute eigrp 100 metric 20 metric-type 1 subnets route-map RIGHT-ONLY
 exit
router eigrp 100
 no auto-summary
 network 198.18.23.0 0.0.0.3
 network 192.0.2.2 0.0.0.0
 passive-interface Loopback0
 default-metric 100000 100 255 1 1500
 redistribute ospf 1 route-map LEFT-ONLY
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
 no auto-summary
 network 198.18.23.0 0.0.0.3
 network 192.0.2.3 0.0.0.0
 passive-interface Loopback0
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
