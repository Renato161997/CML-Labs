# SCOR Checkpoint: Exposure, Policy and Routing Evidence

## Scope and prerequisites

Three actual IOL-XE routers connect two native HTTP peers. The only client route to 198.18.20.0/24 comes from R2's controlled redistribution of its externally learned BGP service into OSPF. R3 learns the client return prefix from R2's BGP network statement backed by an actual OSPF RIB entry. There are no router static/default fallback routes. Hosts have only the necessary remote fixture subnet route through their local router. Independent RIB, adjacency and actual end-to-end HTTP/ICMP establish both directions.

Two actual service listeners on OUTSIDE use TCP 8080 as application and TCP 9090 as an administration-port fixture; the latter is not a real administrative product. Client ingress CHECKPOINT-IN permits only the fixed application flow, denies the administration-port request, permits ICMP and then denies everything else. Local positive controls prove both listeners exist before a denial can be called an access-policy outcome. All addresses are isolated exercise networks. The shared packet/peer implementation remains unchanged.

These checkpoints combine the explicitly listed routing and stateless IPv4 ACL behaviors. They are not complete exam simulations, stateful NGFW, malware detection, endpoint posture, a vendor controller or a production topology. A finite traffic matrix is not a universal policy-equivalence proof. Nominal RAM is 4096MiB; no real credentials, Internet connector or existing user lab is needed. Stop/wipe only the imported copy.

Insert a deliberately unsafe administration-port permit before the existing deny: the actual remote 9090 request must now succeed with its observed client peer, while application, routes and ICMP remain healthy. Remove only that permit and prove the remote administration request is denied again without losing its local listener or the allowed application. Then withdraw the service through BGP policy while OSPF and the bound ACL remain healthy: the resulting application failure is an availability failure, not evidence of improved filtering. Restore the service and recover the original safe matrix.

Use licensed reference images for iol-xe, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- INSIDE eth1 <-> R1 Ethernet0/0
- R1 Ethernet0/1 <-> R2 Ethernet0/0
- R2 Ethernet0/1 <-> R3 Ethernet0/0
- R3 Ethernet0/1 <-> OUTSIDE eth1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Ethernet0/0 | `ip address 198.18.10.1 255.255.255.0` |
| R1 | Ethernet0/1 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Ethernet0/1 | `ip address 198.18.0.5 255.255.255.252` |
| R3 | Ethernet0/0 | `ip address 198.18.0.6 255.255.255.252` |
| R3 | Ethernet0/1 | `ip address 198.18.20.1 255.255.255.0` |
| INSIDE | eth1 | `198.18.10.10/24` |
| OUTSIDE | eth1 | `198.18.20.20/24` |

## Tasks

1. Trace real OSPF/BGP service and return routes plus actual endpoint packets without static/default fallbacks.
2. Distinguish routing unavailability from an access-policy denial by preserving independent positive controls.
3. Apply one bounded fault at a time and restore the measured clean traffic matrix.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip ospf neighbor` | The actual R1/R2 OSPF neighbor is FULL. |
| R2 | `show ip bgp summary` | The actual external BGP session remains established even when its service prefix is filtered. |
| R2 | `show ip bgp 198.18.20.0` | The border learns the service from the directly connected external BGP peer. |
| R1 | `show ip route 198.18.20.20` | The actual frontend RIB learns the service through OSPF, not a default/static fallback. |
| R3 | `show ip route 198.18.10.10` | The actual service-side router learns the client return route through BGP. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.20.20 --port 9090` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| INSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| INSIDE | `python3 /lab/t.py probe 198.18.20.20 --port 9090` | The actual plain-HTTP connection is blocked while its separately checked server stays healthy. |
| INSIDE | `ping -n -c 3 -W 2 198.18.20.20` | All three actual end-to-end ICMP control packets cross the complete routed path. |
| R1 | `show ip interface Ethernet0/0` | The exact client ingress ACL remains bound. |

## Transition: introduce an unsafe administration-port exception

On **R1**:

```ios
configure terminal
ip access-list extended CHECKPOINT-IN
5 permit tcp host 198.18.10.10 host 198.18.20.20 eq 9090
end
```

- R1: `show ip ospf neighbor` -- The actual R1/R2 OSPF neighbor is FULL.
- R2: `show ip bgp 198.18.20.0` -- The border learns the service from the directly connected external BGP peer.
- R1: `show ip route 198.18.20.20` -- The actual frontend RIB learns the service through OSPF, not a default/static fallback.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- All three actual end-to-end ICMP control packets cross the complete routed path.
- R1: `show ip interface Ethernet0/0` -- The exact client ingress ACL remains bound.

## Transition: remove only the unsafe exception

On **R1**:

```ios
configure terminal
ip access-list extended CHECKPOINT-IN
no 5
end
```

