# ENCOR Capstone Enterprise Edge

## Scope and prerequisites

Three IOL-XE routers form a dual-provider eBGP edge. EDGE advertises only192.0.2.1/32; each separate provider advertises only192.0.2.80/32 and owns an equivalent isolated loopback endpoint. Local preference200 vs100 selects ISP1. Actual edge requests explicitly source Loopback0, so provider return learning is required. Fresh per-provider ingress ACL counters identify the request path: the selected receiver must count packets and the other must have no selected echo-request matches, independently of route text or successful ping. Withdrawing ISP1 service origination must move forwarding to ISP2 while the alternate session remains healthy. Restoring the advertisement must reselect ISP1. A deliberate ISP2 local-preference250 error, applied with inbound soft refresh, must move traffic to ISP2 despite both sessions being up; restoring100 must restore intended forwarding. The equal service loopbacks model an anycast-style equivalent endpoint, not preservation of a stateful application. No Internet, physical provider, RPKI, BFD, WAN encryption or production firewall is instantiated. Nominal RAM is3GiB.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- EDGE Ethernet0/0 <-> ISP1 Ethernet0/0
- EDGE Ethernet0/1 <-> ISP2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| EDGE | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| EDGE | Ethernet0/0 | `ip address 198.18.1.1 255.255.255.252` |
| EDGE | Ethernet0/1 | `ip address 198.18.2.1 255.255.255.252` |
| ISP1 | Loopback0 | `ip address 192.0.2.80 255.255.255.255` |
| ISP1 | Ethernet0/0 | `ip address 198.18.1.2 255.255.255.252` |
| ISP2 | Loopback0 | `ip address 192.0.2.80 255.255.255.255` |
| ISP2 | Ethernet0/0 | `ip address 198.18.2.2 255.255.255.252` |

## Tasks

1. Verify both real eBGP sessions, per-provider prefix controls, preferred installed route and actual receiver-side packet path.
2. Withdraw only the preferred service advertisement and prove continued traffic through the alternate provider.
3. Recover the advertisement, introduce a local-preference mistake with both sessions healthy, and restore the intended provider path.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| EDGE | `show ip bgp summary` | The actual ISP1 BGP session has received the one allowed service prefix. |
| EDGE | `show ip bgp summary` | The actual ISP2 BGP session has received the one allowed service prefix. |
| EDGE | `show ip route 192.0.2.80` | The actual installed service route selects ISP1. |
| EDGE | `ping 192.0.2.80 source Loopback0 repeat 3` | The independent edge loopback source actually reaches the selected provider service. |

## Transition: reference clear first receiver request counters

On **ISP1**:

```ios
clear access-list counters PATH-MEASURE
```

- ISP1: `show access-lists PATH-MEASURE` -- The receiver records no selected service requests since its counter reset.

## Transition: reference measure selected provider with fresh receiver counters

On **ISP2**:

```ios
clear access-list counters PATH-MEASURE
```

- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent edge loopback source actually reaches the selected provider service.
- ISP1: `show access-lists PATH-MEASURE` -- The receiver records actual selected service requests.
- ISP2: `show access-lists PATH-MEASURE` -- The receiver records no selected service requests since its counter reset.

## Transition: withdraw only the preferred service advertisement

On **ISP1**:

```ios
configure terminal
router bgp 65002
no network 192.0.2.80 mask 255.255.255.255
end
```

- EDGE: `show ip bgp summary` -- The actual ISP2 BGP session has received the one allowed service prefix.
- EDGE: `show ip route 192.0.2.80` -- The actual installed service route selects ISP2.
- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent edge loopback source actually reaches the selected provider service.

## Transition: withdrawal clear first receiver request counters

On **ISP1**:

```ios
clear access-list counters PATH-MEASURE
```

- ISP1: `show access-lists PATH-MEASURE` -- The receiver records no selected service requests since its counter reset.

## Transition: withdrawal measure selected provider with fresh receiver counters

On **ISP2**:

```ios
clear access-list counters PATH-MEASURE
```

- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent edge loopback source actually reaches the selected provider service.
- ISP2: `show access-lists PATH-MEASURE` -- The receiver records actual selected service requests.
- ISP1: `show access-lists PATH-MEASURE` -- The receiver records no selected service requests since its counter reset.

## Transition: restore preferred service origination

On **ISP1**:

```ios
configure terminal
router bgp 65002
network 192.0.2.80 mask 255.255.255.255
end
```

- EDGE: `show ip bgp summary` -- The actual ISP1 BGP session has received the one allowed service prefix.
- EDGE: `show ip bgp summary` -- The actual ISP2 BGP session has received the one allowed service prefix.
- EDGE: `show ip route 192.0.2.80` -- The actual installed service route selects ISP1.
- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent edge loopback source actually reaches the selected provider service.

## Transition: advertisement recovery clear first receiver request counters

On **ISP1**:

```ios
clear access-list counters PATH-MEASURE
```

- ISP1: `show access-lists PATH-MEASURE` -- The receiver records no selected service requests since its counter reset.

## Transition: advertisement recovery measure selected provider with fresh receiver counters

On **ISP2**:

