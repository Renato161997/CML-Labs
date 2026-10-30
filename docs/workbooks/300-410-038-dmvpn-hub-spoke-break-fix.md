# DMVPN Hub Spoke Break Fix

## Scope and prerequisites

Three IOSv routers share an isolated Layer2 benchmark-address underlay. The hub and both spokes use mGRE, NHRP and AES256/SHA256 IPsec transport protection with PFS14. Phase2 disables hub EIGRP next-hop-self so spokes learn direct overlay next hops. Phase3 retains the hub next hop, advertises a /24 summary and uses actual NHRP redirect/shortcut processing to install a more-specific path. Direct-peer NHRP and IPsec packet counters are checked separately from hub registration and routed pings. IKEv1 and the PUBLIC CML-DMVPN-PUBLIC-ONLY / CMLONLY strings are disposable legacy interoperability fixtures, never production credentials or a production security recommendation. MTU/MSS are conservative lab settings; scale, throughput and Internet NAT traversal are outside scope. Nominal RAM is 3x512+768 MiB. SPOKE-B starts with only its NHRP authentication intentionally wrong; IPsec and underlay configuration are otherwise correct.

Use licensed reference images for iosv, iosvl2 in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Deliberately broken: SPOKE-B uses the wrong NHRP authentication string. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- HUB GigabitEthernet0/0 <-> UNDERLAY GigabitEthernet0/0
- SPOKE-A GigabitEthernet0/0 <-> UNDERLAY GigabitEthernet0/1
- SPOKE-B GigabitEthernet0/0 <-> UNDERLAY GigabitEthernet0/2

| Node | Interface | Address |
| --- | --- | --- |
| HUB | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| HUB | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.0` |
| HUB | Tunnel0 | `ip address 172.16.0.1 255.255.255.0` |
| SPOKE-A | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| SPOKE-A | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.0` |
| SPOKE-A | Tunnel0 | `ip address 172.16.0.2 255.255.255.0` |
| SPOKE-B | Loopback0 | `ip address 192.0.2.3 255.255.255.255` |
| SPOKE-B | GigabitEthernet0/0 | `ip address 198.18.0.3 255.255.255.0` |
| SPOKE-B | Tunnel0 | `ip address 172.16.0.3 255.255.255.0` |

## Tasks

1. Register real NHRP mappings over mGRE protected with actual IPsec.
2. Verify the distinct Phase2 next-hop or Phase3 aggregate/shortcut behavior with real spoke-to-spoke traffic.
3. Isolate the intended authentication or ESP forwarding fault while preserving the healthy underlay, then recover.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| SPOKE-A | `ping 192.0.2.3 source Loopback0 repeat 3` | Actual customer traffic crosses the encrypted spoke path. |
| HUB | `show ip nhrp` | Both spokes actually register their overlay/NBMA mapping. |
| SPOKE-A | `show ip route 192.0.2.3` | Phase2 preserves the remote spoke as the EIGRP next hop. |
| SPOKE-A | `show ip nhrp 172.16.0.3` | The actual remote-spoke mapping is dynamically resolved. |
| SPOKE-A | `show crypto ipsec sa peer 198.18.0.3 | include #pkts|transform` | The direct spoke peer has actual encrypted and decrypted packets with AES256/SHA256. |

## Initial fault and repair

SPOKE-B uses the wrong NHRP authentication string.

Apply on SPOKE-B:

```ios
configure terminal
interface Tunnel0
ip nhrp authentication CMLONLY
end
```

Run baseline acceptance after the repair.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### HUB

