# Floating Static Routes

## Scope and prerequisites

Two isolated routed links connect the same routers. The backup has administrative distance 200. CML virtual links do not reliably propagate a remote administrative shutdown as local carrier loss: shutting only R1 can leave the R2 return route on a black hole. The test first observes that asymmetric failure, then disables both ends to model a bidirectional link failure.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 GigabitEthernet0/0 <-> R2 GigabitEthernet0/0
- R1 GigabitEthernet0/1 <-> R2 GigabitEthernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | GigabitEthernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | GigabitEthernet0/1 | `ip address 198.18.1.2 255.255.255.252` |

## Tasks

1. Compare administrative distance with prefix length.
2. Fail the primary interface and verify the floating route actually forwards traffic.
3. Restore the interface and observe the preferred route return.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip route 192.0.2.2` | Primary next hop is 198.18.0.2. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |

## Transition: local primary failure

On **R1**:

```ios
configure terminal
interface GigabitEthernet0/0
shutdown
end
```

- R1: `show ip route 192.0.2.2` -- The floating route is installed with distance 200.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- All three probes fail while the route is removed.

## Transition: remote primary failure

On **R2**:

```ios
configure terminal
interface GigabitEthernet0/0
shutdown
end
```

- R1: `show ip route 192.0.2.2` -- The floating route is installed with distance 200.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Three replies.

## Transition: remote primary recovery

On **R2**:

```ios
configure terminal
interface GigabitEthernet0/0
no shutdown
end
```

- R2: `show ip interface brief` -- The remote primary interface is restored.

## Transition: local primary recovery

On **R1**:

```ios
configure terminal
interface GigabitEthernet0/0
no shutdown
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
interface GigabitEthernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.2 255.255.255.255 198.18.0.2
ip route 192.0.2.2 255.255.255.255 198.18.1.2 200
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
interface GigabitEthernet0/1
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.1 255.255.255.255 198.18.0.1
ip route 192.0.2.1 255.255.255.255 198.18.1.1 200
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
