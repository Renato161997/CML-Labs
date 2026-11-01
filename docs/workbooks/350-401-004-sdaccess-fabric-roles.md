# Fabric Roles: Routed Underlay and VXLAN Overlay

## Scope and prerequisites

The overlay is an actual native Linux VXLAN tunnel, with two independent endpoint namespaces bridged through native VTEP namespaces. VTEP eth1 is the underlay interface and eth2 connects its local endpoint. Each VTEP bridges only eth2 and vx0 through br0; br0 has no data IP. LEFT 198.19.0.1/30 and RIGHT 198.19.0.2/30 share the overlay, while VTEP underlay addresses use distinct 198.18 benchmark space. Only declared point-to-point links exist; native management eth0 is unwired.

VXLAN starts at VNI100 with explicit local/remote unicast peers, UDP destination 4789 and outer TTL 64. The static classroom peer configuration uses no multicast group and is not EVPN, LISP or a proprietary controller. Small interface-bound IPv4 probes measure actual underlay and overlay behavior. Probe warm-up precedes each three-packet measurement. Actual device state, preserved endpoint addressing and both forwarding bridge ports accompany the packet controls.

Only VTEP2 changes to VNI101. Changing this immutable tunnel identifier recreates only its own vx0 bridge port with the same underlay, remote peer, UDP port and TTL. Underlay addressing/routes and both endpoint addresses remain unchanged. Both overlay directions must fail while both underlay directions retain three replies. A fresh packet-socket window on VTEP2 eth1 must nevertheless observe the expected VTEP1 UDP4789 packet carrying an actual selected inner LEFT-to-RIGHT ARP or echo request. Its decoded wire VNI100 must differ from actual receiver VNI101. After local VNI100 repair, fresh wire evidence, bidirectional overlay delivery and underlay controls must recover.

The capture worker belongs to this guest only, has an explicit PID/command identity and atomically acknowledges new evidence generations. It records bounded counters and decoded header facts, not arbitrary media or production traffic. Header/payload length bounds, the basic VXLAN I flag, peer addresses, inner request tuple and expected TTL are checked. This is the declared untagged small-packet scope, not a general traffic decoder, fragmentation/MTU test, encryption/authentication mechanism or performance benchmark. Native images share their execution kernel; actual kernel release is recorded. No external connector, Internet service or production credentials are required. Stop/wipe only your imported copy to reset.

VTEP1 underlay 198.18.0.1/30 reaches the SPINE 198.18.0.2/30; SPINE 198.18.1.1/30 reaches VTEP2 198.18.1.2/30. Each VTEP has only the explicit peer-subnet route through its connected SPINE next hop. The actual IOL-XE router forwards the VXLAN UDP transport and must decrement outer TTL 64 to observed TTL 63, while endpoints still share their unchanged inner subnet. This demonstrates routed-underlay, VTEP and endpoint roles, not a Cisco SDA deployment, LISP/EVPN control plane, identity policy or vendor controller API.

Use licensed reference images for iol-xe, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- LEFT eth1 <-> VTEP1 eth2
- RIGHT eth1 <-> VTEP2 eth2
- VTEP1 eth1 <-> SPINE Ethernet0/0
- VTEP2 eth1 <-> SPINE Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| VTEP1 | eth1 underlay | 198.18.0.1/30 |
| VTEP2 | eth1 underlay | 198.18.1.2/30 |
| LEFT | eth1 overlay | 198.19.0.1/30 |
| RIGHT | eth1 overlay | 198.19.0.2/30 |
| VTEP1 / VTEP2 | br0: eth2 + vx0 | No data IP; bridge only |
| SPINE | Ethernet0/0 | `ip address 198.18.0.2 255.255.255.252` |
| SPINE | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |

## Tasks

1. Separate actual underlay transport from bridged overlay addressing and delivery.
2. Decode expected-peer VXLAN VNI/TTL and selected inner request fields from a fresh real wire window.
3. Break only receiver VNI, retain underlay controls, and recover actual bidirectional overlay traffic.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| VTEP1 | `python3 /lab/v.py underlay` | Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up. |
| VTEP2 | `python3 /lab/v.py underlay` | Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up. |
| VTEP1 | `python3 /lab/v.py state` | Actual kernel VXLAN identifier, local/remote addresses, UDP4789, TTL64, route next hop and forwarding bridge ports agree; the execution kernel is recorded. |
| VTEP2 | `python3 /lab/v.py state` | Actual kernel VXLAN identifier, local/remote addresses, UDP4789, TTL64, route next hop and forwarding bridge ports agree; the execution kernel is recorded. |

## Transition: start a fresh baseline wire window

On **VTEP2**:

```ios
python3 /lab/v.py capture
```

- VTEP1: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.
- VTEP2: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.
- VTEP1: `python3 /lab/v.py state` -- Actual kernel VXLAN identifier, local/remote addresses, UDP4789, TTL64, route next hop and forwarding bridge ports agree; the execution kernel is recorded.
- VTEP2: `python3 /lab/v.py state` -- Actual kernel VXLAN identifier, local/remote addresses, UDP4789, TTL64, route next hop and forwarding bridge ports agree; the execution kernel is recorded.

