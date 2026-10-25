# IP SLA Tracking Static Route

## Scope and prerequisites

R1 tests the primary peer every three seconds and tracks the result. CML can leave the local virtual carrier up when the remote interface shuts; IP SLA detects this condition independently. The untracked return routes on R2 follow its own local interface state.

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

1. Distinguish local carrier state from end-to-end path health.
2. Fail the far-end primary interface and observe probe-driven route withdrawal.
3. Verify backup data-plane traffic and restore the primary.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show track 1` | The ICMP reachability track is up. |
| R1 | `show ip route 192.0.2.2` | Primary next hop is 198.18.0.2. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |

## Transition: remote failure detected

On **R2**:

```ios
configure terminal
interface GigabitEthernet0/0
shutdown
end
```

- R1: `show ip route 192.0.2.2` -- The floating route is installed with distance 200.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Three replies.

## Transition: remote primary restored

On **R2**:

```ios
configure terminal
interface GigabitEthernet0/0
no shutdown
end
```

- R1: `show track 1` -- The ICMP reachability track is up.
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
ip sla 1
 icmp-echo 198.18.0.2 source-interface GigabitEthernet0/0
 timeout 1000
 frequency 3
 exit
ip sla schedule 1 life forever start-time now
track 1 ip sla 1 reachability
 exit
ip route 192.0.2.2 255.255.255.255 198.18.0.2 track 1
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

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
