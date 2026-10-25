# IPv4 Subnetting And VLSM

## Scope and prerequisites

Two loopback networks model differently sized endpoint subnets; the routers are joined by a /30 transit. The unused addresses are intentional. Correct subnet arithmetic and a return route are both necessary.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 GigabitEthernet0/0 <-> R2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.192` |
| R1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.65 255.255.255.224` |
| R2 | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Calculate network, host range and broadcast for the /26, /27 and /30.
2. Verify the actual installed masks rather than inferring them from addresses.
3. Trace the forward and return route between differently sized prefixes.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip route connected` | The /26 endpoint network is connected. |
| R2 | `show ip route connected` | The /27 endpoint network is connected. |
| R1 | `ping 192.0.2.65 source Loopback0 repeat 3` | Three replies. |

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
 ip address 192.0.2.1 255.255.255.192
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.64 255.255.255.224 198.18.0.2
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
 ip address 192.0.2.65 255.255.255.224
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
ip route 192.0.2.0 255.255.255.192 198.18.0.1
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
