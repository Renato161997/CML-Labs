# iBGP eBGP Neighbors

[Topology YAML](../../labs/300-410-enarsi-implementing-cisco-enterprise-advanced-routing-and-services/bgp/013-ibgp-ebgp-neighbors.yaml) · [Observed validation](../../validation/RESULTS.md)

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

1. Establish and inspect the eBGP session.
2. Explain AS_PATH and next-hop using the received loopback prefix.
3. Convert a copy to iBGP and document the additional reachability/next-hop requirements.

## Acceptance checks

| Node | Command | Expected result |
| --- | --- | --- |
| R1 | `show ip bgp summary` | Neighbor is established and one prefix is received. |
| R1 | `ping 192.0.2.2 source Loopback0 repeat 3` | Learned loopback is reachable in both directions. |

## Reset and troubleshooting

Stop, wipe and restart **only this lab** to restore its checked-in startup configuration. Save your own configuration first if needed. Check interface state, addressing and routing before changing protocols. A failed ping alone does not identify the fault.