```ios
clear access-list counters PATH-MEASURE
```

- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent edge loopback source actually reaches the selected provider service.
- ISP1: `show access-lists PATH-MEASURE` -- The receiver records actual selected service requests.
- ISP2: `show access-lists PATH-MEASURE` -- The receiver records no selected service requests since its counter reset.

## Transition: introduce a preference mistake with healthy peers

On **EDGE**:

```ios
configure terminal
route-map ISP2-IN permit 10
set local-preference 250
exit
do clear ip bgp 198.18.2.2 soft in
end
```

- EDGE: `show ip bgp summary` -- The actual ISP1 BGP session has received the one allowed service prefix.
- EDGE: `show ip bgp summary` -- The actual ISP2 BGP session has received the one allowed service prefix.
- EDGE: `show ip route 192.0.2.80` -- The actual installed service route selects ISP2.
- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent edge loopback source actually reaches the selected provider service.

## Transition: preference mistake clear first receiver request counters

On **ISP1**:

```ios
clear access-list counters PATH-MEASURE
```

- ISP1: `show access-lists PATH-MEASURE` -- The receiver records no selected service requests since its counter reset.

## Transition: preference mistake measure selected provider with fresh receiver counters

On **ISP2**:

```ios
clear access-list counters PATH-MEASURE
```

- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent edge loopback source actually reaches the selected provider service.
- ISP2: `show access-lists PATH-MEASURE` -- The receiver records actual selected service requests.
- ISP1: `show access-lists PATH-MEASURE` -- The receiver records no selected service requests since its counter reset.

## Transition: restore intended provider preference

On **EDGE**:

```ios
configure terminal
route-map ISP2-IN permit 10
set local-preference 100
exit
do clear ip bgp 198.18.2.2 soft in
end
```

- EDGE: `show ip bgp summary` -- The actual ISP1 BGP session has received the one allowed service prefix.
- EDGE: `show ip bgp summary` -- The actual ISP2 BGP session has received the one allowed service prefix.
- EDGE: `show ip route 192.0.2.80` -- The actual installed service route selects ISP1.
- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent edge loopback source actually reaches the selected provider service.

## Transition: final recovery clear first receiver request counters

On **ISP1**:

```ios
clear access-list counters PATH-MEASURE
```

- ISP1: `show access-lists PATH-MEASURE` -- The receiver records no selected service requests since its counter reset.

## Transition: final recovery measure selected provider with fresh receiver counters

On **ISP2**:

```ios
clear access-list counters PATH-MEASURE
```

- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent edge loopback source actually reaches the selected provider service.
- ISP1: `show access-lists PATH-MEASURE` -- The receiver records actual selected service requests.
- ISP2: `show access-lists PATH-MEASURE` -- The receiver records no selected service requests since its counter reset.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### EDGE

```ios
hostname EDGE
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
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.2.1 255.255.255.252
 no shutdown
 exit
ip prefix-list EDGE-ONLY permit 192.0.2.1/32
route-map ISP1-IN permit 10
 set local-preference 200
 exit
route-map ISP2-IN permit 10
 set local-preference 100
 exit
router bgp 65001
 bgp router-id 192.0.2.1
 network 192.0.2.1 mask 255.255.255.255
 neighbor 198.18.1.2 remote-as 65002
 neighbor 198.18.1.2 timers 3 9
 neighbor 198.18.1.2 route-map ISP1-IN in
 neighbor 198.18.1.2 prefix-list EDGE-ONLY out
 neighbor 198.18.2.2 remote-as 65003
 neighbor 198.18.2.2 timers 3 9
 neighbor 198.18.2.2 route-map ISP2-IN in
 neighbor 198.18.2.2 prefix-list EDGE-ONLY out
 exit
end
```

### ISP1

```ios
hostname ISP1
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
 ip address 192.0.2.80 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 ip access-group PATH-MEASURE in
 exit
ip access-list extended PATH-MEASURE
 permit icmp host 192.0.2.1 host 192.0.2.80 echo
 permit ip any any
 exit
ip prefix-list SERVICE-ONLY permit 192.0.2.80/32
router bgp 65002
 bgp router-id 203.0.113.1
 network 192.0.2.80 mask 255.255.255.255
 neighbor 198.18.1.1 remote-as 65001
 neighbor 198.18.1.1 timers 3 9
 neighbor 198.18.1.1 prefix-list SERVICE-ONLY out
 exit
end
```

### ISP2

```ios
hostname ISP2
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
 ip address 192.0.2.80 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.2.2 255.255.255.252
 no shutdown
 ip access-group PATH-MEASURE in
 exit
ip access-list extended PATH-MEASURE
 permit icmp host 192.0.2.1 host 192.0.2.80 echo
 permit ip any any
 exit
ip prefix-list SERVICE-ONLY permit 192.0.2.80/32
router bgp 65003
 bgp router-id 203.0.113.2
 network 192.0.2.80 mask 255.255.255.255
 neighbor 198.18.2.1 remote-as 65001
 neighbor 198.18.2.1 timers 3 9
 neighbor 198.18.2.1 prefix-list SERVICE-ONLY out
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
