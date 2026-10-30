# CCNA Practical Checkpoint Two

## Scope and prerequisites

The NAT source ACL intentionally matches the wrong subnet. Interface roles, DHCP pool, local DNS and default route are otherwise correct. The initial direct-IP probe must fail before changing only the ACL prefix. IOL-XE models the endpoint: the address is DHCP-acquired but gateway and resolver are explicit fixture configuration, not a claim about DHCP client route installation. The ISP loopback is an isolated service target, not Internet access.

Use licensed reference images for iol-xe in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Deliberately broken: NAT-SOURCES permits an unused prefix rather than the actual DHCP client network. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- CLIENT Ethernet0/0 <-> EDGE Ethernet0/0
- EDGE Ethernet0/1 <-> ISP Ethernet0/0

| Node | Interface | Address |
| --- | --- | --- |
| EDGE | Ethernet0/0 | `ip address 192.0.2.1 255.255.255.0` |
| EDGE | Ethernet0/1 | `ip address 198.18.0.1 255.255.255.252` |
| CLIENT | Ethernet0/0 | `ip address dhcp` |
| ISP | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| ISP | Loopback0 | `ip address 203.0.113.80 255.255.255.255` |

## Tasks

1. Distinguish a working local DHCP/DNS service from failed external forwarding.
2. Find the incorrect source prefix in the PAT classification ACL.
3. Apply a narrow source-prefix repair, inspect the actual translation and verify name-based traffic.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `ping 203.0.113.80 repeat 3` | The endpoint reaches a destination with no customer return route only after PAT is repaired. |
| CLIENT | `show ip interface brief` | The client acquired its actual address by DHCP. |
| CLIENT | `ping app.example.test repeat 3` | The local DNS name resolves and the complete routed/PAT path works. |
| EDGE | `show ip nat translations` | An actual outside-global to inside-local translation exists. |
| ISP | `show ip route 192.0.2.0` | The ISP has no customer return route that could hide missing PAT. |

## Initial fault and repair

NAT-SOURCES permits an unused prefix rather than the actual DHCP client network.

Apply on EDGE:

```ios
configure terminal
ip access-list standard NAT-SOURCES
no permit 198.18.99.0 0.0.0.255
permit 192.0.2.0 0.0.0.255
end
```

Run baseline acceptance after the repair.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### EDGE

```ios
hostname EDGE
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
no logging console
ip dhcp excluded-address 192.0.2.1 192.0.2.9
ip dhcp pool CLIENTS
 network 192.0.2.0 255.255.255.0
 default-router 192.0.2.1
 dns-server 192.0.2.1
 exit
ip dns server
ip host app.example.test 203.0.113.80
ip access-list standard NAT-SOURCES
 permit 198.18.99.0 0.0.0.255
 exit
interface Ethernet0/0
 ip address 192.0.2.1 255.255.255.0
 ip nat inside
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.0.1 255.255.255.252
 ip nat outside
 no shutdown
 exit
ip nat inside source list NAT-SOURCES interface Ethernet0/1 overload
ip route 0.0.0.0 0.0.0.0 198.18.0.2
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
no logging console
ip domain lookup
ip name-server 192.0.2.1
interface Ethernet0/0
 ip address dhcp
 no shutdown
 exit
ip route 0.0.0.0 0.0.0.0 192.0.2.1
end
```

### ISP

```ios
hostname ISP
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
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Loopback0
 ip address 203.0.113.80 255.255.255.255
 no shutdown
 exit
end
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

## Healthy dependencies before fault measurement

Wait for CLIENT to hold a DHCP lease, verify its gateway ping, and verify EDGE reaches the isolated ISP service. The runner records these prerequisites before attempting the deliberately failing client probe or changing the NAT ACL. An unavailable IP stack or failed upstream link must never be treated as proof of the intended NAT fault.
