# Routing Table Selection

## Scope and prerequisites

R2 and R3 deliberately advertise the same educational loopback on separate routed links. The duplicate /32 represents alternative destinations for the forwarding exercise; it is not a duplicate host address on one Ethernet segment.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 GigabitEthernet0/0 <-> R2 GigabitEthernet0/0
- R1 GigabitEthernet0/1 <-> R3 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | GigabitEthernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.100 255.255.255.255` |
| R2 | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R3 | Loopback0 | `ip address 192.0.2.100 255.255.255.255` |
| R3 | GigabitEthernet0/0 | `ip address 198.18.1.2 255.255.255.252` |

## Tasks

1. Distinguish prefix-length selection from administrative distance.
2. Withdraw the more-specific /32 and inspect the resulting next hop.
3. Restore the /32 without changing the covering aggregate.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip route 192.0.2.100` | The /32 through R3 wins longest-prefix matching. |
| R1 | `ping 192.0.2.100 source Loopback0 repeat 3` | Three replies. |

## Transition: withdraw specific

On **R1**:

```ios
configure terminal
no ip route 192.0.2.100 255.255.255.255 198.18.1.2
end
```

- R1: `show ip route 192.0.2.100` -- After withdrawing the /32, the /24 through R2 is selected.
- R1: `ping 192.0.2.100 source Loopback0 repeat 3` -- Three replies.

## Transition: restore specific

On **R1**:

```ios
configure terminal
ip route 192.0.2.100 255.255.255.255 198.18.1.2
end
```

- R1: `show ip route 192.0.2.100` -- The /32 through R3 wins longest-prefix matching.

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
ip route 192.0.2.0 255.255.255.0 198.18.0.2
ip route 192.0.2.100 255.255.255.255 198.18.1.2
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
 ip address 192.0.2.100 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.1 255.255.255.255 198.18.0.1
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
interface Loopback0
 ip address 192.0.2.100 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.1 255.255.255.255 198.18.1.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