## Transition: prove baseline overlay delivery and actual encapsulation

On **LEFT**:

```ios
python3 /lab/v.py good
```

- RIGHT: `python3 /lab/v.py good` -- Three actual interface-bound overlay probes succeed.
- VTEP2: `python3 /lab/v.py wire-good` -- A fresh acknowledged packet-socket window observes actual expected-peer UDP4789 VXLAN with the selected inner ARP/echo request; the wire VNI and TTL are decoded independently of actual receiver VNI state.
- VTEP1: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.
- VTEP2: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.

## Transition: change only the receiver VNI

On **VTEP2**:

```ios
python3 /lab/v.py mismatch
```

- VTEP1: `python3 /lab/v.py state` -- Actual kernel VXLAN identifier, local/remote addresses, UDP4789, TTL64, route next hop and forwarding bridge ports agree; the execution kernel is recorded.
- VTEP2: `python3 /lab/v.py state` -- Actual kernel VXLAN identifier, local/remote addresses, UDP4789, TTL64, route next hop and forwarding bridge ports agree; the execution kernel is recorded.
- VTEP1: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.
- VTEP2: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.

## Transition: start a fresh mismatch wire window

On **VTEP2**:

```ios
python3 /lab/v.py capture
```

- VTEP2: `python3 /lab/v.py state` -- Actual kernel VXLAN identifier, local/remote addresses, UDP4789, TTL64, route next hop and forwarding bridge ports agree; the execution kernel is recorded.
- VTEP1: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.
- VTEP2: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.

## Transition: observe wire VNI mismatch with healthy underlay

On **LEFT**:

```ios
python3 /lab/v.py down
```

- RIGHT: `python3 /lab/v.py down` -- Three actual interface-bound overlay probes fail while both endpoint addressing and underlay controls remain intact.
- VTEP2: `python3 /lab/v.py wire-mismatch` -- A fresh acknowledged packet-socket window observes actual expected-peer UDP4789 VXLAN with the selected inner ARP/echo request; the wire VNI and TTL are decoded independently of actual receiver VNI state.
- VTEP1: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.
- VTEP2: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.

## Transition: restore the original receiver VNI

On **VTEP2**:

```ios
python3 /lab/v.py repair
```

- VTEP1: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.
- VTEP2: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.
- VTEP1: `python3 /lab/v.py state` -- Actual kernel VXLAN identifier, local/remote addresses, UDP4789, TTL64, route next hop and forwarding bridge ports agree; the execution kernel is recorded.
- VTEP2: `python3 /lab/v.py state` -- Actual kernel VXLAN identifier, local/remote addresses, UDP4789, TTL64, route next hop and forwarding bridge ports agree; the execution kernel is recorded.

## Transition: start a fresh recovered wire window

On **VTEP2**:

```ios
python3 /lab/v.py capture
```

- VTEP1: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.
- VTEP2: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.
- VTEP1: `python3 /lab/v.py state` -- Actual kernel VXLAN identifier, local/remote addresses, UDP4789, TTL64, route next hop and forwarding bridge ports agree; the execution kernel is recorded.
- VTEP2: `python3 /lab/v.py state` -- Actual kernel VXLAN identifier, local/remote addresses, UDP4789, TTL64, route next hop and forwarding bridge ports agree; the execution kernel is recorded.

## Transition: verify actual overlay and wire recovery

On **LEFT**:

```ios
python3 /lab/v.py good
```

- RIGHT: `python3 /lab/v.py good` -- Three actual interface-bound overlay probes succeed.
- VTEP2: `python3 /lab/v.py wire-good` -- A fresh acknowledged packet-socket window observes actual expected-peer UDP4789 VXLAN with the selected inner ARP/echo request; the wire VNI and TTL are decoded independently of actual receiver VNI state.
- VTEP1: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.
- VTEP2: `python3 /lab/v.py underlay` -- Actual interface-bound underlay traffic reaches the declared peer through the expected direct or routed next hop while the configured tunnel and bridge ports remain up.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Readable dataplane implementation

The [VXLAN fixture, packet decoder and probes](../../examples/virtualization/vxlan_probe.py) are embedded byte-for-byte. Inspect `ip -d link show vx0`, `bridge link show`, `bridge fdb show dev vx0`, and `ip route` on each VTEP. Capture files and the explicitly owned worker remain under `/lab` in VTEP2 and disappear with its imported copy. An acknowledged new generation prevents historical totals from replacing fresh wire evidence.

[RFC7348](https://www.rfc-editor.org/rfc/rfc7348) describes VXLAN encapsulation and its context. Actual route selection, bridge port state, bound packet outcomes and decoded wire fields are separate controls. VNI is a forwarding namespace identifier, not cryptographic authentication. Scope and exact image/kernel observations govern the result; proprietary fabric-control and vendor-product compatibility are not inferred.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
