# VPN Types: Policy IPsec and Routed VTI

## Scope and prerequisites

Four IOSv guests provide two genuinely separate site-to-site paths in one closed exercise. P1/P2 use a crypto map with exact service-loopback selectors on the physical underlay; their actual service route selects the peer next hop. V1/V2 use tunnel-mode-ipsec VTI with an IPsec profile and an actual service route through Tunnel0. The second pair has distinct underlay, tunnel and service prefixes. It does not share routes, bridges or connectors with the first pair. Both pairs must establish actual IKE and bidirectional nonzero ESP encapsulation/decapsulation counters using AES256/SHA256/DH14/PFS14; a configured string, tunnel-up state or a plain ping cannot pass alone.

First block only ESP on V2: VTI service packets must fail, the VTI peer underlay/IKE must remain healthy, its real ESP deny counter must increase, and the separate policy-based service must still work. Restore that filter and require protected data/counters again. Then apply the corresponding ESP-only fault to P2: its protected service must fail with healthy underlay/IKE and actual deny matches, while the independent VTI service stays usable. Restore the policy pair and recheck both actual routing/encapsulation models. This compares traffic selection and failure domains, rather than suggesting that one type is universally preferable.

Nominal RAM is 2048 MiB across four software routers. IKEv1 and the deliberately published classroom PSKs are legacy interoperability fixtures, not current production authentication recommendations. No remote-access client, NAT traversal, IKEv2, cloud gateway, external connector, hardware throughput or production-resilience claim is made. All mutations affect only the imported copy, and all credentials are public exercise fixtures. The existing peer/profile configurations and actual-counter probes are reused unchanged in meaning from the separately verified policy-IPsec and VTI exercises, with explicit label/prefix remapping for this new independent topology. This comparison still requires its own complete fresh functional proof.


Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- P1 GigabitEthernet0/0 <-> P2 GigabitEthernet0/0
- V1 GigabitEthernet0/0 <-> V2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| P1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| P1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| P2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| P2 | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| V1 | Loopback0 | `ip address 192.0.2.11 255.255.255.255` |
| V1 | GigabitEthernet0/0 | `ip address 198.18.1.1 255.255.255.252` |
| V1 | Tunnel0 | `ip address 172.16.1.1 255.255.255.252` |
| V2 | Loopback0 | `ip address 192.0.2.12 255.255.255.255` |
| V2 | GigabitEthernet0/0 | `ip address 198.18.1.2 255.255.255.252` |
| V2 | Tunnel0 | `ip address 172.16.1.2 255.255.255.252` |

## Tasks

1. Compare actual policy-selector IPsec and route-selected native VTI service paths.
2. Measure real IKE/ESP traffic and counters independently on both peer pairs.
3. Isolate an ESP-only failure to one pair, preserve the other pair and recover each protected path.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| P1 | `ping 198.18.0.2 repeat 3` | Unprotected peer-address reachability remains healthy. |
| P1 | `ping 192.0.2.2 source Loopback0 repeat 3` | All protected loopback packets receive replies after actual negotiation. |
| P1 | `show crypto isakmp sa` | The actual IKEv1 session completes Quick Mode. |
| P1 | `show crypto ipsec sa | include #pkts|transform` | Both actual packet counters are nonzero and the negotiated transform is AES256/SHA256. |
| P2 | `show crypto ipsec sa | include #pkts|transform` | Both actual packet counters are nonzero and the negotiated transform is AES256/SHA256. |
| P1 | `show ip route 192.0.2.2` | The actual policy-based service route selects the physical peer next hop. |
| P1 | `show crypto map` | The policy pair actually selects its crypto-map transform. |
| V1 | `ping 198.18.1.2 repeat 3` | The unprotected peer transport remains reachable. |
| V1 | `ping 192.0.2.12 source Loopback0 repeat 3` | The actual protected service loopback replies. |
| V1 | `show crypto isakmp sa` | The actual IKEv1 session reaches Quick Mode idle. |
| V1 | `show crypto ipsec sa | include #pkts|transform` | Both actual protected packet directions are nonzero with AES256/SHA256. |
| V2 | `show crypto ipsec sa | include #pkts|transform` | Both actual protected packet directions are nonzero with AES256/SHA256. |
| V1 | `show ip route 192.0.2.12` | The actual route-based service prefix selects the protected VTI. |
| V1 | `show interfaces Tunnel0` | The live routed tunnel uses native IPsec transport, rather than a GRE interface. |

## Transition: drop only VTI ESP while the policy pair remains usable

On **V2**:

```ios
configure terminal
ip access-list extended TYPES-ESP
deny esp any any
permit ip any any
exit
interface GigabitEthernet0/0
ip access-group TYPES-ESP in
end
```

- V1: `ping 192.0.2.12 source Loopback0 repeat 3` -- The controlled fault blocks the protected service.
- V1: `ping 198.18.1.2 repeat 3` -- The unprotected peer transport remains reachable.
- V1: `show crypto isakmp sa` -- The actual IKEv1 session reaches Quick Mode idle.
- V2: `show access-lists TYPES-ESP` -- Actual VTI ESP packets hit this receiving filter.
- P1: `ping 192.0.2.2 source Loopback0 repeat 3` -- All protected loopback packets receive replies after actual negotiation.

## Transition: restore only VTI encrypted forwarding

On **V2**:

```ios
configure terminal
interface GigabitEthernet0/0
no ip access-group TYPES-ESP in
end
```

