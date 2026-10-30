# IPsec GRE Design

## Scope and prerequisites

Two IOSv routers run point-to-point GRE protected by an IPsec transport-mode profile. The overlay is GRE/IP; the outside wire protocol is encrypted ESP. An outer ingress deny for GRE must leave the protected service operational and must not count clear GRE packets. Adding an earlier ESP deny must block the service and count actual ESP drops while IKE and peer-IP reachability remain healthy. Removing that ESP deny must restore traffic even while the GRE deny remains. This distinguishes encapsulation, encryption and ACL placement through actual probes and counters rather than tunnel-up state. Nominal RAM is1GiB. IKEv1 and the public exercise-only PSK are legacy interoperability fixtures, not production authentication guidance. All peers and prefixes are isolated. This verifies software protocol and packet behavior, not hardware cryptographic throughput.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 GigabitEthernet0/0 <-> R2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Tunnel0 | `ip address 172.16.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Tunnel0 | `ip address 172.16.0.2 255.255.255.252` |

## Tasks

1. Separate the actual GRE overlay from the outer ESP encryption transport.
2. Show that an outer GRE deny does not block encrypted GRE packets.
3. Add a selective ESP deny, identify actual packet drops and restore forwarding.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.0.2 repeat 3` | The unprotected peer transport remains reachable. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | The actual protected service loopback replies. |
| R1 | `show crypto isakmp sa` | The actual IKEv1 session reaches Quick Mode idle. |
| R1 | `show crypto ipsec sa | include #pkts|transform` | Both actual protected packet directions are nonzero with AES256/SHA256. |
| R2 | `show crypto ipsec sa | include #pkts|transform` | Both actual protected packet directions are nonzero with AES256/SHA256. |
| R1 | `show interfaces Tunnel0` | The live overlay is point-to-point GRE. |
| R1 | `show crypto ipsec sa` | The negotiated IPsec SA actually uses transport mode. |

## Transition: filter clear GRE on the receiving underlay

On **R2**:

```ios
configure terminal
ip access-list extended GRE-OUTER
10 deny gre any any
20 permit ip any any
exit
interface GigabitEthernet0/0
ip access-group GRE-OUTER in
end
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The actual protected service loopback replies.
- R1: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.
- R2: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.
- R2: `show access-lists GRE-OUTER` -- The clear-GRE filter exists but sees no encrypted payload.

## Transition: also filter the actual outer ESP protocol

On **R2**:

```ios
configure terminal
ip access-list extended GRE-OUTER
5 deny esp any any
end
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The controlled fault blocks the protected service.
- R1: `ping 198.18.0.2 repeat 3` -- The unprotected peer transport remains reachable.
- R1: `show crypto isakmp sa` -- The actual IKEv1 session reaches Quick Mode idle.
- R2: `show access-lists GRE-OUTER` -- The actual outer ESP packets hit the new deny.

## Transition: remove only the ESP deny

On **R2**:

```ios
configure terminal
ip access-list extended GRE-OUTER
no 5
end
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The actual protected service loopback replies.
- R1: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.
- R2: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.
- R2: `show access-lists GRE-OUTER` -- The GRE-only deny remains while protected traffic recovers.

## Transition: remove the exercise underlay filter

On **R2**:

```ios
configure terminal
interface GigabitEthernet0/0
no ip access-group GRE-OUTER in
end
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The actual protected service loopback replies.
- R1: `ping 198.18.0.2 repeat 3` -- The unprotected peer transport remains reachable.
- R1: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.
- R2: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.

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
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 3600
 exit
crypto isakmp key CML-VPN-DESIGN-PUBLIC-ONLY address 198.18.0.2
crypto ipsec transform-set DESIGN-SET esp-aes 256 esp-sha256-hmac
 mode transport
 exit
crypto ipsec profile DESIGN-PROFILE
 set transform-set DESIGN-SET
 set pfs group14
 exit
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
interface Tunnel0
 ip address 172.16.0.1 255.255.255.252
 ip mtu 1400
 tunnel source GigabitEthernet0/0
 tunnel destination 198.18.0.2
 tunnel mode gre ip
 tunnel protection ipsec profile DESIGN-PROFILE
 no shutdown
 exit
ip route 192.0.2.2 255.255.255.255 Tunnel0
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
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 3600
 exit
crypto isakmp key CML-VPN-DESIGN-PUBLIC-ONLY address 198.18.0.1
crypto ipsec transform-set DESIGN-SET esp-aes 256 esp-sha256-hmac
 mode transport
 exit
crypto ipsec profile DESIGN-PROFILE
 set transform-set DESIGN-SET
 set pfs group14
 exit
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Tunnel0
 ip address 172.16.0.2 255.255.255.252
 ip mtu 1400
 tunnel source GigabitEthernet0/0
 tunnel destination 198.18.0.1
 tunnel mode gre ip
 tunnel protection ipsec profile DESIGN-PROFILE
 no shutdown
 exit
ip route 192.0.2.1 255.255.255.255 Tunnel0
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
