# Campus Routing Blackhole

## Scope and prerequisites

Three isolated IOL-XE routers carry service loopbacks through OSPF area0. A static Null0 host route on the transit router wins over the learned service host route; actual RIB selection, failed service probes, a healthy remote transit probe and a FULL neighbor distinguish this forwarding blackhole from adjacency failure. After restoring OSPF selection, a separate R2 ingress ACL on the R3-facing link drops only echo replies from the service to the originating loopback. Its actual deny counter, healthy route and unaffected transit probe distinguish the return-path policy fault. Both faults are fully removed and the same service probe must recover. No external service, hardware forwarding capacity or physical campus failure timing is claimed. Nominal RAM is3GiB.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R2 Ethernet0/1 <-> R3 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Ethernet0/1 | `ip address 198.18.0.5 255.255.255.252` |
| R3 | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| R3 | Ethernet0/0 | `ip address 198.18.0.6 255.255.255.252` |

## Tasks

1. Separate healthy OSPF adjacency and transit reachability from service forwarding.
2. Install a preferred static discard for the service and verify its actual RIB selection.
3. Distinguish a return-direction ACL blackhole using packet counters, then recover the service.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R2 | `show ip ospf neighbor` | The upstream adjacency remains FULL despite the service fault. |
| R2 | `show ip route 192.0.2.3` | The service route is actually learned through OSPF. |
| R1 | `ping 192.0.2.3 source Loopback0 repeat 3` | The service loopbacks exchange actual end-to-end traffic. |
| R1 | `ping 198.18.0.6 source Loopback0 repeat 3` | The same remote router transit address remains reachable. |

## Transition: prefer a service discard route

On **R2**:

```ios
configure terminal
ip route 192.0.2.3 255.255.255.255 Null0
end
```

- R2: `show ip route 192.0.2.3` -- The actual selected service route discards through Null0.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The controlled data-plane fault blocks the service.
- R1: `ping 198.18.0.6 source Loopback0 repeat 3` -- The same remote router transit address remains reachable.
- R2: `show ip ospf neighbor` -- The upstream adjacency remains FULL despite the service fault.

## Transition: recover dynamic service forwarding

On **R2**:

```ios
configure terminal
no ip route 192.0.2.3 255.255.255.255 Null0
end
```

- R2: `show ip route 192.0.2.3` -- The service route is actually learned through OSPF.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The service loopbacks exchange actual end-to-end traffic.

## Transition: drop only service echo replies

On **R2**:

```ios
configure terminal
ip access-list extended SERVICE-RETURN
deny icmp host 192.0.2.3 host 192.0.2.1 echo-reply
permit ip any any
exit
interface Ethernet0/1
ip access-group SERVICE-RETURN in
end
```

- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The controlled data-plane fault blocks the service.
- R2: `show ip route 192.0.2.3` -- The service route is actually learned through OSPF.
- R2: `show ip ospf neighbor` -- The upstream adjacency remains FULL despite the service fault.
- R1: `ping 198.18.0.6 source Loopback0 repeat 3` -- The same remote router transit address remains reachable.
- R2: `show access-lists SERVICE-RETURN` -- The return policy counts actual blocked replies.

## Transition: remove the return-direction policy fault

On **R2**:

```ios
configure terminal
interface Ethernet0/1
no ip access-group SERVICE-RETURN in
end
```

- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The service loopbacks exchange actual end-to-end traffic.
- R2: `show ip route 192.0.2.3` -- The service route is actually learned through OSPF.
- R1: `ping 198.18.0.6 source Loopback0 repeat 3` -- The same remote router transit address remains reachable.

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
interface Loopback0
 ip ospf 10 area 0
 exit
router ospf 10
 router-id 192.0.2.1
 passive-interface Loopback0
 exit
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
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
interface Loopback0
 ip ospf 10 area 0
 exit
router ospf 10
 router-id 192.0.2.2
 passive-interface Loopback0
 exit
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 exit
interface Ethernet0/1
 ip address 198.18.0.5 255.255.255.252
 no shutdown
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
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
interface Loopback0
 ip ospf 10 area 0
 exit
router ospf 10
 router-id 192.0.2.3
 passive-interface Loopback0
 exit
interface Ethernet0/0
 ip address 198.18.0.6 255.255.255.252
 no shutdown
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
