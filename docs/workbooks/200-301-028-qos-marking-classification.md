# QoS Marking Classification

## Scope and prerequisites

Requires IOL-XE with software MQC marking support. The receiver ACL distinguishes EF-marked traffic from other IP packets. Clearing only its named test counters avoids mistaking earlier matches for fresh evidence. This verifies classification/marking, not hardware queuing, policing accuracy or throughput.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Classify ICMP and apply an egress DSCP policy.
2. Verify the resulting marking at the receiver, not just the configured action.
3. Remove and restore the policy with fresh counters between observations.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.0.2 repeat 3` | The test flow forwards. |
| R2 | `show access-lists OBSERVE-DSCP` | The receiving ACL observes actual EF-marked requests. |

## Transition: remove egress marking

On **R1**:

```ios
configure terminal
interface Ethernet0/0
no service-policy output MARK-EF
end
```

- R1: `show running-config interface Ethernet0/0` -- The egress policy is detached.

## Transition: observe unmarked requests

On **R2**:

```ios
clear access-list counters OBSERVE-DSCP
```

- R1: `ping 198.18.0.2 repeat 3` -- The test flow forwards.
- R2: `show access-lists OBSERVE-DSCP` -- Unmarked requests reach the fallback ACL entry.

## Transition: restore egress marking

On **R1**:

```ios
configure terminal
interface Ethernet0/0
service-policy output MARK-EF
end
```

- R1: `show policy-map interface Ethernet0/0` -- The policy is attached again.

## Transition: observe restored marking

On **R2**:

```ios
clear access-list counters OBSERVE-DSCP
```

- R1: `ping 198.18.0.2 repeat 3` -- The test flow forwards.
- R2: `show access-lists OBSERVE-DSCP` -- The receiving ACL observes actual EF-marked requests.

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
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
ip access-list extended CLASSIFY-ICMP
 permit icmp any any
 exit
class-map match-all ICMP
 match access-group name CLASSIFY-ICMP
 exit
policy-map MARK-EF
 class ICMP
  set dscp ef
 exit
 exit
interface Ethernet0/0
 service-policy output MARK-EF
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
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
ip access-list extended OBSERVE-DSCP
 permit icmp any any dscp ef
 permit ip any any
 exit
interface Ethernet0/0
 ip access-group OBSERVE-DSCP in
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
