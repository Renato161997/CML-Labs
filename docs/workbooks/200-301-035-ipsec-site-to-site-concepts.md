# IPsec Site To Site Concepts

## Scope and prerequisites

Two IOSv guests exchange actual IKEv1/IPsec ESP tunnel traffic between isolated loopbacks. Both peers must report nonzero protected encapsulation and decapsulation counters; configured crypto strings and a plaintext ping alone cannot pass. AES256, SHA256 and DH14/PFS14 are explicit interoperability settings. IKEv1 and the published training PSK are legacy educational fixtures, not production authentication recommendations. No NAT, public endpoint, external connector or real credential is involved. IOSv is software/performance limited; throughput, hardware offload and production resilience are not claimed. Cisco lists IPsec among IOSv features: https://developer.cisco.com/docs/modeling-labs/iosv/ . Only your disposable imported copy may be stopped/wiped.

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

1. Distinguish underlay reachability, IKE establishment and protected data-plane forwarding.
2. Generate actual interesting traffic and inspect both peers encryption/decapsulation counters.
3. For the security exercise, block only ESP while IKE/underlay remain healthy, then recover.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.0.2 repeat 3` | Unprotected peer-address reachability remains healthy. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | All protected loopback packets receive replies after actual negotiation. |
| R1 | `show crypto isakmp sa` | The actual IKEv1 session completes Quick Mode. |
| R1 | `show crypto ipsec sa | include #pkts|transform` | Both actual packet counters are nonzero and the negotiated transform is AES256/SHA256. |
| R2 | `show crypto ipsec sa | include #pkts|transform` | Both actual packet counters are nonzero and the negotiated transform is AES256/SHA256. |

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
