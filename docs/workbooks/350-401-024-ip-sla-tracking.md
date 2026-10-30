# IP SLA Tracking

## Scope and prerequisites

Two isolated paths share a remote router. An ingress ACL selectively drops only the primary ICMP echo probe while leaving both Ethernet carriers and other traffic intact. This deliberately differs from a simple interface-shutdown test: IP SLA must detect a silent reachability failure, remove the tracked route and expose the floating route. Recovery removes the ACL attachment and proves both tracker and primary forwarding return. No throughput or independent-provider resilience is claimed.

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

1. Separate carrier state from measured service reachability.
2. Drop only primary SLA probes without shutting either link and verify tracked-route withdrawal.
3. Preserve payload forwarding on the floating path and restore primary preference.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show track 10` | The primary ICMP probe succeeds. |
| R1 | `show ip route 192.0.2.2` | The tracked primary next hop is installed. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Actual end-to-end payload forwarding survives the probe-only blackhole. |
| R1 | `show interfaces GigabitEthernet0/0` | The primary local carrier remains up; physical state cannot detect this fault. |

## Transition: blackhole the monitored service without losing carrier

On **R2**:

```ios
configure terminal
interface GigabitEthernet0/0
ip access-group DROP-SLA in
end
```

- R1: `show track 10` -- Probe reachability goes down while carrier remains up.
- R1: `show ip route 192.0.2.2` -- The floating route takes over.
- R1: `show interfaces GigabitEthernet0/0` -- The primary local carrier remains up; physical state cannot detect this fault.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Actual end-to-end payload forwarding survives the probe-only blackhole.
- R2: `show access-lists DROP-SLA` -- The intended rule counts actual dropped SLA probes.

## Transition: restore the primary service

On **R2**:

```ios
configure terminal
interface GigabitEthernet0/0
no ip access-group DROP-SLA in
end
```

- R1: `show track 10` -- The primary ICMP probe succeeds.
- R1: `show ip route 192.0.2.2` -- The tracked primary next hop is installed.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Actual end-to-end payload forwarding survives the probe-only blackhole.
- R1: `show interfaces GigabitEthernet0/0` -- The primary local carrier remains up; physical state cannot detect this fault.

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
interface GigabitEthernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
ip sla 10
 icmp-echo 198.18.0.2 source-interface GigabitEthernet0/0
 timeout 1000
 frequency 3
 exit
ip sla schedule 10 life forever start-time now
track 10 ip sla 10 reachability
 exit
ip route 192.0.2.2 255.255.255.255 198.18.0.2 track 10
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
no logging console
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
ip access-list extended DROP-SLA
 deny icmp host 198.18.0.1 host 198.18.0.2 echo
 permit ip any any
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
