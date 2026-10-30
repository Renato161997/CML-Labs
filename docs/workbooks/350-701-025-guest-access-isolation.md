# Guest Access Isolation

## Scope and prerequisites

Four IOL reference nodes implement a trusted VLAN, a guest VLAN, real guest DHCP and gateway-local DNS for a documentation portal loopback. IOL models the guest endpoint: its address is acquired dynamically, while gateway and DNS client configuration are explicit; no desktop DHCP-option behavior is claimed. The guest ingress ACL permits DHCP/DNS, denies trusted-subnet destinations, allows only the guest source prefix for remaining traffic, and denies other sources. This is stateless policy, so guest replies toward trusted destinations are also denied; stateful trusted-initiated sessions are not claimed. An early permit must visibly bypass isolation, its removal must restore actual denies, and separate guest trunk pruning must preserve trusted portal availability. Restoring the trunk must first recover actual gateway reachability, then DNS/portal while retaining isolation. DNS command collection has a bounded90-second limit separate from Layer2 convergence. The portal is a local router loopback, not Internet access or a captive portal product. Nominal RAM is4GiB.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- GW Ethernet0/0 <-> SW1 Ethernet0/0
- TRUSTED Ethernet0/0 <-> SW1 Ethernet0/1
- GUEST Ethernet0/0 <-> SW1 Ethernet0/2

| Node | Interface | Address |
| --- | --- | --- |
| GW | Ethernet0/0.10 | `ip address 198.18.10.1 255.255.255.0` |
| GW | Ethernet0/0.20 | `ip address 198.18.20.1 255.255.255.0` |
| GW | Loopback0 | `ip address 192.0.2.80 255.255.255.255` |
| TRUSTED | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |
| GUEST | Ethernet0/0 | `ip address dhcp` |

## Tasks

1. Acquire a real guest DHCP lease and resolve an isolated portal through the allowed DNS path.
2. Prove routed guest isolation using actual deny counters while trusted service remains healthy.
3. Repair an early permit and distinguish policy enforcement from a pruned guest trunk.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| GUEST | `show ip interface brief` | The guest obtains an actual DHCP lease. |
| GUEST | `ping portal.lab.example source Ethernet0/0 repeat 3` | The actual endpoint probe succeeds. |
| GUEST | `ping 198.18.10.10 source Ethernet0/0 repeat 3` | The actual endpoint probe is blocked during the controlled fault. |
| GW | `show access-lists GUEST-POLICY` | Actual guest-to-trusted packets hit the isolation deny. |
| TRUSTED | `ping 192.0.2.80 source Ethernet0/0 repeat 3` | The actual endpoint probe succeeds. |

## Transition: introduce an early guest policy bypass

On **GW**:

```ios
configure terminal
ip access-list extended GUEST-POLICY
5 permit ip any any
end
```

- GUEST: `ping 198.18.10.10 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.
- GW: `show access-lists GUEST-POLICY` -- The misplaced permit actually bypasses isolation.

## Transition: restore the ordered guest policy

On **GW**:

```ios
configure terminal
ip access-list extended GUEST-POLICY
no 5
end
```

- GUEST: `ping 198.18.10.10 source Ethernet0/0 repeat 3` -- The actual endpoint probe is blocked during the controlled fault.
- GW: `show access-lists GUEST-POLICY` -- Actual guest-to-trusted packets hit the isolation deny.
- GUEST: `ping portal.lab.example source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.
- TRUSTED: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.

## Transition: prune only the guest VLAN

On **SW1**:

```ios
configure terminal
interface Ethernet0/0
switchport trunk allowed vlan 10
end
```

- GUEST: `ping 198.18.20.1 source Ethernet0/0 repeat 3` -- The actual endpoint probe is blocked during the controlled fault.
- TRUSTED: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.

## Transition: restore guest trunk availability

On **SW1**:

```ios
configure terminal
interface Ethernet0/0
switchport trunk allowed vlan 10,20
end
```

- GUEST: `ping 198.18.20.1 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.
- GUEST: `ping portal.lab.example source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.
- GUEST: `ping 198.18.10.10 source Ethernet0/0 repeat 3` -- The actual endpoint probe is blocked during the controlled fault.
- GW: `show access-lists GUEST-POLICY` -- Actual guest-to-trusted packets hit the isolation deny.
- TRUSTED: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### GW

```ios
hostname GW
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
ip dns server
ip host portal.lab.example 192.0.2.80
interface Ethernet0/0
 no shutdown
 exit
interface Ethernet0/0.10
 encapsulation dot1Q 10
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 exit
interface Ethernet0/0.20
 encapsulation dot1Q 20
 ip address 198.18.20.1 255.255.255.0
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.80 255.255.255.255
 no shutdown
 exit
ip dhcp excluded-address 198.18.20.1 198.18.20.99
ip dhcp pool GUESTS
 network 198.18.20.0 255.255.255.0
 default-router 198.18.20.1
 dns-server 198.18.20.1
 exit
ip access-list extended GUEST-POLICY
 10 permit udp any eq bootpc any eq bootps
 20 permit udp 198.18.20.0 0.0.0.255 host 198.18.20.1 eq domain
 30 permit tcp 198.18.20.0 0.0.0.255 host 198.18.20.1 eq domain
 40 deny ip any 198.18.10.0 0.0.0.255
 50 permit ip 198.18.20.0 0.0.0.255 any
 60 deny ip any any
 exit
interface Ethernet0/0.20
 ip access-group GUEST-POLICY in
 exit
end
```

### SW1

```ios
hostname SW1
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
vtp mode transparent
spanning-tree mode rapid-pvst
interface range Ethernet0/0 - 3
 shutdown
 exit
vlan 10
 exit
vlan 20
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,20
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface Ethernet0/2
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
 no shutdown
 exit
end
```

### TRUSTED

```ios
hostname TRUSTED
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

### GUEST

```ios
hostname GUEST
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
ip domain-lookup
ip name-server 198.18.20.1
interface Ethernet0/0
 ip address dhcp
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.20.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
