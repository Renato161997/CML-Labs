# GRE Tunnel Routing

## Scope and prerequisites

IOL-XE reference images are required. GRE provides encapsulation, not encryption or authentication. This two-router exercise has no keepalive, intentionally demonstrating that tunnel up state alone does not establish successful payload forwarding.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Tunnel0 | `ip address 172.16.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| R2 | Tunnel0 | `ip address 172.16.0.2 255.255.255.252` |

## Tasks

1. Distinguish physical underlay routes from overlay endpoint routes.
2. Block GRE while leaving IP connectivity intact and observe the misleading up interface.
3. Restore forwarding and verify the GRE data plane.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show interfaces Tunnel0` | The GRE interface is up; this alone is not a data-plane proof. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |

## Transition: GRE is filtered

On **R2**:

```ios
configure terminal
ip access-list extended BLOCK-GRE
deny gre host 198.18.0.1 host 198.18.0.2
permit ip any any
exit
interface Ethernet0/0
ip access-group BLOCK-GRE in
end
```

- R1: `show interfaces Tunnel0` -- The GRE interface is up; this alone is not a data-plane proof.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- All three probes fail while the route is removed.
- R2: `show access-lists BLOCK-GRE` -- The filter counts actual blocked GRE packets.

## Transition: GRE restored

On **R2**:

```ios
configure terminal
interface Ethernet0/0
no ip access-group BLOCK-GRE in
end
```

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
interface Tunnel0
 ip address 172.16.0.1 255.255.255.252
 tunnel source Ethernet0/0
 tunnel destination 198.18.0.2
 tunnel mode gre ip
 no shutdown
 exit
ip route 192.0.2.2 255.255.255.255 172.16.0.2
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
interface Tunnel0
 ip address 172.16.0.2 255.255.255.252
 tunnel source Ethernet0/0
 tunnel destination 198.18.0.1
 tunnel mode gre ip
 no shutdown
 exit
ip route 192.0.2.1 255.255.255.255 172.16.0.1
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
