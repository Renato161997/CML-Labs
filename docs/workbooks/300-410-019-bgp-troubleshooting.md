# BGP Troubleshooting

## Scope and prerequisites

Requires IOL-XE. This startup deliberately gives R1 the wrong peer AS (65099 rather than 65002). R2 and R3 are otherwise functional, allowing a narrow one-line repair.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Deliberately broken: The R1-to-R2 peer identity is incorrect; the BGP session cannot establish. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R2 Ethernet0/1 <-> R3 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| R3 | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| R3 | Ethernet0/0 | `ip address 198.18.1.2 255.255.255.252` |

## Tasks

1. Verify direct IP transport before diagnosing BGP.
2. Find the incorrect remote-AS setting without changing the peer router.
3. Repair the peer identity and prove the full transit route.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip bgp summary` | The corrected session is established and receives prefixes. |
| R1 | `show ip bgp 192.0.2.3` | The advertised route has the expected two-AS path. |
| R1 | `ping 192.0.2.3 source Loopback0 repeat 3` | Three replies. |

## Initial fault and repair

The R1-to-R2 peer identity is incorrect; the BGP session cannot establish.

Apply on R1:

```ios
configure terminal
router bgp 65001
neighbor 198.18.0.2 remote-as 65002
end
```

Run baseline acceptance after the repair.

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
ip bgp-community new-format
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
router bgp 65001
 bgp router-id 192.0.2.1
 network 192.0.2.1 mask 255.255.255.255
 neighbor 198.18.0.2 remote-as 65099
 neighbor 198.18.0.2 advertisement-interval 0
 neighbor 198.18.0.2 send-community
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
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
ip bgp-community new-format
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
router bgp 65002
 bgp router-id 192.0.2.2
 network 192.0.2.2 mask 255.255.255.255
 neighbor 198.18.0.1 remote-as 65001
 neighbor 198.18.0.1 advertisement-interval 0
 neighbor 198.18.0.1 send-community
 neighbor 198.18.1.2 remote-as 65003
 neighbor 198.18.1.2 advertisement-interval 0
 neighbor 198.18.1.2 send-community
 exit
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
interface range Ethernet0/0 - 3
 no ip address
 shutdown
 exit
interface Loopback0
 ip address 192.0.2.3 255.255.255.255
 no shutdown
 exit
ip bgp-community new-format
interface Ethernet0/0
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 exit
router bgp 65003
 bgp router-id 192.0.2.3
 network 192.0.2.3 mask 255.255.255.255
 neighbor 198.18.1.1 remote-as 65002
 neighbor 198.18.1.1 advertisement-interval 0
 neighbor 198.18.1.1 send-community
 exit
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
