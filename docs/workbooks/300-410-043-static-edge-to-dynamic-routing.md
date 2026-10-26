# Static Edge To Dynamic Routing

## Scope and prerequisites

Requires three IOL-XE nodes. The initial reference uses four explicit static routes, including transit return routes. OSPF point-to-point interface mode is prepared but the routing process is enabled only during the documented migration. The final state intentionally uses OSPF for both endpoints and the transit router. Reachability is sampled after each step; this is not a continuous-loss measurement or a zero-downtime guarantee. Stop/wipe the disposable copy to recover the original static baseline.

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

1. Verify a genuinely static forward and return path before migration.
2. Establish both OSPF adjacencies and the full LSDB while static routes still win.
3. Withdraw each explicit endpoint/transit static route only after the dynamic path is available.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip route 192.0.2.3` | The actual static route selects 198.18.12.2. |
| R3 | `show ip route 192.0.2.1` | The actual static route selects 198.18.23.1. |
| R1 | `ping 192.0.2.3 source Loopback0 repeat 3` | The sampled end-to-end traffic passes after this migration step. |

## Transition: enable OSPF on R1

On **R1**:

```ios
configure terminal
router ospf 1
router-id 192.0.2.1
network 198.18.12.0 0.0.0.3 area 0
network 192.0.2.1 0.0.0.0 area 0
exit
end
```

- R1: `show running-config | section router ospf` -- The first router is prepared; this alone does not prove an adjacency.

## Transition: enable OSPF on R2

On **R2**:

```ios
configure terminal
router ospf 1
router-id 192.0.2.2
network 198.18.12.0 0.0.0.3 area 0
network 198.18.23.0 0.0.0.3 area 0
network 192.0.2.2 0.0.0.0 area 0
exit
end
```

- R1: `show ip ospf neighbor` -- The first point-to-point adjacency is FULL.

## Transition: enable OSPF on R3

On **R3**:

```ios
configure terminal
router ospf 1
router-id 192.0.2.3
network 198.18.23.0 0.0.0.3 area 0
network 192.0.2.3 0.0.0.0 area 0
exit
end
```

- R2: `show ip ospf neighbor` -- The second point-to-point adjacency is FULL.
- R1: `show ip ospf database router 192.0.2.3` -- The complete topology is in the LSDB before static withdrawal.
- R1: `show ip route 192.0.2.3` -- The actual static route selects 198.18.12.2.
- R3: `show ip route 192.0.2.1` -- The actual static route selects 198.18.23.1.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The sampled end-to-end traffic passes after this migration step.

## Transition: migrate the first endpoint

On **R1**:

```ios
configure terminal
no ip route 192.0.2.3 255.255.255.255 198.18.12.2
end
```

- R1: `show ip route 192.0.2.3` -- The actual ospf 1 route selects 198.18.12.2.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The sampled end-to-end traffic passes after this migration step.

## Transition: migrate the return endpoint

On **R3**:

```ios
configure terminal
no ip route 192.0.2.1 255.255.255.255 198.18.23.1
end
```

- R3: `show ip route 192.0.2.1` -- The actual ospf 1 route selects 198.18.23.1.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The sampled end-to-end traffic passes after this migration step.

## Transition: migrate the transit router

On **R2**:

```ios
configure terminal
no ip route 192.0.2.1 255.255.255.255 198.18.12.1
no ip route 192.0.2.3 255.255.255.255 198.18.23.2
end
```

- R2: `show ip route 192.0.2.1` -- The actual ospf 1 route selects 198.18.12.1.
- R2: `show ip route 192.0.2.3` -- The actual ospf 1 route selects 198.18.23.2.
- R1: `ping 192.0.2.3 source Loopback0 repeat 3` -- The sampled end-to-end traffic passes after this migration step.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. This migration intentionally ends on dynamic routing; wiping and restarting the imported copy restores its static starting state. Repeat the applicable acceptance checks before ending the exercise.

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
 ip ospf network point-to-point
 exit
ip route 192.0.2.3 255.255.255.255 198.18.12.2
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
 ip ospf network point-to-point
 exit
interface Ethernet0/1
 ip address 198.18.23.1 255.255.255.252
 no shutdown
 ip ospf network point-to-point
 exit
ip route 192.0.2.1 255.255.255.255 198.18.12.1
ip route 192.0.2.3 255.255.255.255 198.18.23.2
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
 ip ospf network point-to-point
 exit
ip route 192.0.2.1 255.255.255.255 198.18.23.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
