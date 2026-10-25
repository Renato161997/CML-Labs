# CDP And LLDP Discovery

## Scope and prerequisites

Requires IOL-L2 XE. CDP and LLDP are explicitly enabled on an isolated Layer-2 link. A five-second LLDP advertisement interval bounds the exercise waiting time; it is not a production tuning recommendation. No physical cable or transceiver behavior is modeled.

Use licensed reference images for ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SW1 Ethernet0/0 <-> SW2 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| SW1 | Vlan10 | `ip address 198.18.0.1 255.255.255.252` |
| SW2 | Vlan10 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Identify the same peer through independent CDP and LLDP tables.
2. Compare discovered port identity with the actual lab wiring.
3. Verify IP reachability separately from discovery.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| SW1 | `show cdp neighbors` | The Cisco discovery table contains SW2. |
| SW1 | `show lldp neighbors` | The IEEE LLDP table independently contains SW2. |
| SW1 | `ping 198.18.0.2 source Vlan10 repeat 3` | The management SVIs communicate across VLAN 10. |

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
cdp run
lldp run
lldp timer 5
vlan 10
 name DISCOVERY
interface Vlan10
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
interface Ethernet0/0
 switchport mode access
 switchport access vlan 10
 lldp transmit
 lldp receive
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
cdp run
lldp run
lldp timer 5
vlan 10
 name DISCOVERY
interface Vlan10
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Ethernet0/0
 switchport mode access
 switchport access vlan 10
 lldp transmit
 lldp receive
 no shutdown
 exit
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
