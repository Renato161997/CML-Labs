# Site To Site VPN Security Baseline

## Scope and prerequisites

Two IOSv routers use a policy-based IPsec crypto map with exact service-loopback selectors and explicit AES256/SHA256/DH14/PFS14. The negative fixture switches only R2 to a different AES128 transform and clears old IKE/IPsec SAs on both peers so an earlier working SA cannot conceal the incompatibility. The protected probe must fail while the peer-IP underlay remains reachable. Recovery selects the original transform, clears incompatible state on both peers and requires actual IKE completion plus fresh nonzero encapsulation/decapsulation counters on both peers. The AES128 proposal is a deliberate incompatible training fault, not a suggested downgrade. Nominal RAM is1GiB. IKEv1 and the public exercise-only PSK are legacy interoperability fixtures, not production authentication guidance. All peers and prefixes are isolated. This verifies software protocol and packet behavior, not hardware cryptographic throughput.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 GigabitEthernet0/0 <-> R2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Record actual IKE/IPsec establishment, negotiated AES256/SHA256 and nonzero bidirectional counters.
2. Replace one peer proposal with an incompatible transform and remove its old SAs.
3. Require fail-closed protected traffic with healthy underlay, then recover a fresh matching SA.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.0.2 repeat 3` | The unprotected peer transport remains reachable. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | The actual protected service loopback replies. |
| R1 | `show crypto isakmp sa` | The actual IKEv1 session reaches Quick Mode idle. |
| R1 | `show crypto ipsec sa | include #pkts|transform` | Both actual protected packet directions are nonzero with AES256/SHA256. |
| R2 | `show crypto ipsec sa | include #pkts|transform` | Both actual protected packet directions are nonzero with AES256/SHA256. |

## Transition: replace one peer with an incompatible proposal

On **R2**:

```ios
configure terminal
crypto ipsec transform-set INCOMPATIBLE esp-aes esp-sha256-hmac
mode tunnel
exit
crypto map CML-VPN 10 ipsec-isakmp
set transform-set INCOMPATIBLE
exit
do clear crypto isakmp
do clear crypto sa
end
```

- R2: `show crypto map` -- The receiving peer actually selects the incompatible transform.
- R1: `ping 198.18.0.2 repeat 3` -- The unprotected peer transport remains reachable.

## Transition: clear the initiating peer before the negative negotiation

On **R1**:

```ios
clear crypto isakmp
clear crypto sa
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The controlled fault blocks the protected service.
- R1: `ping 198.18.0.2 repeat 3` -- The unprotected peer transport remains reachable.

## Transition: restore the required proposal on the receiver

On **R2**:

```ios
configure terminal
crypto map CML-VPN 10 ipsec-isakmp
set transform-set CML-ESP
exit
do clear crypto isakmp
do clear crypto sa
end
```

- R2: `show crypto map` -- The receiving peer again requires the original transform.
- R1: `ping 198.18.0.2 repeat 3` -- The unprotected peer transport remains reachable.

## Transition: clear the initiating peer and prove fresh recovery

On **R1**:

```ios
clear crypto isakmp
clear crypto sa
```

- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- The actual protected service loopback replies.
- R1: `show crypto isakmp sa` -- The actual IKEv1 session reaches Quick Mode idle.
- R1: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.
- R2: `show crypto ipsec sa | include #pkts|transform` -- Both actual protected packet directions are nonzero with AES256/SHA256.
- R1: `ping 198.18.0.2 repeat 3` -- The unprotected peer transport remains reachable.

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

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
