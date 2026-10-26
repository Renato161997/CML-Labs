# GRE Overlay Underlay

## Scope and prerequisites

Two IOL-XE routers provide an unencrypted GRE overlay with routed loopback endpoints. The tunnel IP MTU is deliberately limited to1400, below the underlying Ethernet limit; a1401-byte DF request provides a precise negative control. Both directions are tested independently because an echo reply need not copy the request DF bit. This measures configured L3 tunnel limits, not an unknown physical path MTU, encryption, wire capture or hardware fragmentation performance.

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

1. Separate direct underlay reachability from GRE overlay endpoint routing.
2. Measure both request directions at the configured tunnel IP MTU with DF set.
3. Increase and restore both tunnel MTUs while checking the unchanged underlay.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show interfaces Tunnel0` | The live tunnel uses GRE over IP. |
| R1 | `show ip interface Tunnel0` | The active tunnel IP MTU is 1400. |
| R2 | `show ip interface Tunnel0` | The active tunnel IP MTU is 1400. |
| R1 | `ping 198.18.0.2 size 1401 df-bit repeat 3` | The same-sized DF request succeeds on the direct underlay. |
| R1 | `ping 192.0.2.2 source Loopback0 size 1400 df-bit repeat 3` | The 1400-byte DF request crosses the configured tunnel MTU. |
| R2 | `ping 192.0.2.1 source Loopback0 size 1400 df-bit repeat 3` | The 1400-byte DF request crosses the configured tunnel MTU. |
| R1 | `ping 192.0.2.2 source Loopback0 size 1401 df-bit repeat 3` | The 1401-byte DF request is larger than the configured tunnel IP MTU. |
| R2 | `ping 192.0.2.1 source Loopback0 size 1401 df-bit repeat 3` | The 1401-byte DF request is larger than the configured tunnel IP MTU. |

## Transition: increase first tunnel MTU

On **R1**:

```ios
configure terminal
interface Tunnel0
ip mtu 1450
end
```

- R1: `show ip interface Tunnel0` -- The active tunnel IP MTU is 1450.

## Transition: increase second tunnel MTU

On **R2**:

```ios
configure terminal
interface Tunnel0
ip mtu 1450
end
```

- R1: `show ip interface Tunnel0` -- The active tunnel IP MTU is 1450.
- R2: `show ip interface Tunnel0` -- The active tunnel IP MTU is 1450.
- R1: `ping 198.18.0.2 size 1401 df-bit repeat 3` -- The same-sized DF request succeeds on the direct underlay.
- R1: `ping 192.0.2.2 source Loopback0 size 1401 df-bit repeat 3` -- The 1401-byte DF request crosses the configured tunnel MTU.
- R2: `ping 192.0.2.1 source Loopback0 size 1401 df-bit repeat 3` -- The 1401-byte DF request crosses the configured tunnel MTU.

## Transition: restore first tunnel MTU

On **R1**:

```ios
configure terminal
interface Tunnel0
ip mtu 1400
end
```

- R1: `show ip interface Tunnel0` -- The active tunnel IP MTU is 1400.

## Transition: restore second tunnel MTU

On **R2**:

```ios
configure terminal
interface Tunnel0
ip mtu 1400
end
```

- R1: `show ip interface Tunnel0` -- The active tunnel IP MTU is 1400.
- R2: `show ip interface Tunnel0` -- The active tunnel IP MTU is 1400.
- R1: `ping 198.18.0.2 size 1401 df-bit repeat 3` -- The same-sized DF request succeeds on the direct underlay.
- R1: `ping 192.0.2.2 source Loopback0 size 1400 df-bit repeat 3` -- The 1400-byte DF request crosses the configured tunnel MTU.
- R2: `ping 192.0.2.1 source Loopback0 size 1400 df-bit repeat 3` -- The 1400-byte DF request crosses the configured tunnel MTU.
- R1: `ping 192.0.2.2 source Loopback0 size 1401 df-bit repeat 3` -- The 1401-byte DF request is larger than the configured tunnel IP MTU.
- R2: `ping 192.0.2.1 source Loopback0 size 1401 df-bit repeat 3` -- The 1401-byte DF request is larger than the configured tunnel IP MTU.

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
 ip mtu 1400
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
 ip mtu 1400
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
