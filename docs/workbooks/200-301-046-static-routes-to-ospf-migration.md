# Static Routes To OSPF Migration

## Scope and prerequisites

Both control planes initially coexist: administrative distance 1 makes the static route win over OSPF distance 110. Removing a static route should reveal the already converged dynamic path, not require building routing during an outage.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 GigabitEthernet0/0 <-> R2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Verify OSPF convergence before withdrawing preferred static routes.
2. Migrate each direction independently while checking reachability.
3. Perform a tested rollback to the original static preference.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip ospf neighbor` | The OSPF adjacency is already established. |
| R1 | `show ip route 192.0.2.2` | Primary next hop is 198.18.0.2. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |

## Transition: migrate R1

On **R1**:

```ios
configure terminal
no ip route 192.0.2.2 255.255.255.255 198.18.0.2
end
```

- R1: `show ip route 192.0.2.2` -- OSPF supplies the installed route after the static is removed.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Three replies.

## Transition: migrate return route

On **R2**:

```ios
configure terminal
no ip route 192.0.2.1 255.255.255.255 198.18.0.1
end
```

- R2: `show ip route 192.0.2.1` -- The return route is also learned through OSPF.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Three replies.

## Transition: rollback return route

On **R2**:

```ios
configure terminal
ip route 192.0.2.1 255.255.255.255 198.18.0.1
end
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Three replies.

## Transition: rollback R1

On **R1**:

```ios
configure terminal
ip route 192.0.2.2 255.255.255.255 198.18.0.2
end
```

- R1: `show ip route 192.0.2.2` -- Primary next hop is 198.18.0.2.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Three replies.

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
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.2 255.255.255.255 198.18.0.2
router ospf 1
 router-id 192.0.2.1
 passive-interface Loopback0
 network 198.18.0.0 0.0.0.3 area 0
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
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.1 255.255.255.255 198.18.0.1
router ospf 1
 router-id 192.0.2.2
 passive-interface Loopback0
 network 198.18.0.0 0.0.0.3 area 0
 network 192.0.2.2 0.0.0.0 area 0
 exit
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