```ios
hostname HUB
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.1 255.255.255.0
 no shutdown
 exit
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 3600
 exit
crypto isakmp key CML-DMVPN-PUBLIC-ONLY address 0.0.0.0 0.0.0.0
crypto ipsec transform-set DMVPN-SET esp-aes 256 esp-sha256-hmac
 mode transport
 exit
crypto ipsec profile DMVPN-PROFILE
 set transform-set DMVPN-SET
 set pfs group14
 exit
interface Tunnel0
 ip address 172.16.0.1 255.255.255.0
 ip mtu 1400
 ip tcp adjust-mss 1360
 no ip redirects
 ip nhrp authentication CMLONLY
 ip nhrp network-id 100
 ip nhrp holdtime 180
 ip nhrp map multicast dynamic
 no ip split-horizon eigrp 100
 no ip next-hop-self eigrp 100
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile DMVPN-PROFILE
 no shutdown
 exit
router eigrp 100
 no auto-summary
 network 172.16.0.0 0.0.0.255
 network 192.0.2.1 0.0.0.0
 passive-interface Loopback0
 exit
end
```

### SPOKE-A

```ios
hostname SPOKE-A
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.2 255.255.255.0
 no shutdown
 exit
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 3600
 exit
crypto isakmp key CML-DMVPN-PUBLIC-ONLY address 0.0.0.0 0.0.0.0
crypto ipsec transform-set DMVPN-SET esp-aes 256 esp-sha256-hmac
 mode transport
 exit
crypto ipsec profile DMVPN-PROFILE
 set transform-set DMVPN-SET
 set pfs group14
 exit
interface Tunnel0
 ip address 172.16.0.2 255.255.255.0
 ip mtu 1400
 ip tcp adjust-mss 1360
 no ip redirects
 ip nhrp authentication CMLONLY
 ip nhrp network-id 100
 ip nhrp holdtime 180
 ip nhrp map 172.16.0.1 198.18.0.1
 ip nhrp map multicast 198.18.0.1
 ip nhrp nhs 172.16.0.1
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile DMVPN-PROFILE
 no shutdown
 exit
router eigrp 100
 no auto-summary
 network 172.16.0.0 0.0.0.255
 network 192.0.2.2 0.0.0.0
 passive-interface Loopback0
 exit
end
```

### SPOKE-B

```ios
hostname SPOKE-B
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
interface Loopback0
 ip address 192.0.2.3 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.3 255.255.255.0
 no shutdown
 exit
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 3600
 exit
crypto isakmp key CML-DMVPN-PUBLIC-ONLY address 0.0.0.0 0.0.0.0
crypto ipsec transform-set DMVPN-SET esp-aes 256 esp-sha256-hmac
 mode transport
 exit
crypto ipsec profile DMVPN-PROFILE
 set transform-set DMVPN-SET
 set pfs group14
 exit
interface Tunnel0
 ip address 172.16.0.3 255.255.255.0
 ip mtu 1400
 ip tcp adjust-mss 1360
 no ip redirects
 ip nhrp authentication WRONG
 ip nhrp network-id 100
 ip nhrp holdtime 180
 ip nhrp map 172.16.0.1 198.18.0.1
 ip nhrp map multicast 198.18.0.1
 ip nhrp nhs 172.16.0.1
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile DMVPN-PROFILE
 no shutdown
 exit
router eigrp 100
 no auto-summary
 network 172.16.0.0 0.0.0.255
 network 192.0.2.3 0.0.0.0
 passive-interface Loopback0
 exit
ip access-list extended BLOCK-DIRECT-ESP
 deny esp host 198.18.0.2 host 198.18.0.3
 permit ip any any
 exit
end
```

### UNDERLAY

```ios
hostname UNDERLAY
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
vtp mode transparent
spanning-tree mode rapid-pvst
interface GigabitEthernet0/0
 switchport mode access
 spanning-tree portfast
 no shutdown
 exit
interface GigabitEthernet0/1
 switchport mode access
 spanning-tree portfast
 no shutdown
 exit
interface GigabitEthernet0/2
 switchport mode access
 spanning-tree portfast
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

See [Cisco DMVPN troubleshooting and phase behavior](https://www.cisco.com/c/en/us/support/docs/security/dynamic-multipoint-vpn-dmvpn/111976-dmvpn-troubleshoot-00.html) and [NHRP shortcut switching](https://www.cisco.com/c/en/us/td/docs/routers/ios-xe/ip-addressing/ip-addressing/m_nhrp-switch-enhancemts-dmvpn-0.html). Image support is established by this case live evidence.
