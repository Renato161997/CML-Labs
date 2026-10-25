# DHCP Server And Relay

## Scope and prerequisites

A router is used as a DHCP client so the console can inspect the lease without an external desktop. The server must route replies to the client subnet; the relay uses giaddr to select the USERS pool.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- CLIENT GigabitEthernet0/0 <-> RELAY GigabitEthernet0/0
- RELAY GigabitEthernet0/1 <-> SERVER GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| CLIENT | GigabitEthernet0/0 | `ip address dhcp` |
| RELAY | GigabitEthernet0/0 | `ip address 198.18.10.1 255.255.255.0` |
| RELAY | GigabitEthernet0/1 | `ip address 198.18.0.1 255.255.255.252` |
| SERVER | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Follow a broadcast request across a routed relay.
2. Verify the client obtains a dynamic address and default route.
3. Inspect the lease on the server and prove routed reachability.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `show ip interface brief` | The client interface holds a DHCP lease. |
| SERVER | `show ip dhcp binding` | The server records a client binding. |
| CLIENT | `ping 198.18.0.2 repeat 3` | The leased client reaches the DHCP server through the relay. |

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### CLIENT

```ios
hostname CLIENT
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
interface GigabitEthernet0/0
 ip address dhcp
 no shutdown
 exit
end
```

### RELAY

```ios
hostname RELAY
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
interface GigabitEthernet0/0
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 ip helper-address 198.18.0.2
 exit
interface GigabitEthernet0/1
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
end
```

### SERVER

```ios
hostname SERVER
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
ip route 198.18.10.0 255.255.255.0 198.18.0.1
ip dhcp excluded-address 198.18.10.1 198.18.10.9
ip dhcp pool USERS
 network 198.18.10.0 255.255.255.0
 default-router 198.18.10.1
 exit
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
