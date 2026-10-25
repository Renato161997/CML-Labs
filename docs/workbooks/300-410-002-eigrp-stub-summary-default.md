# EIGRP Stub Summary Default

## Scope and prerequisites

Requires IOL-XE. R1 uses the default from CORE; STUB advertises a /25 summary covering its two endpoint networks. The automatic Null0 summary route prevents accidental forwarding loops for unused addresses in the aggregate.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> CORE Ethernet0/0
- CORE Ethernet0/1 <-> STUB Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.200 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| CORE | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| CORE | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| STUB | Ethernet0/0 | `ip address 198.18.1.2 255.255.255.252` |
| STUB | Loopback0 | `ip address 192.0.2.1 255.255.255.192` |
| STUB | Loopback1 | `ip address 192.0.2.65 255.255.255.192` |

## Tasks

1. Identify a stub peer and explain its query boundary.
2. Observe the /25 aggregate instead of the two endpoint /26s.
3. Use the default advertised to R1 and prove return routing.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CORE | `show ip eigrp neighbors detail` | The downstream peer advertises its stub capability. |
| CORE | `show ip route 192.0.2.65` | CORE selects the received aggregate. |
| R1 | `show ip route eigrp` | R1 receives a dynamic default. |
| R1 | `ping 192.0.2.65 source Loopback0 repeat 3` | The default, aggregate and return route all forward correctly. |

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
 ip address 192.0.2.200 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
router eigrp 100
 no auto-summary
 network 192.0.2.200 0.0.0.0
 network 198.18.0.0 0.0.0.3
 exit
end
```

### CORE

```ios
hostname CORE
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
 ip summary-address eigrp 100 0.0.0.0 0.0.0.0
 exit
interface Ethernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
router eigrp 100
 no auto-summary
 network 198.18.0.0 0.0.0.3
 network 198.18.1.0 0.0.0.3
 exit
end
```

### STUB

```ios
hostname STUB
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
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 ip summary-address eigrp 100 192.0.2.0 255.255.255.128
 exit
interface Loopback0
 ip address 192.0.2.1 255.255.255.192
 no shutdown
 exit
interface Loopback1
 ip address 192.0.2.65 255.255.255.192
 no shutdown
 exit
router eigrp 100
 no auto-summary
 network 198.18.1.0 0.0.0.3
 network 192.0.2.0 0.0.0.127
 eigrp stub connected summary
 exit
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
