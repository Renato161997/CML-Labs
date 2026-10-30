# Suspicious Host Containment

## Scope and prerequisites

Three IOL-XE routers implement a host, enforcement gateway and internal service. The incident signal is a stated training decision, not an EDR detection claim. An ingress source-IP containment ACL permits only the selected host remediation probe before denying its remaining traffic; unrelated sources retain normal policy. A counter and real negative service probe must identify enforcement while remediation and the service-side gateway remain healthy. An early permit intentionally bypasses containment, then its removal must restore the deny. Finally the ACL is detached and service traffic recovers. This is source-IP policy, not device identity, endpoint posture, stateful firewalling or automatic SOC integration. Nominal RAM is3GiB.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- HOST Ethernet0/0 <-> GW Ethernet0/0
- GW Ethernet0/1 <-> SERVICE Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| HOST | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |
| GW | Ethernet0/0 | `ip address 198.18.10.1 255.255.255.0` |
| GW | Ethernet0/1 | `ip address 198.18.20.1 255.255.255.0` |
| GW | Loopback0 | `ip address 192.0.2.80 255.255.255.255` |
| SERVICE | Ethernet0/0 | `ip address 198.18.20.101 255.255.255.0` |

## Tasks

1. Separate a simulated incident decision from actual network containment enforcement.
2. Block the selected source while preserving its remediation path and unrelated service connectivity.
3. Expose an incorrectly ordered permit, repair it and roll back containment.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| HOST | `ping 198.18.20.101 source Ethernet0/0 repeat 3` | The actual endpoint probe succeeds. |
| HOST | `ping 192.0.2.80 source Ethernet0/0 repeat 3` | The actual endpoint probe succeeds. |
| SERVICE | `ping 198.18.20.1 source Ethernet0/0 repeat 3` | The actual endpoint probe succeeds. |

## Transition: apply the selected host containment

On **GW**:

```ios
configure terminal
interface Ethernet0/0
ip access-group CONTAIN-HOST in
end
```

- HOST: `ping 198.18.20.101 source Ethernet0/0 repeat 3` -- The actual endpoint probe is blocked during the controlled fault.
- GW: `show access-lists CONTAIN-HOST` -- The containment rule counts actual blocked host traffic.
- HOST: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.
- SERVICE: `ping 198.18.20.1 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.

## Transition: introduce an incorrectly ordered exception

On **GW**:

```ios
configure terminal
ip access-list extended CONTAIN-HOST
5 permit ip host 198.18.10.10 any
end
```

- HOST: `ping 198.18.20.101 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.
- GW: `show access-lists CONTAIN-HOST` -- The early permit actually bypasses the lower deny.

## Transition: repair containment rule ordering

On **GW**:

```ios
configure terminal
ip access-list extended CONTAIN-HOST
no 5
end
```

- HOST: `ping 198.18.20.101 source Ethernet0/0 repeat 3` -- The actual endpoint probe is blocked during the controlled fault.
- GW: `show access-lists CONTAIN-HOST` -- The containment rule counts actual blocked host traffic.
- HOST: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.

## Transition: release the host after the exercise decision

On **GW**:

```ios
configure terminal
interface Ethernet0/0
no ip access-group CONTAIN-HOST in
end
```

- HOST: `ping 198.18.20.101 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.
- HOST: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.
- SERVICE: `ping 198.18.20.1 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### HOST

```ios
hostname HOST
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
 ip address 198.18.10.10 255.255.255.0
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.10.1
end
```

### GW

```ios
hostname GW
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
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.20.1 255.255.255.0
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.80 255.255.255.255
 no shutdown
 exit
ip access-list extended CONTAIN-HOST
 10 permit icmp host 198.18.10.10 host 192.0.2.80
 20 deny ip host 198.18.10.10 any
 30 permit ip any any
 exit
end
```

### SERVICE

```ios
hostname SERVICE
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
 ip address 198.18.20.101 255.255.255.0
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.20.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
