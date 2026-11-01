# Control and Data Planes: Independent BGP and Encrypted GRE Paths

## Scope and prerequisites

Two real IOSv routers separate an underlay BGP control session from GRE-over-IPsec service forwarding. Each advertises only its service loopback; a documented inbound route-map sets the peer tunnel next hop. Actual BGP learned routes, CEF recursion to Tunnel0, bidirectional service replies and both IPsec counter directions are independent acceptance controls. There are no static/default service routes concealing loss of control information.

First block only ESP on R2. BGP and its learned service routes must remain healthy while service data fails and the exact ESP deny counter increments. Restore ESP and prove the data path recovers. Then administratively stop only R1's BGP neighbor. Both service routes must disappear and service traffic fail, while direct transport and actual encrypted tunnel-peer traffic remain healthy. Restore that neighbor and require fresh learned routes, CEF selection and service recovery.

This is a protocol-backed architectural analogy, not Cisco SD-WAN. No vManage, vSmart, vBond, OMP, proprietary TLOC policy, application-aware routing or controller compatibility is implemented or inferred. BGP carries training control information; GRE/IPsec carries selected service traffic. IKEv1 and the public exercise-only PSK are legacy interoperability fixtures, not production authentication guidance. All peers and prefixes are isolated. This verifies software protocol and packet behavior, not hardware cryptographic throughput.

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

1. Observe real control-session, learned-route, CEF and encrypted service-path evidence separately.
2. Break only encrypted forwarding while retaining control-plane state and identify actual ESP drops.
3. Withdraw only the control session while retaining transport/tunnel reachability, then recover the learned service path.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.0.2 repeat 3` | The direct control/transport address remains reachable independently of the service route. |
| R2 | `ping 198.18.0.1 repeat 3` | The direct control/transport address remains reachable independently of the service route. |
| R1 | `show ip bgp summary` | The actual independent underlay BGP session is established and receives the peer service prefix. |
| R2 | `show ip bgp summary` | The actual independent underlay BGP session is established and receives the peer service prefix. |
| R1 | `show ip route 192.0.2.2` | The service route was learned through BGP and selects the explicitly declared overlay next hop. |
| R2 | `show ip route 192.0.2.1` | The service route was learned through BGP and selects the explicitly declared overlay next hop. |
| R1 | `show ip cef 192.0.2.2` | Actual CEF recursion selects the encrypted GRE tunnel rather than a plaintext underlay path. |
| R2 | `show ip cef 192.0.2.1` | Actual CEF recursion selects the encrypted GRE tunnel rather than a plaintext underlay path. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | The remote service loopback responds through the actual learned overlay path. |
| R2 | `ping 192.0.2.1 source Loopback0 repeat 3` | The remote service loopback responds through the actual learned overlay path. |
| R1 | `show crypto isakmp sa` | The actual IKEv1 session reaches Quick Mode idle. |
| R1 | `show crypto ipsec sa | include #pkts|transform` | Both actual protected packet directions are nonzero with AES256/SHA256. |
| R2 | `show crypto ipsec sa | include #pkts|transform` | Both actual protected packet directions are nonzero with AES256/SHA256. |

## Transition: block only encrypted data while control remains up

On **R2**:

