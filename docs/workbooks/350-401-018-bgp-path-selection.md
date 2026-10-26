# BGP Path Selection

## Scope and prerequisites

Two IOL-XE routers use independent eBGP links A and B. The higher local preference on R1 initially selects B; adding two prepends makes that AS_PATH longer without changing its local preference. Fresh R2 ACL request counters identify the chosen ingress link, so successful pings cannot hide a policy change. Reply paths can be asymmetric. Default weights/origin/MED are unchanged; this demonstrates the listed best-path ordering, not all BGP tie-breakers or multipath throughput.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R1 Ethernet0/1 <-> R2 Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Ethernet0/1 | `ip address 198.18.1.2 255.255.255.252` |

## Tasks

1. Observe a higher-local-preference best path and its real request ingress port.
2. Prepend the same external AS on B and prove that local preference still wins.
3. Equalize local preference, verify the shorter A path in both RIB and fresh counters, and restore the original preference.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip route 192.0.2.2` | The RIB selects WAN B. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |

## Transition: measure initial B request path

On **R2**:

```ios
clear access-list counters AD-PRIMARY
clear access-list counters AD-SECONDARY
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The destination still responds, despite the changed request path.
- R2: `show access-lists AD-PRIMARY` -- Fresh request counters identify AD-PRIMARY as unused.
- R2: `show access-lists AD-SECONDARY` -- Fresh request counters identify AD-SECONDARY as used.

## Transition: lengthen B while keeping higher preference

On **R2**:

```ios
configure terminal
ip prefix-list R2-LOOP seq 5 permit 192.0.2.2/32
route-map PREPEND-B permit 10
match ip address prefix-list R2-LOOP
set as-path prepend 65002 65002
exit
route-map PREPEND-B permit 20
exit
router bgp 65002
neighbor 198.18.1.1 route-map PREPEND-B out
end
clear ip bgp 198.18.1.1 soft out
```

- R1: `show ip route 192.0.2.2` -- The RIB selects WAN B.
- R1: `show ip bgp 192.0.2.2` -- The longer path on B remains best because of its higher local preference.

## Transition: measure B despite its longer AS path

On **R2**:

```ios
clear access-list counters AD-PRIMARY
clear access-list counters AD-SECONDARY
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The destination still responds, despite the changed request path.
- R2: `show access-lists AD-PRIMARY` -- Fresh request counters identify AD-PRIMARY as unused.
- R2: `show access-lists AD-SECONDARY` -- Fresh request counters identify AD-SECONDARY as used.

## Transition: equalize local preference

On **R1**:

```ios
configure terminal
route-map PREFER-B permit 10
set local-preference 100
end
clear ip bgp 198.18.1.2 soft in
```

- R1: `show ip route 192.0.2.2` -- The RIB selects WAN A.

## Transition: measure the shorter A path

On **R2**:

```ios
clear access-list counters AD-PRIMARY
clear access-list counters AD-SECONDARY
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The destination still responds, despite the changed request path.
- R2: `show access-lists AD-PRIMARY` -- Fresh request counters identify AD-PRIMARY as used.
- R2: `show access-lists AD-SECONDARY` -- Fresh request counters identify AD-SECONDARY as unused.

## Transition: restore higher local preference on B

On **R1**:

```ios
configure terminal
route-map PREFER-B permit 10
set local-preference 200
end
clear ip bgp 198.18.1.2 soft in
```

- R1: `show ip route 192.0.2.2` -- The RIB selects WAN B.

## Transition: remove the test prepends

On **R2**:

```ios
configure terminal
router bgp 65002
no neighbor 198.18.1.1 route-map PREPEND-B out
end
clear ip bgp 198.18.1.1 soft out
```

- R1: `show ip route 192.0.2.2` -- The RIB selects WAN B.

## Transition: measure restored B request path

On **R2**:

```ios
clear access-list counters AD-PRIMARY
clear access-list counters AD-SECONDARY
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The destination still responds, despite the changed request path.
- R2: `show access-lists AD-PRIMARY` -- Fresh request counters identify AD-PRIMARY as unused.
- R2: `show access-lists AD-SECONDARY` -- Fresh request counters identify AD-SECONDARY as used.

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
interface Ethernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
route-map PREFER-B permit 10
 set local-preference 200
 exit
router bgp 65001
 bgp router-id 192.0.2.1
 network 192.0.2.1 mask 255.255.255.255
 neighbor 198.18.0.2 remote-as 65002
 neighbor 198.18.1.2 remote-as 65002
 neighbor 198.18.1.2 route-map PREFER-B in
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
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 exit
ip access-list extended AD-PRIMARY
 permit icmp host 192.0.2.1 host 192.0.2.2
 permit ip any any
 exit
interface Ethernet0/0
 ip access-group AD-PRIMARY in
 exit
ip access-list extended AD-SECONDARY
 permit icmp host 192.0.2.1 host 192.0.2.2
 permit ip any any
 exit
interface Ethernet0/1
 ip access-group AD-SECONDARY in
 exit
router bgp 65002
 bgp router-id 192.0.2.2
 network 192.0.2.2 mask 255.255.255.255
 neighbor 198.18.0.1 remote-as 65001
 neighbor 198.18.1.1 remote-as 65001
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
