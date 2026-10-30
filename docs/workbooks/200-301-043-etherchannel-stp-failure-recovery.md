# EtherChannel STP Failure Recovery

## Scope and prerequisites

Three IOL-L2 switches form a real VLAN10 triangle; SW1-SW2 uses two-member LACP and SW3 supplies a separate redundant path. Explicit priorities and VLAN costs make expected roles deterministic. A single-member shutdown must keep Po1 active. A logical port-channel shutdown must change SW2 root port to the SW3 path while preserving actual sourced SVI traffic. The test models administrative link failures and protocol convergence, not physical cable timing or throughput. Nominal RAM is3GiB.

Use licensed reference images for ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SW1 Ethernet0/0 <-> SW2 Ethernet0/0
- SW1 Ethernet0/1 <-> SW2 Ethernet0/1
- SW1 Ethernet0/2 <-> SW3 Ethernet0/0
- SW2 Ethernet0/2 <-> SW3 Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| SW1 | Vlan10 | `ip address 198.18.10.1 255.255.255.0` |
| SW2 | Vlan10 | `ip address 198.18.10.2 255.255.255.0` |
| SW3 | Vlan10 | `ip address 198.18.10.3 255.255.255.0` |

## Tasks

1. Validate LACP membership and STP root/alternate roles independently of successful IP traffic.
2. Lose one bundle member without changing the preferred logical path.
3. Shut the logical bundle, prove STP fallback through the third switch, then restore both protocols.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| SW2 | `show etherchannel summary` | Both physical members actually participate in the Layer2 LACP bundle. |
| SW2 | `show spanning-tree vlan 10` | The port-channel is the preferred root-facing path. |
| SW3 | `show spanning-tree vlan 10` | The redundant triangle link is blocked by STP. |
| SW2 | `ping 198.18.10.1 source Vlan10 repeat 3` | Actual VLAN traffic survives each supported path change. |

## Transition: lose one LACP member

On **SW2**:

```ios
configure terminal
interface Ethernet0/1
shutdown
end
```

- SW2: `show etherchannel summary` -- The remaining member keeps the bundle usable.
- SW2: `show spanning-tree vlan 10` -- The port-channel is the preferred root-facing path.
- SW2: `ping 198.18.10.1 source Vlan10 repeat 3` -- Actual VLAN traffic survives each supported path change.

## Transition: restore both LACP members

On **SW2**:

```ios
configure terminal
interface Ethernet0/1
no shutdown
end
```

- SW2: `show etherchannel summary` -- Both physical members actually participate in the Layer2 LACP bundle.
- SW2: `ping 198.18.10.1 source Vlan10 repeat 3` -- Actual VLAN traffic survives each supported path change.

## Transition: fail the logical bundle

On **SW2**:

```ios
configure terminal
interface Port-channel1
shutdown
end
```

- SW2: `show interfaces Port-channel1` -- The fault is on the actual logical interface.
- SW2: `show spanning-tree vlan 10` -- SW2 now reaches the root through SW3.
- SW3: `show spanning-tree vlan 10` -- The former alternate path actually forwards.
- SW2: `ping 198.18.10.1 source Vlan10 repeat 3` -- Actual VLAN traffic survives each supported path change.

## Transition: recover the preferred bundle path

On **SW2**:

```ios
configure terminal
interface Port-channel1
no shutdown
end
```

- SW2: `show etherchannel summary` -- Both physical members actually participate in the Layer2 LACP bundle.
- SW2: `show spanning-tree vlan 10` -- The port-channel is the preferred root-facing path.
- SW3: `show spanning-tree vlan 10` -- The redundant triangle link is blocked by STP.
- SW2: `ping 198.18.10.1 source Vlan10 repeat 3` -- Actual VLAN traffic survives each supported path change.

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
spanning-tree mode rapid-pvst
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/0
 channel-group 1 mode active
 exit
interface Ethernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 channel-group 1 mode active
 exit
interface Port-channel1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
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
spanning-tree vlan 10 priority 8192
interface Vlan10
 ip address 198.18.10.2 255.255.255.0
 no shutdown
 exit
spanning-tree mode rapid-pvst
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/0
 channel-group 1 mode active
 exit
interface Ethernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 channel-group 1 mode active
 exit
interface Port-channel1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
end
```

### SW3

```ios
hostname SW3
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
 ip address 198.18.10.3 255.255.255.0
 no shutdown
 exit
spanning-tree mode rapid-pvst
interface Ethernet0/0
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
interface Ethernet0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 10
 spanning-tree vlan 10 cost 4
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