- V1: `ping 192.0.2.12 source Loopback0 repeat 3` -- The actual protected service loopback replies.
- V1: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.
- V2: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.
- V1: `show ip route 192.0.2.12` -- The actual route-based service prefix selects the protected VTI.
- V1: `show interfaces Tunnel0` -- The live routed tunnel uses native IPsec transport, rather than a GRE interface.
- P1: `ping 192.0.2.2 source Loopback0 repeat 3` -- All protected loopback packets receive replies after actual negotiation.

## Transition: drop only policy ESP while the VTI pair remains usable

On **P2**:

```ios
configure terminal
ip access-list extended TYPES-ESP
deny esp any any
permit ip any any
exit
interface GigabitEthernet0/0
ip access-group TYPES-ESP in
end
```

- P1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Policy-selected payload is blocked rather than sent in plaintext.
- P1: `ping 198.18.0.2 repeat 3` -- Unprotected peer-address reachability remains healthy.
- P1: `show crypto isakmp sa` -- The actual IKEv1 session completes Quick Mode.
- P2: `show access-lists TYPES-ESP` -- Actual policy-protected ESP packets hit this receiving filter.
- V1: `ping 192.0.2.12 source Loopback0 repeat 3` -- The actual protected service loopback replies.

## Transition: restore both models and verify their distinct selected paths

On **P2**:

```ios
configure terminal
interface GigabitEthernet0/0
no ip access-group TYPES-ESP in
end
```

- P1: `ping 192.0.2.2 source Loopback0 repeat 3` -- All protected loopback packets receive replies after actual negotiation.
- P1: `show crypto ipsec sa | include #pkts|transform` -- Both actual packet counters are nonzero and the negotiated transform is AES256/SHA256.
- P2: `show crypto ipsec sa | include #pkts|transform` -- Both actual packet counters are nonzero and the negotiated transform is AES256/SHA256.
- P1: `show ip route 192.0.2.2` -- The actual policy-based service route selects the physical peer next hop.
- P1: `show crypto map` -- The policy pair actually selects its crypto-map transform.
- V1: `ping 192.0.2.12 source Loopback0 repeat 3` -- The actual protected service loopback replies.
- V1: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.
- V2: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.
- V1: `show ip route 192.0.2.12` -- The actual route-based service prefix selects the protected VTI.
- V1: `show interfaces Tunnel0` -- The live routed tunnel uses native IPsec transport, rather than a GRE interface.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### P1

```ios
hostname P1
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
crypto isakmp policy 10
 encr aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 3600
 exit
crypto isakmp key CML-LAB-PSK-only-984 address 198.18.0.2
crypto ipsec transform-set CML-ESP esp-aes 256 esp-sha256-hmac
 mode tunnel
 exit
ip access-list extended CML-PROTECTED
 permit ip host 192.0.2.1 host 192.0.2.2
 exit
crypto map CML-VPN 10 ipsec-isakmp
 set peer 198.18.0.2
 set transform-set CML-ESP
 set pfs group14
 match address CML-PROTECTED
 exit
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 crypto map CML-VPN
 exit
ip route 192.0.2.2 255.255.255.255 198.18.0.2
end
```

### P2

```ios
hostname P2
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
crypto isakmp policy 10
 encr aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 3600
 exit
crypto isakmp key CML-LAB-PSK-only-984 address 198.18.0.1
crypto ipsec transform-set CML-ESP esp-aes 256 esp-sha256-hmac
 mode tunnel
 exit
ip access-list extended CML-PROTECTED
 permit ip host 192.0.2.2 host 192.0.2.1
 exit
crypto map CML-VPN 10 ipsec-isakmp
 set peer 198.18.0.1
 set transform-set CML-ESP
 set pfs group14
 match address CML-PROTECTED
 exit
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 crypto map CML-VPN
 exit
ip route 192.0.2.1 255.255.255.255 198.18.0.1
end
```

### V1

```ios
hostname V1
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
crypto isakmp key CML-VPN-DESIGN-PUBLIC-ONLY address 198.18.1.2
crypto ipsec transform-set DESIGN-SET esp-aes 256 esp-sha256-hmac
 mode tunnel
 exit
crypto ipsec profile DESIGN-PROFILE
 set transform-set DESIGN-SET
 set pfs group14
 exit
interface Loopback0
 ip address 192.0.2.11 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
interface Tunnel0
 ip address 172.16.1.1 255.255.255.252
 ip mtu 1400
 tunnel source GigabitEthernet0/0
 tunnel destination 198.18.1.2
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile DESIGN-PROFILE
 no shutdown
 exit
ip route 192.0.2.12 255.255.255.255 Tunnel0
end
```

### V2

```ios
hostname V2
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
crypto isakmp key CML-VPN-DESIGN-PUBLIC-ONLY address 198.18.1.1
crypto ipsec transform-set DESIGN-SET esp-aes 256 esp-sha256-hmac
 mode tunnel
 exit
crypto ipsec profile DESIGN-PROFILE
 set transform-set DESIGN-SET
 set pfs group14
 exit
interface Loopback0
 ip address 192.0.2.12 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 exit
interface Tunnel0
 ip address 172.16.1.2 255.255.255.252
 ip mtu 1400
 tunnel source GigabitEthernet0/0
 tunnel destination 198.18.1.1
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile DESIGN-PROFILE
 no shutdown
 exit
ip route 192.0.2.11 255.255.255.255 Tunnel0
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
