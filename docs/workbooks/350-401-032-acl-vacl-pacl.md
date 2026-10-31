# ACL VACL PACL

## Scope and prerequisites

An IOL-L2 switch and three IOL-XE endpoints exchange actual ICMP in isolated VLAN10. CLIENT-A and CLIENT-B enter different access ports. The port ACL denies only echo requests to SERVER on CLIENT-A ingress: A service probes must fail, B service probes and both management paths must work, and SERVER-to-A probes must work because echo replies are not the selected request type. The VLAN access map instead selects those same echo requests on the entire VLAN, so both clients must lose service while management/reverse controls stay healthy. An ACL permit inside VACL-SELECT is a classifier; the access-map action performs the drop, and a separate explicit forward entry preserves unmatched traffic. The final detached policies restore both clients. This is tested virtual software forwarding, not an ASIC, throughput or production access-control guarantee. Nominal RAM is4GiB. Scope depends on actual independent-port traffic results, not accepted configuration text. IOSvL2 documents port/VLAN ACL capabilities at https://developer.cisco.com/docs/modeling-labs/iosvl2/ ; the recorded IOL-L2 image must independently pass these packet gates.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SERVER Ethernet0/0 <-> SW Ethernet0/0
- CLIENT-A Ethernet0/0 <-> SW Ethernet0/1
- CLIENT-B Ethernet0/0 <-> SW Ethernet0/2

| Node | Interface | Address |
| --- | --- | --- |
| SW | Vlan10 | `ip address 198.18.10.1 255.255.255.0` |
| CLIENT-A | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |
| CLIENT-B | Ethernet0/0 | `ip address 198.18.10.11 255.255.255.0` |
| SERVER | Ethernet0/0 | `ip address 198.18.10.20 255.255.255.0` |

## Tasks

1. Measure working traffic from two separate ingress ports in the same VLAN.
2. Apply a port ACL and prove only the selected ingress loses its service request while the other ingress remains healthy.
3. Replace the ingress policy with a VLAN access map and verify VLAN-wide scope, allowed management/reverse traffic and final rollback.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT-A | `ping 198.18.10.20 repeat 3` | All three probes succeed. |
| CLIENT-B | `ping 198.18.10.20 repeat 3` | All three probes succeed. |
| CLIENT-A | `ping 198.18.10.1 repeat 3` | All three probes succeed. |
| CLIENT-B | `ping 198.18.10.1 repeat 3` | All three probes succeed. |
| SERVER | `ping 198.18.10.10 repeat 3` | All three probes succeed. |

## Transition: apply only the selected ingress port ACL

On **SW**:

```ios
configure terminal
interface Ethernet0/1
ip access-group CLIENT-POLICY in
end
```

- CLIENT-A: `ping 198.18.10.20 repeat 3` -- The protected segment drops all three probes.
- CLIENT-B: `ping 198.18.10.20 repeat 3` -- All three probes succeed.
- CLIENT-A: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- CLIENT-B: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- SERVER: `ping 198.18.10.10 repeat 3` -- All three probes succeed.
- SW: `show access-lists CLIENT-POLICY` -- Actual selected ingress echo requests increment the deny counter.

## Transition: restore the unfiltered access port

On **SW**:

```ios
configure terminal
interface Ethernet0/1
no ip access-group CLIENT-POLICY in
end
```

- CLIENT-A: `ping 198.18.10.20 repeat 3` -- All three probes succeed.
- CLIENT-B: `ping 198.18.10.20 repeat 3` -- All three probes succeed.
- CLIENT-A: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- CLIENT-B: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- SERVER: `ping 198.18.10.10 repeat 3` -- All three probes succeed.

## Transition: apply VLAN-wide request selection

On **SW**:

```ios
configure terminal
vlan filter SERVICE-GUARD vlan-list 10
end
```

- CLIENT-A: `ping 198.18.10.20 repeat 3` -- The protected segment drops all three probes.
- CLIENT-B: `ping 198.18.10.20 repeat 3` -- The protected segment drops all three probes.
- CLIENT-A: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- CLIENT-B: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- SERVER: `ping 198.18.10.10 repeat 3` -- All three probes succeed.

## Transition: restore independent ingress service paths

On **SW**:

```ios
configure terminal
no vlan filter SERVICE-GUARD vlan-list 10
end
```

- CLIENT-A: `ping 198.18.10.20 repeat 3` -- All three probes succeed.
- CLIENT-B: `ping 198.18.10.20 repeat 3` -- All three probes succeed.
- CLIENT-A: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- CLIENT-B: `ping 198.18.10.1 repeat 3` -- All three probes succeed.
- SERVER: `ping 198.18.10.10 repeat 3` -- All three probes succeed.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### SW

```ios
hostname SW
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
 name POLICY-LAB
 exit
interface Ethernet0/0
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
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
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface Vlan10
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 exit
ip access-list extended CLIENT-POLICY
 deny icmp any host 198.18.10.20 echo
 permit ip any any
 exit
ip access-list extended VACL-SELECT
 permit icmp any host 198.18.10.20 echo
 exit
vlan access-map SERVICE-GUARD 10
 match ip address VACL-SELECT
 action drop
 exit
vlan access-map SERVICE-GUARD 20
 action forward
 exit
end
```

### CLIENT-A

```ios
hostname CLIENT-A
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
end
```

### CLIENT-B

```ios
hostname CLIENT-B
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
 ip address 198.18.10.11 255.255.255.0
 no shutdown
 exit
end
```

### SERVER

```ios
hostname SERVER
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
 ip address 198.18.10.20 255.255.255.0
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
