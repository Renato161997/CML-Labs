# PBR With IP SLA Fallback

## Scope and prerequisites

Requires three IOL-XE nodes. R1 tracks ICMP reachability of the policy next hop using its secondary interface. The fault inserts a narrow receiver ACL entry that denies only those SLA echo requests; client traffic remains permitted. This intentionally models failure of the monitoring signal, not a powered-off peer or a physical cable failure. Fresh receiver counters prove the resulting policy fallback and recovery while the static RIB remains unchanged. The named observer ACLs stay applied throughout.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0
- R1 Ethernet0/1 <-> R2 Ethernet0/1
- CLIENT Ethernet0/0 <-> R1 Ethernet0/2

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| R1 | Ethernet0/2 | `ip address 198.18.10.1 255.255.255.0` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Ethernet0/1 | `ip address 198.18.1.2 255.255.255.252` |
| CLIENT | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |

## Tasks

1. Verify SLA-controlled PBR and the independently measured receiver ingress path.
2. Block only SLA echo probes without changing virtual Ethernet carrier or the ordinary RIB.
3. Observe actual fallback to the normal path, then restore tracked PBR and measure recovery.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show track 1` | The actual SLA reachability object is Up. |
| CLIENT | `ping 192.0.2.2 repeat 3` | The client flow reaches the real remote loopback. |
| R1 | `show ip route 192.0.2.2` | The ordinary RIB still selects the primary next hop. |

## Transition: observe healthy tracked policy

On **R2**:

```ios
clear access-list counters OBSERVE-PRIMARY
clear access-list counters OBSERVE-POLICY
```

- CLIENT: `ping 192.0.2.2 repeat 3` -- The client flow reaches the real remote loopback.
- R2: `show access-lists OBSERVE-POLICY` -- Fresh matching requests are observed on OBSERVE-POLICY.
- R2: `show access-lists OBSERVE-PRIMARY` -- No matching request is observed on OBSERVE-PRIMARY.
- R1: `show ip route 192.0.2.2` -- The ordinary RIB still selects the primary next hop.

## Transition: deny only SLA probes

On **R2**:

```ios
configure terminal
ip access-list extended OBSERVE-POLICY
5 deny icmp host 198.18.1.1 host 198.18.1.2 echo
end
```

- R1: `show track 1` -- The actual SLA reachability object is Down.

## Transition: observe tracked next-hop fallback

On **R2**:

```ios
clear access-list counters OBSERVE-PRIMARY
clear access-list counters OBSERVE-POLICY
```

- CLIENT: `ping 192.0.2.2 repeat 3` -- The client flow reaches the real remote loopback.
- R2: `show access-lists OBSERVE-POLICY` -- No matching request is observed on OBSERVE-POLICY.
- R2: `show access-lists OBSERVE-PRIMARY` -- Fresh matching requests are observed on OBSERVE-PRIMARY.
- R1: `show ip route 192.0.2.2` -- The ordinary RIB still selects the primary next hop.

## Transition: restore SLA probes

On **R2**:

```ios
configure terminal
ip access-list extended OBSERVE-POLICY
no 5
end
```

- R1: `show track 1` -- The actual SLA reachability object is Up.

## Transition: observe policy recovery

On **R2**:

```ios
clear access-list counters OBSERVE-PRIMARY
clear access-list counters OBSERVE-POLICY
```

- CLIENT: `ping 192.0.2.2 repeat 3` -- The client flow reaches the real remote loopback.
- R2: `show access-lists OBSERVE-POLICY` -- Fresh matching requests are observed on OBSERVE-POLICY.
- R2: `show access-lists OBSERVE-PRIMARY` -- No matching request is observed on OBSERVE-PRIMARY.
- R1: `show ip route 192.0.2.2` -- The ordinary RIB still selects the primary next hop.

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
interface Ethernet0/2
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 exit
ip route 192.0.2.2 255.255.255.255 198.18.0.2
ip access-list extended SELECT-LAN
 permit icmp 198.18.10.0 0.0.0.255 host 192.0.2.2
 exit
ip sla 1
 icmp-echo 198.18.1.2 source-interface Ethernet0/1
 timeout 1000
 frequency 5
 exit
ip sla schedule 1 life forever start-time now
track 1 ip sla 1 reachability
 exit
route-map PBR permit 10
 match ip address SELECT-LAN
 set ip next-hop verify-availability 198.18.1.2 1 track 1
 exit
interface Ethernet0/2
 ip policy route-map PBR
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
ip route 198.18.10.0 255.255.255.0 198.18.0.1
ip access-list extended OBSERVE-PRIMARY
 10 permit icmp 198.18.10.0 0.0.0.255 host 192.0.2.2
 20 permit ip any any
 exit
interface Ethernet0/0
 ip access-group OBSERVE-PRIMARY in
 exit
ip access-list extended OBSERVE-POLICY
 10 permit icmp 198.18.10.0 0.0.0.255 host 192.0.2.2
 20 permit ip any any
 exit
interface Ethernet0/1
 ip access-group OBSERVE-POLICY in
 exit
end
```

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
interface range Ethernet0/0 - 3
 no ip address
 shutdown
 exit
interface Ethernet0/0
 ip address 198.18.10.10 255.255.255.0
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.10.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

[Cisco policy-routing reference](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/iproute_pi/command/iri-cr-book/iri-cr-a1.html). Actual data-path support must be confirmed by the recorded receiver observations.
