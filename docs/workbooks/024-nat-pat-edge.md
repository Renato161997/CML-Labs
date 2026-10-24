# NAT PAT Internet Edge

[Topology YAML](../../labs/200-301-ccna-implementing-and-administering-cisco-solutions/ip-services/024-nat-pat-edge.yaml) · [Observed validation](../../validation/RESULTS.md)

## Scope and prerequisites

- Estimated study time: 35 minutes; difficulty: Intermediate.
- CML 2.10.1 is the validation target; use licensed reference images matching the node types below.
- No external connector. Do not bridge these demo configurations into a home, work or public network.
- No application installation from the Internet is required for routing/switching labs.
- An imported topology is not a functional pass. Dated results and exact tested image IDs are in [runtime evidence](../../validation/README.md).

## Topology and node requirements

- **CLIENT**: `iosv`.
- **EDGE**: `iosv`.
- **ISP**: `iosv`.

```mermaid
flowchart LR
  n0["CLIENT"]
  n1["EDGE"]
  n2["ISP"]
  n0 ---|"GigabitEthernet0/0 ↔ GigabitEthernet0/0"| n1
  n1 ---|"GigabitEthernet0/1 ↔ GigabitEthernet0/0"| n2
```

## Starting state

The startup configuration is a working reference baseline. Establish the checks below before changing it; then implement the exercises and compare your results.

## Addressing

### CLIENT

```text
interface GigabitEthernet0/0
 ip address 198.18.10.2 255.255.255.0
 no shutdown
 exit
```

### EDGE

```text
interface GigabitEthernet0/0
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 ip nat inside
 exit
interface GigabitEthernet0/1
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 ip nat outside
 exit
```

### ISP

```text
interface GigabitEthernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.100 255.255.255.255
 no shutdown
 exit
```

## Exercises

1. Explain why ISP has no route to the client subnet.
2. Generate ICMP and inspect the translated source.
3. Remove the inside NAT role, observe failure, then restore it.

## Acceptance checks

| Node | Command | Expected result |
| --- | --- | --- |
| CLIENT | `ping 192.0.2.100 repeat 3` | Translated traffic reaches the ISP loopback. |
| EDGE | `show ip nat statistics` | NAT hit counter increases after client traffic. |

## Reset and troubleshooting

Stop, wipe and restart **only this lab** to restore its checked-in startup configuration. Save your own configuration first if needed. Check interface state, addressing and routing before changing protocols. A failed ping alone does not identify the fault.
