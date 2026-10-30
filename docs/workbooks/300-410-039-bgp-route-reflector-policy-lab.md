# BGP Route Reflector Policy Lab

## Scope and prerequisites

Four IOL-XE routers implement two iBGP clients, a real route reflector and an external service AS. OSPF supplies only transport between loopbacks. LEAF1 sets next-hop-self toward RR for the external service; RR preserves the originating client and adds its cluster ID. LEAF2 has no direct LEAF1 BGP session. Its probe-loopback prefix is reflected back to LEAF1 and exported to REMOTE, providing an actual learned return path. Removing both reflector-client roles turns RR into ordinary non-transit iBGP: established sessions and healthy underlay must remain, but the remote client service must disappear. Removing only one client flag would not prove this fault, because client-to-nonclient reflection is allowed. A separate LEAF2 import filter tests per-client policy without changing RR service availability. All faults are removed. Nominal RAM is4GiB.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- RR Ethernet0/0 <-> LEAF1 Ethernet0/0
- RR Ethernet0/1 <-> LEAF2 Ethernet0/0
- LEAF1 Ethernet0/1 <-> REMOTE Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| RR | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| RR | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| RR | Ethernet0/1 | `ip address 198.18.0.5 255.255.255.252` |
| LEAF1 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| LEAF1 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| LEAF1 | Ethernet0/1 | `ip address 198.18.0.9 255.255.255.252` |
| LEAF2 | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| LEAF2 | Ethernet0/0 | `ip address 198.18.0.6 255.255.255.252` |
| REMOTE | Ethernet0/0 | `ip address 198.18.0.10 255.255.255.252` |
| REMOTE | Loopback0 | `ip address 203.0.113.9 255.255.255.255` |

## Tasks

1. Verify actual reflected originator/cluster attributes without an iBGP full mesh.
2. Remove both client roles and distinguish iBGP transit rules from healthy transport and sessions.
3. Apply a client-local import filter, prove its selective effect and recover the route.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| LEAF2 | `show ip bgp 203.0.113.9` | The service has actual reflected originator and cluster attributes. |
| LEAF2 | `show ip bgp neighbors 192.0.2.1` | The reflector session is genuinely established. |
| LEAF2 | `ping 203.0.113.9 source Loopback0 repeat 3` | The reflected service and advertised return prefix support actual traffic. |
| REMOTE | `show ip route 192.0.2.3` | The return prefix is actually learned through eBGP. |

## Transition: remove both reflection client roles

On **RR**:

```ios
configure terminal
router bgp 65000
no neighbor 192.0.2.2 route-reflector-client
no neighbor 192.0.2.3 route-reflector-client
exit
do clear ip bgp * soft out
end
```

- LEAF2: `show ip bgp neighbors 192.0.2.1` -- The reflector session is genuinely established.
- LEAF2: `show ip route 203.0.113.9` -- The client service route is actually withdrawn.
- LEAF2: `ping 192.0.2.2 source Loopback0 repeat 3` -- OSPF transport to the originating client remains healthy.
- RR: `show ip bgp 203.0.113.9` -- The reflector still has the service from its originating peer.

## Transition: restore the reflector clients

On **RR**:

```ios
configure terminal
router bgp 65000
neighbor 192.0.2.2 route-reflector-client
neighbor 192.0.2.3 route-reflector-client
exit
do clear ip bgp * soft out
end
```

- LEAF2: `show ip bgp 203.0.113.9` -- The service has actual reflected originator and cluster attributes.
- LEAF2: `ping 203.0.113.9 source Loopback0 repeat 3` -- The reflected service and advertised return prefix support actual traffic.

## Transition: filter the service on only one client

On **LEAF2**:

```ios
configure terminal
ip prefix-list SERVICE seq 10 permit 203.0.113.9/32
route-map CLIENT-IN deny 10
match ip address prefix-list SERVICE
exit
route-map CLIENT-IN permit 20
exit
router bgp 65000
neighbor 192.0.2.1 route-map CLIENT-IN in
exit
do clear ip bgp 192.0.2.1 soft in
end
```

- LEAF2: `show ip route 203.0.113.9` -- The client service route is actually withdrawn.
- LEAF2: `show ip bgp neighbors 192.0.2.1` -- The reflector session is genuinely established.
- RR: `show ip bgp 203.0.113.9` -- The reflector still has the service from its originating peer.
- LEAF2: `ping 192.0.2.2 source Loopback0 repeat 3` -- OSPF transport to the originating client remains healthy.

## Transition: remove the client-local import fault

On **LEAF2**:

```ios
configure terminal
router bgp 65000
no neighbor 192.0.2.1 route-map CLIENT-IN in
exit
do clear ip bgp 192.0.2.1 soft in
end
```

- LEAF2: `show ip bgp 203.0.113.9` -- The service has actual reflected originator and cluster attributes.
- LEAF2: `ping 203.0.113.9 source Loopback0 repeat 3` -- The reflected service and advertised return prefix support actual traffic.
- LEAF2: `show ip bgp neighbors 192.0.2.1` -- The reflector session is genuinely established.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### RR

```ios
hostname RR
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
router ospf 10
 router-id 192.0.2.1
 passive-interface Loopback0
 exit
interface Loopback0
 ip ospf 10 area 0
 exit
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
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
router bgp 65000
 bgp router-id 192.0.2.1
 bgp cluster-id 192.0.2.1
 neighbor 192.0.2.2 remote-as 65000
 neighbor 192.0.2.2 update-source Loopback0
 neighbor 192.0.2.2 route-reflector-client
 neighbor 192.0.2.3 remote-as 65000
 neighbor 192.0.2.3 update-source Loopback0
 neighbor 192.0.2.3 route-reflector-client
 exit
end
```

### LEAF1

```ios
hostname LEAF1
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
router ospf 10
 router-id 192.0.2.2
 passive-interface Loopback0
 exit
interface Loopback0
 ip ospf 10 area 0
 exit
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 exit
interface Ethernet0/1
 ip address 198.18.0.9 255.255.255.252
 no shutdown
 exit
router bgp 65000
 bgp router-id 192.0.2.2
 neighbor 192.0.2.1 remote-as 65000
 neighbor 192.0.2.1 update-source Loopback0
 neighbor 192.0.2.1 next-hop-self
 neighbor 192.0.2.1 soft-reconfiguration inbound
 neighbor 198.18.0.10 remote-as 65100
 exit
end
```

### LEAF2

```ios
hostname LEAF2
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
router ospf 10
 router-id 192.0.2.3
 passive-interface Loopback0
 exit
interface Loopback0
 ip ospf 10 area 0
 exit
interface Ethernet0/0
 ip address 198.18.0.6 255.255.255.252
 no shutdown
 ip ospf 10 area 0
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 exit
router bgp 65000
 bgp router-id 192.0.2.3
 neighbor 192.0.2.1 remote-as 65000
 neighbor 192.0.2.1 update-source Loopback0
 neighbor 192.0.2.1 next-hop-self
 neighbor 192.0.2.1 soft-reconfiguration inbound
 network 192.0.2.3 mask 255.255.255.255
 exit
end
```

### REMOTE

```ios
hostname REMOTE
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
 ip address 198.18.0.10 255.255.255.252
 no shutdown
 exit
interface Loopback0
 ip address 203.0.113.9 255.255.255.255
 no shutdown
 exit
router bgp 65100
 bgp router-id 203.0.113.9
 neighbor 198.18.0.9 remote-as 65000
 network 203.0.113.9 mask 255.255.255.255
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
