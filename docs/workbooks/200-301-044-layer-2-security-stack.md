# Layer 2 Security Stack

## Scope and prerequisites

One IOSvL2 switch and three IOL-XE routers integrate DHCP snooping, DAI and sticky port security on isolated VLAN10. Only the DHCP server port is trusted. The legitimate client uses a public fixed exercise MAC and remains a real DHCP client throughout. SPOOFER starts down and duplicates that IP on another untrusted port; actual DAI drops and a healthy legitimate client identify the enforcement layer. The controlled MAC change restarts the client interface so fresh DHCP frames exercise port security. Acceptance requires an actual error-disabled port and nonzero security-violation count, not a failed IPv4 ping while DHCP is unavailable. Restoring the original MAC alone must not clear the latched violation. After the secured port is reset, the test waits for the real lease and snooping binding before checking gateway traffic and fresh ARP. The DHCP server may assign a different address after the interface cycle; recovery checks the actual pool lease, restored MAC/port binding and fresh ARP/data rather than requiring the initial address. All controls remain enabled. IP Source Guard, physical ASIC behavior and production NAC are outside scope. Nominal RAM is3840MiB.

Use licensed reference images for iol-xe, iosvl2 in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SERVER Ethernet0/0 <-> SW1 GigabitEthernet0/0
- CLIENT Ethernet0/0 <-> SW1 GigabitEthernet0/1
- SPOOFER Ethernet0/0 <-> SW1 GigabitEthernet0/2

| Node | Interface | Address |
| --- | --- | --- |
| SERVER | Ethernet0/0 | `ip address 198.18.10.1 255.255.255.0` |
| CLIENT | Ethernet0/0 | `ip address dhcp` |
| SPOOFER | Ethernet0/0 | `ip address 198.18.10.100 255.255.255.0` |

## Tasks

1. Correlate an actual DHCP lease, snooping binding, sticky source MAC and legitimate ARP/traffic.
2. Activate a duplicate-address sender on another untrusted port and distinguish DAI drops from port-security shutdown.
3. Change the protected client MAC, verify a latched port-security violation, then restore the MAC, port and actual DHCP binding before retesting traffic.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `show ip interface brief` | The legitimate endpoint acquires the actual first DHCP lease. |
| SW1 | `show ip dhcp snooping binding` | The switch binds the legitimate lease to the expected port. |
| CLIENT | `ping 198.18.10.1 repeat 3` | The legitimate client actually reaches its gateway. |
| SW1 | `show port-security interface GigabitEthernet0/1` | The protected client access port is operational. |
| SW1 | `show port-security address` | The fixed legitimate source MAC is actually learned on the protected port. |

## Transition: activate the separate static-IP impersonator

On **SPOOFER**:

```ios
configure terminal
interface Ethernet0/0
no shutdown
end
```

- SPOOFER: `ping 198.18.10.1 repeat 3` -- The unbound static sender cannot reach the gateway.
- SW1: `show ip arp inspection statistics vlan 10` -- Actual binding-related ARP drops are counted.
- CLIENT: `ping 198.18.10.1 repeat 3` -- The legitimate client actually reaches its gateway.
- SW1: `show port-security interface GigabitEthernet0/1` -- The protected client access port is operational.

## Transition: remove the separate impersonator

On **SPOOFER**:

```ios
configure terminal
interface Ethernet0/0
shutdown
end
```

- CLIENT: `ping 198.18.10.1 repeat 3` -- The legitimate client actually reaches its gateway.
- SW1: `show port-security interface GigabitEthernet0/1` -- The protected client access port is operational.

## Transition: change the protected DHCP client source MAC

On **CLIENT**:

```ios
configure terminal
interface Ethernet0/0
shutdown
mac-address 0200.0000.1009
no shutdown
end
```

- SW1: `show interfaces status` -- Port security actually error-disables the offending client port.
- SW1: `show port-security interface GigabitEthernet0/1` -- Port security records actual offending source frames.

## Transition: restore the authorized client source MAC

On **CLIENT**:

```ios
configure terminal
interface Ethernet0/0
shutdown
mac-address 0200.0000.1002
no shutdown
end
```

- SW1: `show interfaces status` -- Port security actually error-disables the offending client port.

## Transition: reset the secured port and reacquire the actual lease

On **SW1**:

```ios
configure terminal
interface GigabitEthernet0/1
shutdown
no shutdown
end
```

- SW1: `show port-security interface GigabitEthernet0/1` -- The protected client access port is operational.
- CLIENT: `show ip interface brief` -- The recovered client has a real DHCP lease from the configured pool; the address need not equal the initial lease.
- SW1: `show ip dhcp snooping binding` -- A current dynamic binding matches the restored MAC, expected VLAN and protected port.
- CLIENT: `ping 198.18.10.1 repeat 3` -- The legitimate client actually reaches its gateway.

## Transition: reset only the recovered inspection counters

On **SW1**:

```ios
clear ip arp inspection statistics
```

- SW1: `show ip dhcp snooping binding` -- A current dynamic binding matches the restored MAC, expected VLAN and protected port.

## Transition: prove fresh legitimate ARP after recovery

On **CLIENT**:

```ios
clear arp-cache
```

- CLIENT: `ping 198.18.10.1 repeat 3` -- The legitimate client actually reaches its gateway.
- SW1: `show ip arp inspection statistics vlan 10` -- Fresh legitimate ARP is actually permitted against the DHCP binding.
- SW1: `show port-security interface GigabitEthernet0/1` -- The protected client access port is operational.
- CLIENT: `show ip interface brief` -- The recovered client has a real DHCP lease from the configured pool; the address need not equal the initial lease.

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
interface range GigabitEthernet0/0 - 3
 shutdown
 exit
vlan 10
 name CLIENTS
 exit
ip dhcp snooping
ip dhcp snooping vlan 10
no ip dhcp snooping information option
ip arp inspection vlan 10
interface GigabitEthernet0/0
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 ip dhcp snooping trust
 ip arp inspection trust
 no shutdown
 exit
interface GigabitEthernet0/1
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 switchport port-security
 switchport port-security maximum 1
 switchport port-security violation shutdown
 switchport port-security mac-address sticky
 no shutdown
 exit
interface GigabitEthernet0/2
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
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
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 exit
ip dhcp excluded-address 198.18.10.1 198.18.10.99
ip dhcp pool CLIENTS
 network 198.18.10.0 255.255.255.0
 default-router 198.18.10.1
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
 mac-address 0200.0000.1002
 ip address dhcp
 no shutdown
 exit
end
```

### SPOOFER

```ios
hostname SPOOFER
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
 ip address 198.18.10.100 255.255.255.0
 no shutdown
 shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