- R1: `show ip ospf neighbor` -- The actual R1/R2 OSPF neighbor is FULL.
- R2: `show ip bgp summary` -- The actual external BGP session remains established even when its service prefix is filtered.
- R2: `show ip bgp 198.18.20.0` -- The border learns the service from the directly connected external BGP peer.
- R1: `show ip route 198.18.20.20` -- The actual frontend RIB learns the service through OSPF, not a default/static fallback.
- R3: `show ip route 198.18.10.10` -- The actual service-side router learns the client return route through BGP.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- All three actual end-to-end ICMP control packets cross the complete routed path.
- R1: `show ip interface Ethernet0/0` -- The exact client ingress ACL remains bound.

## Transition: reject only the external service announcement

On **R2**:

```ios
configure terminal
router bgp 65001
neighbor 198.18.0.6 prefix-list DROP-SERVICE in
exit
do clear ip bgp 198.18.0.6 soft in
end
```

- R1: `show ip ospf neighbor` -- The actual R1/R2 OSPF neighbor is FULL.
- R2: `show ip bgp summary` -- The actual external BGP session remains established even when its service prefix is filtered.
- R1: `show ip route 198.18.20.20` -- The actual frontend RIB has no usable service route.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- R1: `show ip interface Ethernet0/0` -- The exact client ingress ACL remains bound.

## Transition: restore the specific accepted BGP service

On **R2**:

```ios
configure terminal
router bgp 65001
no neighbor 198.18.0.6 prefix-list DROP-SERVICE in
exit
do clear ip bgp 198.18.0.6 soft in
end
```

- R1: `show ip ospf neighbor` -- The actual R1/R2 OSPF neighbor is FULL.
- R2: `show ip bgp summary` -- The actual external BGP session remains established even when its service prefix is filtered.
- R2: `show ip bgp 198.18.20.0` -- The border learns the service from the directly connected external BGP peer.
- R1: `show ip route 198.18.20.20` -- The actual frontend RIB learns the service through OSPF, not a default/static fallback.
- R3: `show ip route 198.18.10.10` -- The actual service-side router learns the client return route through BGP.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -n -c 3 -W 2 198.18.20.20` -- All three actual end-to-end ICMP control packets cross the complete routed path.
- R1: `show ip interface Ethernet0/0` -- The exact client ingress ACL remains bound.

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
no logging console
interface Ethernet0/0
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 ip access-group CHECKPOINT-IN in
 exit
interface Ethernet0/1
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 ip ospf 10 area 0
 exit
ip access-list extended CHECKPOINT-IN
 10 permit tcp host 198.18.10.10 host 198.18.20.20 eq 8080
 20 deny tcp any host 198.18.20.20 eq 9090
 30 permit icmp any any
 40 deny ip any any
 exit
router ospf 10
 router-id 192.0.2.1
 passive-interface Ethernet0/0
 network 198.18.10.0 0.0.0.255 area 0
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
no logging console
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 ip ospf 10 area 0
 exit
interface Ethernet0/1
 ip address 198.18.0.5 255.255.255.252
 no shutdown
 exit
ip prefix-list SERVICE seq 10 permit 198.18.20.0/24
ip prefix-list DROP-SERVICE seq 10 deny 198.18.20.0/24
ip prefix-list DROP-SERVICE seq 20 permit 0.0.0.0/0 le 32
route-map BGP-SERVICE-TO-OSPF permit 10
 match ip address prefix-list SERVICE
 exit
router ospf 10
 router-id 192.0.2.2
 redistribute bgp 65001 metric 20 metric-type 1 subnets route-map BGP-SERVICE-TO-OSPF
 exit
router bgp 65001
 bgp router-id 192.0.2.2
 neighbor 198.18.0.6 remote-as 65002
 neighbor 198.18.0.6 timers 3 9
 network 198.18.10.0 mask 255.255.255.0
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
no logging console
interface Ethernet0/0
 ip address 198.18.0.6 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.20.1 255.255.255.0
 no shutdown
 exit
router bgp 65002
 bgp router-id 192.0.2.3
 neighbor 198.18.0.5 remote-as 65001
 neighbor 198.18.0.5 timers 3 9
 network 198.18.20.0 mask 255.255.255.0
 exit
end
```

### Actual endpoint listeners and packet observations

The [unchanged HTTP peer fixture](../../examples/security/traffic_fixture.py) is embedded on INSIDE and OUTSIDE. Their startup scripts assign the listed endpoint addresses, install only the remote fixture-subnet route through the local router, and start their HTTP listeners. OUTSIDE also starts the explicitly synthetic administration-port listener on 9090. Responses report the actual observed peer. Inspect the native startup files in the YAML for the complete launch configuration.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
