# Troubleshooting Path

## Scope and prerequisites

Three IOL-XE routers form a routed linear path, with loopback endpoints192.0.2.1 and192.0.2.80 and separate /30 transport links. Every primary service probe explicitly uses the client loopback source; a default egress-interface source would conceal a missing endpoint return route. Removing only the service return route must fail that exchange while the first hop and TRANSIT-originated final-hop probe stay healthy. A separate transit ACL denies only client-to-service echo requests: reverse-originated echo traffic must still complete, intended routes stay installed and the actual deny counter must increment. A third fault replaces the client destination route with Null0, while neighboring and final-hop controls remain healthy; it is a local forwarding decision, not an application outage. Each distinct repair restores sourced traffic and both routes. This is actual isolated packet-path diagnosis, not a controller assurance product, Internet reachability or application availability guarantee. Nominal RAM is3GiB.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- EDGE Ethernet0/0 <-> TRANSIT Ethernet0/0
- TRANSIT Ethernet0/1 <-> SERVICE Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| EDGE | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| EDGE | Ethernet0/0 | `ip address 198.18.12.1 255.255.255.252` |
| TRANSIT | Ethernet0/0 | `ip address 198.18.12.2 255.255.255.252` |
| TRANSIT | Ethernet0/1 | `ip address 198.18.23.1 255.255.255.252` |
| SERVICE | Ethernet0/0 | `ip address 198.18.23.2 255.255.255.252` |
| SERVICE | Loopback0 | `ip address 192.0.2.80 255.255.255.255` |

## Tasks

1. Validate independent source/service traffic, the first and final hop, and explicit routes in both directions.
2. Distinguish a missing return route from a directional transit ACL using healthy neighboring and reverse-request controls.
3. Diagnose a source Null0 route independently of service health, then restore the complete path.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| EDGE | `ping 192.0.2.80 source Loopback0 repeat 3` | The independent endpoint request completes. |
| SERVICE | `ping 192.0.2.1 source Loopback0 repeat 3` | The reverse-originated echo exchange completes even when only forward echo requests are filtered. |
| EDGE | `ping 198.18.12.2 repeat 3` | All three probes succeed. |
| TRANSIT | `ping 192.0.2.80 source Ethernet0/1 repeat 3` | The final-hop router still reaches the service using its own connected return path. |
| EDGE | `show ip route 192.0.2.80` | The source endpoint retains its intended destination next hop. |
| SERVICE | `show ip route 192.0.2.1` | The service retains its explicit return route. |

## Transition: remove only the endpoint return route

On **SERVICE**:

```ios
configure terminal
no ip route 192.0.2.1 255.255.255.255 198.18.23.1
end
```

- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent endpoint request fails under the named controlled path fault.
- EDGE: `ping 198.18.12.2 repeat 3` -- All three probes succeed.
- TRANSIT: `ping 192.0.2.80 source Ethernet0/1 repeat 3` -- The final-hop router still reaches the service using its own connected return path.
- EDGE: `show ip route 192.0.2.80` -- The source endpoint retains its intended destination next hop.
- SERVICE: `show ip route 192.0.2.1` -- The service lacks only the remote endpoint return route.

## Transition: recover the endpoint return path

On **SERVICE**:

```ios
configure terminal
ip route 192.0.2.1 255.255.255.255 198.18.23.1
end
```

- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent endpoint request completes.
- SERVICE: `ping 192.0.2.1 source Loopback0 repeat 3` -- The reverse-originated echo exchange completes even when only forward echo requests are filtered.
- EDGE: `ping 198.18.12.2 repeat 3` -- All three probes succeed.
- TRANSIT: `ping 192.0.2.80 source Ethernet0/1 repeat 3` -- The final-hop router still reaches the service using its own connected return path.
- EDGE: `show ip route 192.0.2.80` -- The source endpoint retains its intended destination next hop.
- SERVICE: `show ip route 192.0.2.1` -- The service retains its explicit return route.

## Transition: filter only forward echo requests

