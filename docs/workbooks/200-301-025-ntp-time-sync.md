# NTP Time Sync

## Scope and prerequisites

Requires IOL-XE. This isolated reference deliberately trusts its local calendar, following the Cisco clock calendar-valid / ntp master example. It is not a claim of accurate external UTC. No Internet server is used. Each fresh device can need its own 15–20 minute frequency measurement (allow up to 40 minutes for this pair): wait for actual synchronized state instead of treating IP reachability or a low stratum as success. Polling is 16 seconds only for this exercise. During a source failure the clock can remain in holdover; the missing selected association is the failure evidence, not an assumption of immediate loss of synchronization. A server reply with leap indicator 3 is unsynchronized and must not be accepted merely because its stratum is low.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Distinguish a responding server from a trustworthy NTP reference.
2. Verify actual synchronization and selected peer.
3. Retarget the client to an unavailable peer, inspect the missing selected association, then restore the real reference.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.0.2 repeat 3` | The NTP transport network is reachable. |

## Transition: verify local calendar configuration

On **R2**:

```ios
configure terminal
clock calendar-valid
ntp master 3
end
```

- R2: `show ntp status` -- The isolated reference is selected.
- R1: `show ntp status` -- The client synchronizes through the lab reference.
- R1: `show ntp associations` -- The configured reference is selected.

## Transition: unavailable reference

On **R1**:

```ios
configure terminal
ntp server 198.18.1.254 version 4 maxpoll 4 minpoll 4
no ntp server 198.18.0.2
end
```

- R1: `show ntp associations` -- Only the unavailable peer is configured; no upstream is selected.

## Transition: restore reference

On **R1**:

```ios
configure terminal
ntp server 198.18.0.2 version 4 maxpoll 4 minpoll 4
no ntp server 198.18.1.254
end
```

- R1: `show ntp status` -- The client synchronizes through the lab reference.
- R1: `show ntp associations` -- The configured reference is selected.

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
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
ntp server 198.18.0.2 version 4 maxpoll 4 minpoll 4
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
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
clock calendar-valid
ntp master 3
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

Reference: [Cisco time and calendar configuration](https://www.cisco.com/c/en/us/td/docs/routers/ios-xe/system-management/system-management/m_bsm-time-calendar-set.html).
