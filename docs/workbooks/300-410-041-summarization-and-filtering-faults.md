# Summarization And Filtering Faults

## Scope and prerequisites

Requires three IOL-XE nodes. R2 is the area 0/10 ABR and summarizes two real /32 loopbacks into 192.0.2.0/24. The unused .99 address is deliberately not an endpoint; its covering route does not imply reachability. The filter fault uses the explicit area-range not-advertise flag, suppressing the aggregate and its components outside area 10. The test checks route withdrawal and packet loss separately from adjacency health, then restores advertisement.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R2 Ethernet0/1 <-> R3 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 203.0.113.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.12.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 203.0.113.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.12.2 255.255.255.252` |
| R2 | Ethernet0/1 | `ip address 198.18.23.1 255.255.255.252` |
| R3 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R3 | Loopback1 | `ip address 192.0.2.2 255.255.255.255` |
| R3 | Ethernet0/0 | `ip address 198.18.23.2 255.255.255.252` |

## Tasks

1. Verify an ABR aggregate and both real component endpoints.
2. Explain the summary discard route and why an unused covered address is not a live endpoint.
3. Suppress and restore the range advertisement while verifying that both OSPF adjacencies remain healthy.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip ospf neighbor` | The backbone adjacency is FULL. |
| R2 | `show ip ospf neighbor` | The component-area adjacency is FULL. |
| R1 | `show ip route 192.0.2.1` | R1 selects the actual /24 aggregate, not an individual host route. |
| R1 | `ping 192.0.2.1 source Loopback0 repeat 3` | The documented component responds. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | The documented component responds. |
| R2 | `show ip route 192.0.2.99` | The ABR has a discard route for the covering aggregate. |
| R1 | `ping 192.0.2.99 source Loopback0 repeat 3` | The documented component is unreachable. |

## Transition: suppress the component range

On **R2**:

```ios
configure terminal
router ospf 1
area 10 range 192.0.2.0 255.255.255.0 not-advertise
end
```

- R1: `show ip route 192.0.2.1` -- The suppressed component range is absent from the backbone RIB.
- R1: `show ip ospf neighbor` -- The backbone adjacency is FULL.
- R2: `show ip ospf neighbor` -- The component-area adjacency is FULL.
- R1: `ping 192.0.2.1 source Loopback0 repeat 3` -- The documented component is unreachable.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The documented component is unreachable.

## Transition: restore range advertisement

On **R2**:

```ios
configure terminal
router ospf 1
area 10 range 192.0.2.0 255.255.255.0 advertise
end
```

- R1: `show ip route 192.0.2.1` -- R1 selects the actual /24 aggregate, not an individual host route.
- R1: `ping 192.0.2.1 source Loopback0 repeat 3` -- The documented component responds.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The documented component responds.

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
 ip address 203.0.113.1 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.12.1 255.255.255.252
 no shutdown
 exit
router ospf 1
 router-id 203.0.113.1
 network 198.18.12.0 0.0.0.3 area 0
 network 203.0.113.1 0.0.0.0 area 0
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
 ip address 203.0.113.2 255.255.255.255
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
router ospf 1
 router-id 203.0.113.2
 network 198.18.12.0 0.0.0.3 area 0
 network 198.18.23.0 0.0.0.3 area 10
 network 203.0.113.2 0.0.0.0 area 0
 area 10 range 192.0.2.0 255.255.255.0 advertise
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
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface Loopback1
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.23.2 255.255.255.252
 no shutdown
 exit
router ospf 1
 router-id 203.0.113.3
 network 198.18.23.0 0.0.0.3 area 10
 network 192.0.2.0 0.0.0.3 area 10
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

[Cisco OSPF range reference](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/iproute_ospf/command/iro-cr-book/m_ospf-a1.html). The workbook uses IPv4 ranges; actual image output and data-plane observations determine the recorded pass.