On **TRANSIT**:

```ios
configure terminal
interface Ethernet0/0
ip access-group REQUEST-FAULT in
end
```

- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent endpoint request fails under the named controlled path fault.
- SERVICE: `ping 192.0.2.1 source Loopback0 repeat 3` -- The reverse-originated echo exchange completes even when only forward echo requests are filtered.
- EDGE: `ping 198.18.12.2 repeat 3` -- All three probes succeed.
- TRANSIT: `ping 192.0.2.80 source Ethernet0/1 repeat 3` -- The final-hop router still reaches the service using its own connected return path.
- EDGE: `show ip route 192.0.2.80` -- The source endpoint retains its intended destination next hop.
- SERVICE: `show ip route 192.0.2.1` -- The service retains its explicit return route.
- TRANSIT: `show access-lists REQUEST-FAULT` -- Actual selected transit requests increment the deny counter.

## Transition: recover forward request admission

On **TRANSIT**:

```ios
configure terminal
interface Ethernet0/0
no ip access-group REQUEST-FAULT in
end
```

- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent endpoint request completes.
- SERVICE: `ping 192.0.2.1 source Loopback0 repeat 3` -- The reverse-originated echo exchange completes even when only forward echo requests are filtered.
- EDGE: `ping 198.18.12.2 repeat 3` -- All three probes succeed.
- TRANSIT: `ping 192.0.2.80 source Ethernet0/1 repeat 3` -- The final-hop router still reaches the service using its own connected return path.
- EDGE: `show ip route 192.0.2.80` -- The source endpoint retains its intended destination next hop.
- SERVICE: `show ip route 192.0.2.1` -- The service retains its explicit return route.

## Transition: replace the source forwarding decision

On **EDGE**:

```ios
configure terminal
no ip route 192.0.2.80 255.255.255.255 198.18.12.2
ip route 192.0.2.80 255.255.255.255 Null0
end
```

- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent endpoint request fails under the named controlled path fault.
- EDGE: `ping 198.18.12.2 repeat 3` -- All three probes succeed.
- TRANSIT: `ping 192.0.2.80 source Ethernet0/1 repeat 3` -- The final-hop router still reaches the service using its own connected return path.
- SERVICE: `show ip route 192.0.2.1` -- The service retains its explicit return route.
- EDGE: `show ip route 192.0.2.80` -- The actual installed service route is the deliberate local discard.

## Transition: recover the intended source next hop

On **EDGE**:

```ios
configure terminal
no ip route 192.0.2.80 255.255.255.255 Null0
ip route 192.0.2.80 255.255.255.255 198.18.12.2
end
```

- EDGE: `ping 192.0.2.80 source Loopback0 repeat 3` -- The independent endpoint request completes.
- SERVICE: `ping 192.0.2.1 source Loopback0 repeat 3` -- The reverse-originated echo exchange completes even when only forward echo requests are filtered.
- EDGE: `ping 198.18.12.2 repeat 3` -- All three probes succeed.
- TRANSIT: `ping 192.0.2.80 source Ethernet0/1 repeat 3` -- The final-hop router still reaches the service using its own connected return path.
- EDGE: `show ip route 192.0.2.80` -- The source endpoint retains its intended destination next hop.
- SERVICE: `show ip route 192.0.2.1` -- The service retains its explicit return route.

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
 ip address 198.18.12.1 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.80 255.255.255.255 198.18.12.2
end
```

### TRANSIT

```ios
hostname TRANSIT
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
ip route 192.0.2.1 255.255.255.255 198.18.12.1
ip route 192.0.2.80 255.255.255.255 198.18.23.2
ip access-list extended REQUEST-FAULT
 deny icmp host 192.0.2.1 host 192.0.2.80 echo
 permit ip any any
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
interface Ethernet0/0
 ip address 198.18.23.2 255.255.255.252
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.80 255.255.255.255
 no shutdown
 exit
ip route 192.0.2.1 255.255.255.255 198.18.23.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
