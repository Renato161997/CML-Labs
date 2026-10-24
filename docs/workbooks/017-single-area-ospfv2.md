# Single Area OSPFv2

[Topology YAML](../../labs/200-301-ccna-implementing-and-administering-cisco-solutions/ip-connectivity/017-single-area-ospfv2.yaml) · [Observed validation](../../validation/RESULTS.md)

## Scope and prerequisites

- Estimated study time: 35 minutes; difficulty: Intermediate.
- CML 2.10.1 is the validation target; use licensed reference images matching the node types below.
- No external connector. Do not bridge these demo configurations into a home, work or public network.
- No application installation from the Internet is required for routing/switching labs.
- An imported topology is not a functional pass. Dated results and exact tested image IDs are in [runtime evidence](../../validation/README.md).

## Topology and node requirements

- **R1**: `iosv`.
- **R2**: `iosv`.

```mermaid
flowchart LR
  n0["R1"]
  n1["R2"]
  n0 ---|"GigabitEthernet0/0 ↔ GigabitEthernet0/0"| n1
```

## Starting state

The startup configuration is a working reference baseline. Establish the checks below before changing it; then implement the exercises and compare your results.

## Addressing

### R1

```text
interface GigabitEthernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
```

### R2

```text
interface GigabitEthernet0/0
 ip address 198.18.0.2 255.255.255.252
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.2 255.255.255.255
 no shutdown
 exit
```

## Exercises

1. Explain how the router ID is selected.
2. Verify a FULL adjacency and a learned loopback route.
3. Make GigabitEthernet0/0 passive, observe loss of adjacency, then restore it.

## Acceptance checks

| Node | Command | Expected result |
| --- | --- | --- |
| R1 | `show ip ospf neighbor` | One FULL neighbor (2.2.2.2). |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Three successful replies using the learned OSPF route. |

## Reset and troubleshooting

Stop, wipe and restart **only this lab** to restore its checked-in startup configuration. Save your own configuration first if needed. Check interface state, addressing and routing before changing protocols. A failed ping alone does not identify the fault.
