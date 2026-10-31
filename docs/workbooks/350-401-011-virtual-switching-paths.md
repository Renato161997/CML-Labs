# Virtual Switching: VLAN Isolation and Dynamic MAC Learning

## Scope and prerequisites

A real native Linux kernel bridge forwards between two independent native endpoints. SW eth1 connects LEFT eth1 and SW eth2 connects RIGHT eth1. Only these point-to-point links exist; native management eth0 is unwired. Untagged data ports start in VLAN10 with PVID10. VLAN99 stays tagged on both physical ports and terminates on SW br0.99, while endpoint eth1.99 interfaces provide an independent control path on the same physical links.

LEFT untagged data is 198.18.0.1/30 and RIGHT is 198.18.0.2/30. Tagged control addresses are SW 198.18.1.1/29, LEFT 198.18.1.2/29 and RIGHT 198.18.1.3/29. No data IP is assigned to br0 itself, and no routing between the data VLANs is configured. Actual interface-bound IPv4 probes establish connectivity; a warm-up packet precedes each measured three-packet sample. The control ping must succeed even when data isolation is expected. Missing interfaces, addresses or a disabled port cannot substitute for VLAN isolation.

The fault moves only SW eth2 untagged/PVID membership from VLAN10 to VLAN20 and preserves tagged VLAN99. Both data directions must fail while both tagged control paths still receive three replies. Repair restores VLAN10 and requires real bidirectional data recovery plus dynamically learned data-VLAN MAC entries. Those entries must match peer identities observed independently in the tagged control neighbor table; static, self, sticky and externally imported FDB entries cannot pass as learned traffic. CLI policy operations inspect actual state and refuse unknown or leaking membership rather than blindly rewriting it.

This uses software bridge forwarding and the actual execution kernel, whose release is recorded. It is not a VMware/Hyper-V/OVS deployment or physical-switch throughput benchmark. All three native net-tools guests reserve 512 MiB each, totaling 1536 MiB. No external service, production credential or Internet connector is required. Stop/wipe only your imported copy to reset.

Use licensed reference images for net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- SW eth1 <-> LEFT eth1
- SW eth2 <-> RIGHT eth1

| Node | Interface | Address |
| --- | --- | --- |
| SW | br0.99 | 198.18.1.1/29 |
| LEFT | eth1 / eth1.99 | 198.18.0.1/30 / 198.18.1.2/29 |
| RIGHT | eth1 / eth1.99 | 198.18.0.2/30 / 198.18.1.3/29 |

## Tasks

1. Inspect actual VLAN-aware bridge ports, forwarding state and dynamic MAC learning.
2. Isolate only the untagged data path while preserving a tagged control path on the same physical interfaces.
3. Recover both data directions and verify actual dynamic forwarding entries against independently observed peer MACs.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| LEFT | `python3 /lab/b.py good` | Three actual interface-bound tagged-VLAN99 control replies coexist with three actual untagged data replies. Both interface addresses must remain configured. |
| RIGHT | `python3 /lab/b.py good` | Three actual interface-bound tagged-VLAN99 control replies coexist with three actual untagged data replies. Both interface addresses must remain configured. |
| SW | `python3 /lab/b.py check` | Actual kernel VLAN filtering, both forwarding bridge ports, exact untagged data/PVID membership and retained tagged control membership agree. The observed execution kernel release is reported. |
| SW | `python3 /lab/b.py fdb` | Both actual peer MACs, independently observed through control-VLAN neighbors, are dynamically learned on the correct data VLAN and bridge ports; static/self/imported entries do not count. |

## Transition: move only RIGHT untagged traffic into VLAN20

On **SW**:

```ios
python3 /lab/b.py split
```

- LEFT: `python3 /lab/b.py isolated` -- Three actual interface-bound tagged-VLAN99 control replies coexist with zero actual untagged data replies. Both interface addresses must remain configured.
- RIGHT: `python3 /lab/b.py isolated` -- Three actual interface-bound tagged-VLAN99 control replies coexist with zero actual untagged data replies. Both interface addresses must remain configured.
- SW: `python3 /lab/b.py check` -- Actual kernel VLAN filtering, both forwarding bridge ports, exact untagged data/PVID membership and retained tagged control membership agree. The observed execution kernel release is reported.

## Transition: restore common data membership and dynamic forwarding

On **SW**:

```ios
python3 /lab/b.py restore
```

- LEFT: `python3 /lab/b.py good` -- Three actual interface-bound tagged-VLAN99 control replies coexist with three actual untagged data replies. Both interface addresses must remain configured.
- RIGHT: `python3 /lab/b.py good` -- Three actual interface-bound tagged-VLAN99 control replies coexist with three actual untagged data replies. Both interface addresses must remain configured.
- SW: `python3 /lab/b.py check` -- Actual kernel VLAN filtering, both forwarding bridge ports, exact untagged data/PVID membership and retained tagged control membership agree. The observed execution kernel release is reported.
- SW: `python3 /lab/b.py fdb` -- Both actual peer MACs, independently observed through control-VLAN neighbors, are dynamically learned on the correct data VLAN and bridge ports; static/self/imported entries do not count.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Readable implementation and direct observation

The [kernel bridge fixture and traffic probes](../../examples/virtualization/kernel_bridge.py) are embedded byte-for-byte. On SW inspect `ip -d link show br0`, `bridge vlan show`, `bridge link show`, `bridge fdb show br br0`, and `ip neigh show dev br0.99`. The scripted fault changes only eth2 untagged/PVID membership; VLAN99 remains tagged. The helper accepts either known actual membership state and refuses an unknown/leaking configuration. Manual changes outside those two states must be diagnosed and returned to the documented state before automated acceptance.

The [Linux kernel bridge documentation](https://www.kernel.org/doc/html/latest/networking/bridge.html) describes the software bridge and VLAN filtering context. These receipts cover the recorded reference image and execution kernel; they do not assert every kernel/runtime combination or vendor virtual-switch compatibility.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
