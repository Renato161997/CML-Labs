# OSPF Troubleshooting

## Scope and prerequisites

Requires IOL-XE. This is an intentional area mismatch, not an image import error. R2 must join area 0 on both its endpoint and transit interface.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Deliberately broken: R2 advertises area 1 on the transit segment while R1 expects area 0. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Compare area IDs on the same broadcast segment.
2. Separate working Ethernet/IP from a rejected OSPF neighbor.
3. Repair the area and prove endpoint forwarding.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip ospf neighbor` | The repaired neighbor is FULL. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |

## Initial fault and repair

R2 advertises area 1 on the transit segment while R1 expects area 0.

Apply on R2:

```ios
configure terminal
interface Ethernet0/0
ip ospf 1 area 0
interface Loopback0
ip ospf 1 area 0
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
interface Loopback0
 ip ospf 1 area 0
 exit
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 ip ospf 1 area 0
 exit
router ospf 1
 router-id 192.0.2.1
 passive-interface Loopback0
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
interface Loopback0
 ip ospf 1 area 1
 exit
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 ip ospf 1 area 1
 exit
router ospf 1
 router-id 192.0.2.2
 passive-interface Loopback0
 exit
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
