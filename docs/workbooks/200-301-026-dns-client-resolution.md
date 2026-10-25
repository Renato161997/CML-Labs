# DNS Client Resolution

## Scope and prerequisites

R2 supplies a static DNS A record for the reserved example.test namespace. R1 has no local host entry, so the hostname test requires the lab DNS service. No public resolver is contacted.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 GigabitEthernet0/0 <-> R2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Loopback1 | `ip address 192.0.2.100 255.255.255.255` |

## Tasks

1. Resolve the reserved example.test name using only the lab DNS server.
2. Inspect the client host cache after a real lookup.
3. Distinguish DNS resolution from subsequent IP reachability.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping app.example.test repeat 3` | A name lookup and ICMP probes reach the server loopback. |
| R1 | `show hosts` | The name is present in the client cache. |

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
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
ip domain lookup
ip name-server 198.18.0.2
ip route 192.0.2.100 255.255.255.255 198.18.0.2
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
ip dns server
ip host app.example.test 192.0.2.100
interface Loopback1
 ip address 192.0.2.100 255.255.255.255
 no shutdown
 exit
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