```ios
configure terminal
ip access-list extended CONTROL-DATA-ESP
deny esp any any
permit ip any any
exit
interface GigabitEthernet0/0
ip access-group CONTROL-DATA-ESP in
end
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The controlled fault blocks the protected service.
- R1: `ping 198.18.0.2 repeat 3` -- The direct control/transport address remains reachable independently of the service route.
- R2: `ping 198.18.0.1 repeat 3` -- The direct control/transport address remains reachable independently of the service route.
- R1: `show ip bgp summary` -- The actual independent underlay BGP session is established and receives the peer service prefix.
- R2: `show ip bgp summary` -- The actual independent underlay BGP session is established and receives the peer service prefix.
- R1: `show ip route 192.0.2.2` -- The service route was learned through BGP and selects the explicitly declared overlay next hop.
- R2: `show ip route 192.0.2.1` -- The service route was learned through BGP and selects the explicitly declared overlay next hop.
- R2: `show access-lists CONTROL-DATA-ESP` -- The actual encrypted-data deny counter increments while BGP remains established.

## Transition: restore the encrypted data plane

On **R2**:

```ios
configure terminal
interface GigabitEthernet0/0
no ip access-group CONTROL-DATA-ESP in
end
```

- R1: `ping 198.18.0.2 repeat 3` -- The direct control/transport address remains reachable independently of the service route.
- R2: `ping 198.18.0.1 repeat 3` -- The direct control/transport address remains reachable independently of the service route.
- R1: `show ip bgp summary` -- The actual independent underlay BGP session is established and receives the peer service prefix.
- R2: `show ip bgp summary` -- The actual independent underlay BGP session is established and receives the peer service prefix.
- R1: `show ip route 192.0.2.2` -- The service route was learned through BGP and selects the explicitly declared overlay next hop.
- R2: `show ip route 192.0.2.1` -- The service route was learned through BGP and selects the explicitly declared overlay next hop.
- R1: `show ip cef 192.0.2.2` -- Actual CEF recursion selects the encrypted GRE tunnel rather than a plaintext underlay path.
- R2: `show ip cef 192.0.2.1` -- Actual CEF recursion selects the encrypted GRE tunnel rather than a plaintext underlay path.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The remote service loopback responds through the actual learned overlay path.
- R2: `ping 192.0.2.1 source Loopback0 repeat 3` -- The remote service loopback responds through the actual learned overlay path.
- R1: `show crypto isakmp sa` -- The actual IKEv1 session reaches Quick Mode idle.
- R1: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.
- R2: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.

## Transition: withdraw only control information

On **R1**:

```ios
configure terminal
router bgp 65001
neighbor 198.18.0.2 shutdown
end
```

- R1: `show ip route 192.0.2.2` -- Actual loss of BGP information removes the service route, with no static/default fallback.
- R2: `show ip route 192.0.2.1` -- Actual loss of BGP information removes the service route, with no static/default fallback.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The controlled fault blocks the protected service.
- R1: `ping 198.18.0.2 repeat 3` -- The direct control/transport address remains reachable independently of the service route.
- R2: `ping 198.18.0.1 repeat 3` -- The direct control/transport address remains reachable independently of the service route.
- R1: `ping 172.16.0.2 source Tunnel0 repeat 3` -- Encrypted tunnel-peer reachability remains independently usable.
- R2: `ping 172.16.0.1 source Tunnel0 repeat 3` -- Encrypted tunnel-peer reachability remains independently usable.
- R1: `show crypto isakmp sa` -- The actual IKEv1 session reaches Quick Mode idle.

## Transition: restore control and service forwarding

On **R1**:

```ios
configure terminal
router bgp 65001
no neighbor 198.18.0.2 shutdown
end
```

- R1: `ping 198.18.0.2 repeat 3` -- The direct control/transport address remains reachable independently of the service route.
- R2: `ping 198.18.0.1 repeat 3` -- The direct control/transport address remains reachable independently of the service route.
- R1: `show ip bgp summary` -- The actual independent underlay BGP session is established and receives the peer service prefix.
- R2: `show ip bgp summary` -- The actual independent underlay BGP session is established and receives the peer service prefix.
- R1: `show ip route 192.0.2.2` -- The service route was learned through BGP and selects the explicitly declared overlay next hop.
- R2: `show ip route 192.0.2.1` -- The service route was learned through BGP and selects the explicitly declared overlay next hop.
- R1: `show ip cef 192.0.2.2` -- Actual CEF recursion selects the encrypted GRE tunnel rather than a plaintext underlay path.
- R2: `show ip cef 192.0.2.1` -- Actual CEF recursion selects the encrypted GRE tunnel rather than a plaintext underlay path.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The remote service loopback responds through the actual learned overlay path.
- R2: `ping 192.0.2.1 source Loopback0 repeat 3` -- The remote service loopback responds through the actual learned overlay path.
- R1: `show crypto isakmp sa` -- The actual IKEv1 session reaches Quick Mode idle.
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
route-map OVERLAY-IN permit 10
 set ip next-hop 172.16.0.2
 exit
router bgp 65001
 bgp router-id 192.0.2.1
 bgp log-neighbor-changes
 timers bgp 3 9
 neighbor 198.18.0.2 remote-as 65002
 neighbor 198.18.0.2 advertisement-interval 0
 neighbor 198.18.0.2 route-map OVERLAY-IN in
 network 192.0.2.1 mask 255.255.255.255
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
route-map OVERLAY-IN permit 10
 set ip next-hop 172.16.0.1
 exit
router bgp 65002
 bgp router-id 192.0.2.2
 bgp log-neighbor-changes
 timers bgp 3 9
 neighbor 198.18.0.1 remote-as 65001
 neighbor 198.18.0.1 advertisement-interval 0
 neighbor 198.18.0.1 route-map OVERLAY-IN in
 network 192.0.2.2 mask 255.255.255.255
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
