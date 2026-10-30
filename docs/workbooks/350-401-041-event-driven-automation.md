# Event Driven Automation

## Scope and prerequisites

This exercise uses actual IOSv EEM, which is not available in IOL-XE. A LINEPROTO event for exactly Loopback10 opens an internal CLI session and restores that one interface; an independent router tests the actual data plane. Recovery can be faster than a polling interval, so successful event history and forwarding are paired with a removed-policy negative control rather than treating a configured string as proof. No external event bus, webhook receiver, AI model, n8n service or production interface is used. It demonstrates native device automation, not a cloud integration or hardware recovery timing.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 GigabitEthernet0/0 <-> R2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Loopback10 | `ip address 192.0.2.10 255.255.255.255` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Register a real IOSv EEM syslog policy targeting only the disposable Loopback10.
2. Shut the loopback and observe autonomous recovery and remote packet delivery.
3. Remove the policy as a negative control, prove the fault persists, then restore and trigger again.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show event manager policy registered` | The actual applet is registered. |
| R1 | `show ip interface brief` | The actual administrative and line state is up. |
| R2 | `ping 192.0.2.10 repeat 3` | The remote observer reaches the recovered loopback. |
| R2 | `ping 198.18.0.1 repeat 3` | The connected management/control path remains healthy. |

## Transition: trigger the first automatic recovery

On **R1**:

```ios
configure terminal
interface Loopback10
shutdown
end
```

- R1: `show ip interface brief` -- The actual administrative and line state is up.
- R1: `show event manager history events` -- The router records an actual applet invocation.
- R2: `ping 192.0.2.10 repeat 3` -- The remote observer reaches the recovered loopback.
- R2: `ping 198.18.0.1 repeat 3` -- The connected management/control path remains healthy.

## Transition: remove policy and repeat the fault

On **R1**:

```ios
configure terminal
no event manager applet RECOVER-LAB-LO10
interface Loopback10
shutdown
end
```

- R1: `show ip interface brief` -- Without the applet the deliberate fault persists.
- R2: `ping 192.0.2.10 repeat 3` -- The remote observer cannot reach the loopback while automation is absent.
- R2: `ping 198.18.0.1 repeat 3` -- The connected management/control path remains healthy.

## Transition: restore policy and prepare the interface

On **R1**:

```ios
configure terminal
event manager applet RECOVER-LAB-LO10
event syslog pattern "LINEPROTO-5-UPDOWN: Line protocol on Interface Loopback10, changed state to down"
action 1.0 cli command "enable"
action 2.0 cli command "configure terminal"
action 3.0 cli command "interface Loopback10"
action 4.0 cli command "no shutdown"
action 5.0 cli command "end"
action 6.0 syslog msg "CML-LO10-AUTO-RECOVERED"
exit
interface Loopback10
no shutdown
end
```

- R1: `show ip interface brief` -- The actual administrative and line state is up.
- R2: `ping 192.0.2.10 repeat 3` -- The remote observer reaches the recovered loopback.

## Transition: trigger automatic recovery again

On **R1**:

```ios
configure terminal
interface Loopback10
shutdown
end
```

- R1: `show ip interface brief` -- The actual administrative and line state is up.
- R1: `show event manager history events` -- The router records an actual applet invocation.
- R2: `ping 192.0.2.10 repeat 3` -- The remote observer reaches the recovered loopback.
- R2: `ping 198.18.0.1 repeat 3` -- The connected management/control path remains healthy.

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
no logging console
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
interface Loopback10
 ip address 192.0.2.10 255.255.255.255
 no shutdown
 exit
event manager applet RECOVER-LAB-LO10
event syslog pattern "LINEPROTO-5-UPDOWN: Line protocol on Interface Loopback10, changed state to down"
action 1.0 cli command "enable"
action 2.0 cli command "configure terminal"
action 3.0 cli command "interface Loopback10"
action 4.0 cli command "no shutdown"
action 5.0 cli command "end"
action 6.0 syslog msg "CML-LO10-AUTO-RECOVERED"
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
ip route 192.0.2.10 255.255.255.255 198.18.0.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
