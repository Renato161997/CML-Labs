# IPv6 Static Routing

## Scope and prerequisites

Documentation prefix 2001:db8::/32 is used exclusively. IPv6 forwarding must be enabled globally; successful interface addressing alone does not prove remote routing.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 GigabitEthernet0/0 <-> R2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ipv6 address 2001:db8:1::1/128` |
| R1 | GigabitEthernet0/0 | `ipv6 address 2001:db8:12::1/64` |
| R2 | Loopback0 | `ipv6 address 2001:db8:2::2/128` |
| R2 | GigabitEthernet0/0 | `ipv6 address 2001:db8:12::2/64` |

## Tasks

1. Inspect global and link-local addressing.
2. Explain the IPv6 forward and return static routes.
3. Verify end-to-end ICMPv6 from the source loopback.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ipv6 route static` | The remote /128 is installed as a static route. |
| R1 | `ping ipv6 2001:db8:2::2 source Loopback0 repeat 3` | The remote IPv6 loopback replies to all probes. |

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
!
ipv6 unicast-routing
!
interface Loopback0
 no ip address
 ipv6 enable
 ipv6 address 2001:db8:1::1/128
!
interface GigabitEthernet0/0
 no ip address
 ipv6 enable
 ipv6 address 2001:db8:12::1/64
 no shutdown
!
ipv6 route 2001:db8:2::2/128 2001:db8:12::2
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
!
ipv6 unicast-routing
!
interface Loopback0
 no ip address
 ipv6 enable
 ipv6 address 2001:db8:2::2/128
!
interface GigabitEthernet0/0
 no ip address
 ipv6 enable
 ipv6 address 2001:db8:12::2/64
 no shutdown
!
ipv6 route 2001:db8:1::1/128 2001:db8:12::1
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
