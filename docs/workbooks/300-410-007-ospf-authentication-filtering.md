# OSPF Authentication Filtering

## Scope and prerequisites

Requires three IOL-XE nodes. CML-OSPF-LAB is a PUBLIC disposable MD5 exercise key, not a secret or a current production cryptography recommendation. Both ends of the authenticated link use matching 2-second hello and 8-second dead timers. A distribute-list filters local RIB installation, not the OSPF link-state database; the exercise explicitly shows the resulting transit black hole even while R1 retains the advertised destination. No external connector is present.

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

1. Verify an authenticated adjacency and real end-to-end forwarding.
2. Mismatch and restore the public exercise-only MD5 key, observing adjacency-dependent route withdrawal.
3. Apply a local OSPF RIB filter and distinguish unchanged LSA propagation from failed transit forwarding.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip ospf neighbor` | The authenticated R1-R2 adjacency is FULL. |
| R2 | `show ip ospf neighbor` | The second transit adjacency is FULL before checking remote routes. |
| R1 | `show ip route 192.0.2.3` | R1 learns the destination through OSPF and R2. |
| R1 | `ping 192.0.2.3 source Loopback0 repeat 3` | Traffic between the remote loopbacks actually forwards. |
| R1 | `show ip ospf interface Ethernet0/0` | Cryptographic authentication reports the intended key ID. |

## Transition: incorrect authenticated-link key

On **R2**:

```ios
configure terminal
interface Ethernet0/0
ip ospf message-digest-key 1 md5 INCORRECT-LAB
end
```

- R1: `show ip route 192.0.2.3` -- The destination prefix is absent from this RIB.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The withdrawn route cannot forward.
- R2: `show ip ospf neighbor` -- The separate unauthenticated R2-R3 adjacency remains FULL.

## Transition: restore matching link key

On **R2**:

```ios
configure terminal
interface Ethernet0/0
ip ospf message-digest-key 1 md5 CML-OSPF-LAB
end
```

- R1: `show ip ospf neighbor` -- The authenticated R1-R2 adjacency is FULL.
- R1: `show ip route 192.0.2.3` -- R1 learns the destination through OSPF and R2.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- Traffic between the remote loopbacks actually forwards.

## Transition: filter only the transit router RIB

On **R2**:

```ios
configure terminal
ip prefix-list RIBFILTER seq 5 deny 192.0.2.3/32
ip prefix-list RIBFILTER seq 10 permit 0.0.0.0/0 le 32
router ospf 1
distribute-list prefix RIBFILTER in
end
```

- R2: `show ip route 192.0.2.3` -- The destination prefix is absent from this RIB.
- R2: `show ip ospf database router 192.0.2.3` -- R3 remains in the actual link-state database.
- R1: `show ip route 192.0.2.3` -- R1 learns the destination through OSPF and R2.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- An advertised route alone does not guarantee transit forwarding.

## Transition: restore transit route installation

On **R2**:

```ios
configure terminal
router ospf 1
no distribute-list prefix RIBFILTER in
end
```

- R2: `show ip route 192.0.2.3` -- The transit RIB again installs the remote loopback.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- Traffic between the remote loopbacks actually forwards.

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
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 CML-OSPF-LAB
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 exit
router ospf 1
 router-id 192.0.2.1
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
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 CML-OSPF-LAB
 ip ospf hello-interval 2
 ip ospf dead-interval 8
 exit
interface Ethernet0/1
 ip address 198.18.23.1 255.255.255.252
 no shutdown
 exit
router ospf 1
 router-id 192.0.2.2
 network 198.18.12.0 0.0.0.3 area 0
 network 198.18.23.0 0.0.0.3 area 0
 network 192.0.2.2 0.0.0.0 area 0
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
router ospf 1
 router-id 192.0.2.3
 network 198.18.23.0 0.0.0.3 area 0
 network 192.0.2.3 0.0.0.0 area 0
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

[Cisco protocol reference](https://www.cisco.com/c/en/us/support/docs/ip/open-shortest-path-first-ospf/7112-26.pdf). Actual support and executed checks are recorded in the live results.
