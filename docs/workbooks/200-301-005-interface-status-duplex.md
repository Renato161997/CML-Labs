# Interface Status Duplex Speed

## Scope and prerequisites

The interface can report speed and duplex, but a virtual NIC does not reproduce copper negotiation, damaged cables or real duplex mismatches. This exercise tests the supported administrative-state transition explicitly.

Use licensed reference images for iosv in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 GigabitEthernet0/0 <-> R2 GigabitEthernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | GigabitEthernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R2 | Loopback0 | `ip address 192.0.2.2 255.255.255.255` |
| R2 | GigabitEthernet0/0 | `ip address 198.18.0.2 255.255.255.252` |

## Tasks

1. Read administrative state, protocol state and virtual duplex reporting.
2. Shut the interface and distinguish administratively down from a peer fault.
3. Restore the interface and verify direct connectivity.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show interfaces GigabitEthernet0/0` | The virtual interface and protocol are up. |
| R1 | `ping 198.18.0.2 repeat 3` | The directly connected peer replies. |

## Transition: administrative shutdown

On **R1**:

```ios
configure terminal
interface GigabitEthernet0/0
shutdown
end
```

- R1: `show interfaces GigabitEthernet0/0` -- The local interface is explicitly disabled.

## Transition: administrative recovery

On **R1**:

```ios
configure terminal
interface GigabitEthernet0/0
no shutdown
end
```

- R1: `show interfaces GigabitEthernet0/0` -- The virtual interface and protocol are up.

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
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
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
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
interface GigabitEthernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
end
```

## Platform scope

[IOSv feature support](https://developer.cisco.com/docs/modeling-labs/iosv/) and [IOSvL2 feature support](https://developer.cisco.com/docs/modeling-labs/iosvl2/) describe the software platforms. This exercise verifies routing/control behavior, not hardware throughput, physical failure timing or certification coverage. A catalog entry is only marked passed after actual console acceptance and cleanup.
