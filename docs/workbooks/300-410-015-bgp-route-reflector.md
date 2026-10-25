# BGP Route Reflector

## Scope and prerequisites

Requires IOL-XE. OSPF point-to-point links carry only transport addresses. Endpoint prefixes 203.0.113.1/32 and .3/32 depend on iBGP reflection, so an IGP route cannot make the acceptance ping pass. Allow the default BGP connection retry to finish. Remove BOTH client roles: client-learned routes can still be reflected to a nonclient, so removing only the receiving client role would not test suppression between two nonclients.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R2 Ethernet0/1 <-> R3 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Loopback1 | `ip address 203.0.113.1 255.255.255.255` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| R3 | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| R3 | Ethernet0/0 | `ip address 198.18.1.2 255.255.255.252` |
| R3 | Loopback1 | `ip address 203.0.113.3 255.255.255.255` |

## Tasks

1. Explain why clients do not need a full iBGP mesh.
2. Inspect originator and cluster-list attributes on an actual reflected route.
3. Withdraw and restore the client role and observe the route/data-plane effect.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R2 | `show ip bgp summary` | The iBGP session receives the remote endpoint prefix. |
| R2 | `show ip bgp summary` | The iBGP session receives the remote endpoint prefix. |
| R3 | `show ip bgp 203.0.113.1` | The route carries originator and reflector cluster attributes. |
| R3 | `ping 203.0.113.1 source Loopback1 repeat 3` | The reflected routes provide forward and return reachability. |

## Transition: remove both client roles

On **R2**:

```ios
configure terminal
router bgp 65000
no neighbor 192.0.2.1 route-reflector-client
no neighbor 192.0.2.3 route-reflector-client
do clear ip bgp 192.0.2.1 soft out
do clear ip bgp 192.0.2.3 soft out
end
```

- R2: `show ip bgp summary` -- The iBGP session receives the remote endpoint prefix.
- R2: `show ip bgp summary` -- The iBGP session receives the remote endpoint prefix.
- R3: `show ip route 203.0.113.1` -- The non-reflected endpoint route is withdrawn with both sessions still established.

## Transition: restore client roles

On **R2**:

```ios
configure terminal
router bgp 65000
neighbor 192.0.2.1 route-reflector-client
neighbor 192.0.2.3 route-reflector-client
do clear ip bgp 192.0.2.1 soft out
do clear ip bgp 192.0.2.3 soft out
end
```

- R2: `show ip bgp summary` -- The iBGP session receives the remote endpoint prefix.
- R2: `show ip bgp summary` -- The iBGP session receives the remote endpoint prefix.
- R3: `show ip bgp 203.0.113.1` -- The route carries originator and reflector cluster attributes.
- R3: `ping 203.0.113.1 source Loopback1 repeat 3` -- The reflected routes provide forward and return reachability.

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
router ospf 1
 router-id 192.0.2.1
 network 192.0.2.1 0.0.0.0 area 0
 network 198.18.0.0 0.0.0.3 area 0
 network 198.18.1.0 0.0.0.3 area 0
 exit
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 ip ospf network point-to-point
 exit
interface Loopback1
 ip address 203.0.113.1 255.255.255.255
 no shutdown
 exit
router bgp 65000
 bgp router-id 192.0.2.1
 bgp log-neighbor-changes
 neighbor 192.0.2.2 remote-as 65000
 neighbor 192.0.2.2 update-source Loopback0
 network 203.0.113.1 mask 255.255.255.255
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
router ospf 1
 router-id 192.0.2.2
 network 192.0.2.2 0.0.0.0 area 0
 network 198.18.0.0 0.0.0.3 area 0
 network 198.18.1.0 0.0.0.3 area 0
 exit
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 ip ospf network point-to-point
 exit
interface Ethernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 ip ospf network point-to-point
 exit
router bgp 65000
 bgp router-id 192.0.2.2
 bgp log-neighbor-changes
 neighbor 192.0.2.1 remote-as 65000
 neighbor 192.0.2.1 update-source Loopback0
 neighbor 192.0.2.1 route-reflector-client
 neighbor 192.0.2.3 remote-as 65000
 neighbor 192.0.2.3 update-source Loopback0
 neighbor 192.0.2.3 route-reflector-client
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
router ospf 1
 router-id 192.0.2.3
 network 192.0.2.3 0.0.0.0 area 0
 network 198.18.0.0 0.0.0.3 area 0
 network 198.18.1.0 0.0.0.3 area 0
 exit
interface Ethernet0/0
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 ip ospf network point-to-point
 exit
interface Loopback1
 ip address 203.0.113.3 255.255.255.255
 no shutdown
 exit
router bgp 65000
 bgp router-id 192.0.2.3
 bgp log-neighbor-changes
 neighbor 192.0.2.2 remote-as 65000
 neighbor 192.0.2.2 update-source Loopback0
 network 203.0.113.3 mask 255.255.255.255
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
