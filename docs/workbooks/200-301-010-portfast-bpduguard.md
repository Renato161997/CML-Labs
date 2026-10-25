# PortFast And BPDU Guard

## Scope and prerequisites

Requires three IOL reference nodes. SW2 deliberately models a switch attached to an edge port, not a recommended production design. The initial baseline has no BPDU Guard on that link so its traffic can be measured before protection is enabled. CLIENT keeps SW1 VLAN 10 active during the guarded-port failure. SW2 is made root after guard activation to produce fresh BPDUs deterministically; this does not imply BPDU Guard accepts inferior BPDUs. Recovery disables the guard only to restore this disposable baseline; in production remove the unauthorized bridge before re-enabling a protected edge port. No BPDU filtering is used to hide the fault.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SW1 Ethernet0/0 <-> SW2 Ethernet0/0
- SW1 Ethernet0/1 <-> CLIENT Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| SW1 | Vlan10 | `ip address 198.18.10.1 255.255.255.0` |
| SW2 | Vlan10 | `ip address 198.18.10.2 255.255.255.0` |
| CLIENT | Ethernet0/0 | `ip address 198.18.10.10 255.255.255.0` |

## Tasks

1. Distinguish configured PortFast from a suitable endpoint-only topology.
2. Enable explicit interface BPDU Guard and observe real err-disable after a peer BPDU.
3. Verify the authorized local endpoint remains reachable, then restore the disposable baseline.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `ping 198.18.10.1 repeat 3` | All three probes succeed. |
| CLIENT | `ping 198.18.10.2 repeat 3` | All three probes succeed. |
| SW1 | `show interfaces status` | The test-facing access port is connected. |

## Transition: arm the interface guard

On **SW1**:

```ios
configure terminal
interface Ethernet0/0
spanning-tree bpduguard enable
end
```

- SW1: `show running-config interface Ethernet0/0` -- The interface guard is explicitly enabled.

## Transition: peer BPDU disables the edge port

On **SW2**:

```ios
configure terminal
spanning-tree vlan 10 priority 0
end
```

- SW1: `show interfaces status` -- The edge port is actually error-disabled.
- CLIENT: `ping 198.18.10.2 repeat 3` -- The protected segment drops all three probes.
- CLIENT: `ping 198.18.10.1 repeat 3` -- All three probes succeed.

## Transition: restore the peer bridge priority

On **SW2**:

```ios
configure terminal
spanning-tree vlan 10 priority 32768
end
```

- SW2: `show spanning-tree vlan 10` -- The test bridge priority is restored before resetting the guarded port.

## Transition: restore the deliberately unprotected test baseline

On **SW1**:

```ios
configure terminal
interface Ethernet0/0
spanning-tree bpduguard disable
shutdown
no shutdown
end
```

- SW1: `show interfaces status` -- The test-facing access port is connected.
- CLIENT: `ping 198.18.10.2 repeat 3` -- All three probes succeed.
- CLIENT: `ping 198.18.10.1 repeat 3` -- All three probes succeed.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

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
 name LAB
 exit
spanning-tree vlan 10 priority 4096
interface Vlan10
 ip address 198.18.10.1 255.255.255.0
 no shutdown
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
end
```

### SW2

```ios
hostname SW2
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
 name LAB
 exit
spanning-tree vlan 10 priority 32768
interface Vlan10
 ip address 198.18.10.2 255.255.255.0
 no shutdown
 exit
interface Ethernet0/0
 switchport mode access
 switchport access vlan 10
 no shutdown
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
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

See [Cisco optional spanning-tree features](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst2960/software/release/12-2_53_se/configuration/guide/2960scg/swstpopt.html) for guard behavior. The live evidence above determines support on the tested virtual image.
