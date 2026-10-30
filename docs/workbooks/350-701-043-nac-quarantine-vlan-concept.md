# NAC Quarantine VLAN Concept

## Scope and prerequisites

Four IOL reference nodes demonstrate the enforcement side of a NAC quarantine concept. An operator deliberately changes the port VLAN and the explicit IOL endpoint address/default route; no RADIUS, ISE, 802.1X, MAB or automatic admission engine is claimed. VLAN999 has a real routed ingress policy permitting only the documentation remediation loopback and denying other traffic. Once the endpoint has the quarantine address, remediation must succeed while the actual internal service fails with a deny counter. The service-side gateway remains healthy. Restoring the access VLAN and explicit endpoint configuration must recover the original service. VLAN movement alone is not falsely presented as a working posture or identity decision. Nominal RAM is4GiB.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- GW Ethernet0/0 <-> SW1 Ethernet0/0
- HOST Ethernet0/0 <-> SW1 Ethernet0/1
- GW Ethernet0/1 <-> SERVICE Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| GW | Ethernet0/0.10 | `ip address 198.18.10.1 255.255.255.0` |
| GW | Ethernet0/0.999 | `ip address 198.18.99.1 255.255.255.0` |
| GW | Ethernet0/1 | `ip address 198.18.20.1 255.255.255.0` |
| GW | Loopback0 | `ip address 192.0.2.80 255.255.255.255` |
| HOST | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |
| SERVICE | Ethernet0/0 | `ip address 198.18.20.101 255.255.255.0` |

## Tasks

1. Distinguish a manual admission decision, access-port VLAN membership and routed quarantine policy.
2. Move the endpoint to quarantine and prove a working remediation path with blocked internal service.
3. Restore authorized membership and endpoint addressing, then verify normal service recovery.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| HOST | `ping 198.18.20.101 source Ethernet0/0 repeat 3` | The actual endpoint probe succeeds. |
| HOST | `ping 192.0.2.80 source Ethernet0/0 repeat 3` | The actual endpoint probe succeeds. |
| SW1 | `show interfaces Ethernet0/1 switchport` | The endpoint initially belongs to the authorized VLAN. |

## Transition: move the access port into quarantine

On **SW1**:

```ios
configure terminal
interface Ethernet0/1
switchport access vlan 999
end
```

- SW1: `show interfaces Ethernet0/1 switchport` -- The actual endpoint access port belongs to the quarantine VLAN.

## Transition: configure the explicit quarantine endpoint state

On **HOST**:

```ios
configure terminal
interface Ethernet0/0
ip address 198.18.99.10 255.255.255.0
exit
no ip route 0.0.0.0 0.0.0.0 198.18.10.1
ip route 0.0.0.0 0.0.0.0 198.18.99.1
end
```

- HOST: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.
- HOST: `ping 198.18.20.101 source Ethernet0/0 repeat 3` -- The actual endpoint probe is blocked during the controlled fault.
- GW: `show access-lists QUARANTINE` -- The quarantine gateway counts actual denied service traffic.
- SERVICE: `ping 198.18.20.1 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.

## Transition: restore authorized port membership

On **SW1**:

```ios
configure terminal
interface Ethernet0/1
switchport access vlan 10
end
```

- SW1: `show interfaces Ethernet0/1 switchport` -- The access switch restores the authorized VLAN.

## Transition: restore the original explicit endpoint configuration

On **HOST**:

```ios
configure terminal
interface Ethernet0/0
ip address 198.18.10.10 255.255.255.0
exit
no ip route 0.0.0.0 0.0.0.0 198.18.99.1
ip route 0.0.0.0 0.0.0.0 198.18.10.1
end
```

- HOST: `ping 198.18.20.101 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.
- HOST: `ping 192.0.2.80 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.
- SERVICE: `ping 198.18.20.1 source Ethernet0/0 repeat 3` -- The actual endpoint probe succeeds.

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
interface Ethernet0/0
 no shutdown
 exit
interface Ethernet0/0.10
 encapsulation dot1Q 10
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 exit
interface Ethernet0/0.999
 encapsulation dot1Q 999
 ip address 198.18.99.1 255.255.255.0
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.20.1 255.255.255.0
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.80 255.255.255.255
 no shutdown
 exit
ip access-list extended QUARANTINE
 permit icmp 198.18.99.0 0.0.0.255 host 192.0.2.80
 deny ip any any
 exit
interface Ethernet0/0.999
 ip access-group QUARANTINE in
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
 name AUTHORIZED
 exit
vlan 999
 name QUARANTINE
 exit
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10,999
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
end
```

### HOST

```ios
hostname HOST
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

### SERVICE

```ios
hostname SERVICE
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
 ip address 198.18.20.101 255.255.255.0
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 198.18.20.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
