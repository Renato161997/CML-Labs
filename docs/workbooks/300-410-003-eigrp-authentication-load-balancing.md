# EIGRP Authentication Load Balancing

## Scope and prerequisites

Requires IOL-XE named EIGRP. The public CML-LAB-ONLY string is intentionally a disposable exercise key, never a production credential. Both links use HMAC-SHA-256; a mismatch must remove only the affected adjacency.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R1 Ethernet0/1 <-> R2 Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Ethernet0/1 | `ip address 198.18.1.2 255.255.255.252` |

## Tasks

1. Verify two authenticated adjacencies and equal-cost next hops.
2. Introduce one incorrect lab-only HMAC key and observe that adjacency fail.
3. Keep forwarding on the healthy link, then restore both peers.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show ip eigrp neighbors` | Both authenticated peer links are established. |
| R1 | `show ip route 192.0.2.2` | Two equal-cost next hops are installed. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |

## Transition: wrong key on one peer

On **R2**:

```ios
configure terminal
router eigrp SECURE
address-family ipv4 unicast autonomous-system 100
af-interface Ethernet0/0
authentication mode hmac-sha-256 WRONG-LAB-KEY
end
```

- R1: `show ip eigrp neighbors` -- Only the other authenticated link remains.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Three replies.

## Transition: authentication restored

On **R2**:

```ios
configure terminal
router eigrp SECURE
address-family ipv4 unicast autonomous-system 100
af-interface Ethernet0/0
authentication mode hmac-sha-256 CML-LAB-ONLY
end
```

- R1: `show ip eigrp neighbors` -- Both authenticated peer links are established.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- Three replies.

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
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
router eigrp SECURE
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 192.0.2.1
  network 192.0.2.1 0.0.0.0
  network 198.18.0.0 0.0.0.3
  network 198.18.1.0 0.0.0.3
  af-interface Ethernet0/0
   authentication mode hmac-sha-256 CML-LAB-ONLY
  exit-af-interface
  af-interface Ethernet0/1
   authentication mode hmac-sha-256 CML-LAB-ONLY
  exit-af-interface
 exit-address-family
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
interface Ethernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.1.2 255.255.255.252
 no shutdown
 exit
router eigrp SECURE
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 192.0.2.2
  network 192.0.2.2 0.0.0.0
  network 198.18.0.0 0.0.0.3
  network 198.18.1.0 0.0.0.3
  af-interface Ethernet0/0
   authentication mode hmac-sha-256 CML-LAB-ONLY
  exit-af-interface
  af-interface Ethernet0/1
   authentication mode hmac-sha-256 CML-LAB-ONLY
  exit-af-interface
 exit-address-family
 exit
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
