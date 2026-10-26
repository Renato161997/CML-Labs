# EIGRP Named Mode

## Scope and prerequisites

Two IOL-XE nodes run named EIGRP CAMPUS with IPv4 AS100. Default interfaces are passive; only the transit AF-interface sends hellos. The fault changes the AF-interface on R2, not the link or AS number. Peer state, installed RIB entries and real source-loopback probes are all checked. This is a single address-family exercise, not proof of IPv6 or multi-VRF EIGRP behavior.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> R2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Trace the named process, IPv4 address family, topology base and interface submode.
2. Make only the transit AF-interface passive and observe the lost peer and route.
3. Restore the adjacency and forwarding without changing the endpoint addresses.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show running-config | section router eigrp` | The process uses named-mode configuration. |
| R1 | `show ip eigrp neighbors` | The named IPv4 address family has an actual peer. |
| R1 | `show ip route 192.0.2.2` | EIGRP installs the remote endpoint route. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three replies. |

## Transition: transit address-family interface becomes passive

On **R2**:

```ios
configure terminal
router eigrp CAMPUS
address-family ipv4 unicast autonomous-system 100
af-interface Ethernet0/0
passive-interface
end
```

- R1: `show ip eigrp neighbors` -- The neighbor table exists but the transit peer has expired.
- R1: `show ip route 192.0.2.2` -- The endpoint route is actually withdrawn.
- R1: `ping 192.0.2.2 source Loopback0 repeat 3` -- All three probes fail while the route is removed.

## Transition: restore transit hello exchange

On **R2**:

```ios
configure terminal
router eigrp CAMPUS
address-family ipv4 unicast autonomous-system 100
af-interface Ethernet0/0
no passive-interface
end
```

- R1: `show ip eigrp neighbors` -- The named IPv4 address family has an actual peer.
- R1: `show ip route 192.0.2.2` -- EIGRP installs the remote endpoint route.
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
router eigrp CAMPUS
 address-family ipv4 unicast autonomous-system 100
  network 198.18.0.0 0.0.0.3
  network 192.0.2.1 0.0.0.0
  af-interface default
   passive-interface
  exit-af-interface
  af-interface Ethernet0/0
   no passive-interface
   hello-interval 2
   hold-time 6
  exit-af-interface
  topology base
   no auto-summary
  exit-af-topology
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
router eigrp CAMPUS
 address-family ipv4 unicast autonomous-system 100
  network 198.18.0.0 0.0.0.3
  network 192.0.2.2 0.0.0.0
  af-interface default
   passive-interface
  exit-af-interface
  af-interface Ethernet0/0
   no passive-interface
   hello-interval 2
   hold-time 6
  exit-af-interface
  topology base
   no auto-summary
  exit-af-topology
 exit-address-family
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
