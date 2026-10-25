# Port Security Sticky MAC

## Scope and prerequisites

Requires IOL-L2 XE and IOL-XE. Restrict mode drops the violating source while retaining the port. The temporary locally administered address exists only on the isolated test link. Restoring no mac-address returns the client to its original burned-in address; this does not model physical tampering protection.

Use licensed reference images for iol-xe, ioll2-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> SW1 Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| SW1 | Vlan10 | `ip address 198.18.0.2 255.255.255.252` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |

## Tasks

1. Learn one real source MAC with sticky port security.
2. Change the test client MAC and observe actual dropped traffic and violations.
3. Restore the original interface MAC and verify forwarding resumes.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.0.2 repeat 3` | The learned client can reach the management SVI. |
| SW1 | `show port-security interface Ethernet0/0` | One actual source MAC has been learned. |

## Transition: unrecognized client MAC

On **R1**:

```ios
configure terminal
interface Ethernet0/0
mac-address 0200.0000.0002
end
```

- R1: `ping 198.18.0.2 repeat 3` -- The unrecognized source is blocked.
- SW1: `show port-security interface Ethernet0/0` -- The violation counter records actual denied frames.

## Transition: original client returns

On **R1**:

```ios
configure terminal
interface Ethernet0/0
no mac-address
end
```

- R1: `ping 198.18.0.2 repeat 3` -- The learned client can reach the management SVI.

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
 name USERS
interface Vlan10
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Ethernet0/0
 switchport mode access
 switchport access vlan 10
 switchport port-security
 switchport port-security maximum 1
 switchport port-security violation restrict
 switchport port-security mac-address sticky
 spanning-tree portfast
 no shutdown
 exit
end
```

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
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
