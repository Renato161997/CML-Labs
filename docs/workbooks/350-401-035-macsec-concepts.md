# MACsec: Kernel Encryption, Wrong-Key Drops and Recovery

## Scope and prerequisites

Two native net-tools endpoints use the actual Linux kernel MACsec SecY, not a simulated API. Only eth1 is wired. LEFT and RIGHT plain underlay addresses are 198.18.0.1/30 and 198.18.0.2/30; macsec0 protected endpoints are 198.19.0.1/30 and 198.19.0.2/30. The software configuration requires GCM-AES-128, 16-byte ICV, encryption/protection, explicit SCI, strict validation and replay protection with window 0. The native model shares its execution kernel; the exact kernel release is recorded with observations. This is not a Cisco ASIC, physical offload or MKA exercise.

This isolated two-endpoint classroom uses public known teaching keys and benign benchmark packets. It makes no confidentiality or authenticated peer-discovery claim for real data. Each fresh configuration chooses a new random locally administered data MAC and hence SCI; the two controlled peers learn SCI from actual encrypted ARP frames on their exclusive point-to-point link before installing their manual receive associations. This controlled classroom provisioning is not production key management. A repeat configuration must retain existing security associations. The helper refuses unknown preexisting SecY state; stop and wipe only the imported pair to reset a failed experiment. Fresh SCI reduces accidental reuse between copies, while production use requires fresh secret keys and an appropriate key-management protocol. Never reuse a key/IV combination.

SA0 uses matching keys in both directions, with distinct endpoint SCIs. LEFT additionally has a deliberately wrong-key TX SA1; RIGHT has a differently keyed expected RX SA1. The fault changes only LEFT encoding_sa from 0 to 1. It must not recreate SA0, reset its packet number, remove addresses or break the underlay. RIGHT must see three failed protected requests, at least three fresh encrypted wire frames for the actual peer SCI and AN1, and an increase of at least three RX SA1 InPktsNotValid events. Both plain underlay directions remain healthy. Repair selects the retained SA0 and must recover three protected replies, fresh peer AN0 frames and RX SA0 InPktsOK deltas. Every phase checks strict state and monotonic SA0 packet numbers. Wire parsing observes headers and lengths; kernel counters and actual packet behavior establish the cryptographic outcome, rather than treating header inspection as tag verification. Counters use fresh before/after windows, not historical totals. Nominal RAM is 1024 MiB for two 512 MiB native endpoints.

Use licensed reference images for net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- LEFT eth1 <-> RIGHT eth1

| Node | Interface | Address |
| --- | --- | --- |
| LEFT | macsec0 | 198.19.0.1/30 |
| RIGHT | macsec0 | 198.19.0.2/30 |
| LEFT | eth1 | `198.18.0.1/30` |
| RIGHT | eth1 | `198.18.0.2/30` |

## Tasks

1. Inspect real software SecY state, encrypted Ethernet frames and authenticated receive counters.
2. Select a differently keyed transmit association without changing the data path or resetting SA0 packet numbers.
3. Observe actual wrong-key rejection with healthy plain controls, then restore the retained valid association and real traffic.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| LEFT | `python3 /lab/m.py check` | Actual software SecY configuration, endpoint addresses, selected encoding association, monotonic SA0 packet number and three plain underlay control replies agree. |
| RIGHT | `python3 /lab/m.py check` | Actual software SecY configuration, endpoint addresses, selected encoding association, monotonic SA0 packet number and three plain underlay control replies agree. |
| RIGHT | `python3 /lab/m.py measure` | Fresh expected-peer EtherType88e5 encrypted frames and receive-association counter deltas must accompany three actual protected replies. |

## Transition: select the deliberately incorrect transmit key association

On **LEFT**:

```ios
python3 /lab/m.py select --encoding 1
```

- LEFT: `python3 /lab/m.py check --encoding 1` -- Actual software SecY configuration, endpoint addresses, selected encoding association, monotonic SA0 packet number and three plain underlay control replies agree.
- RIGHT: `python3 /lab/m.py check` -- Actual software SecY configuration, endpoint addresses, selected encoding association, monotonic SA0 packet number and three plain underlay control replies agree.
- RIGHT: `python3 /lab/m.py measure --expect down` -- Fresh expected-peer EtherType88e5 encrypted frames and receive-association counter deltas must accompany zero protected replies under the deliberately incorrect transmit key.

## Transition: restore retained valid SA0 without resetting packet numbers

On **LEFT**:

```ios
python3 /lab/m.py select --encoding 0
```

- LEFT: `python3 /lab/m.py check` -- Actual software SecY configuration, endpoint addresses, selected encoding association, monotonic SA0 packet number and three plain underlay control replies agree.
- RIGHT: `python3 /lab/m.py check` -- Actual software SecY configuration, endpoint addresses, selected encoding association, monotonic SA0 packet number and three plain underlay control replies agree.
- RIGHT: `python3 /lab/m.py measure` -- Fresh expected-peer EtherType88e5 encrypted frames and receive-association counter deltas must accompany three actual protected replies.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Readable implementation and reset boundary

The checked-in [MACsec fixture](../../examples/security/macsec_probe.py) is embedded byte-for-byte. The asynchronous owned provisioning worker keeps console bootstrap separate from paired SCI learning. Its log and PID remain under `/lab`; acceptance waits for atomic state completion. Repeating provisioning never reinitializes an existing valid association. Wipe only the imported pair to reset this controlled classroom experiment.

The [ip-macsec manual](https://man7.org/linux/man-pages/man8/ip-macsec.8.html) describes secure channels/associations and warns against key/IV reuse. The [iproute2 implementation](https://github.com/iproute2/iproute2/blob/main/ip/ipmacsec.c) defines the observed counter fields. This exercise uses publicly disclosed teaching keys and controlled peer-SCI learning; it does not supply secret key distribution, MKA or production peer authentication. Real protected data belongs on a separately engineered deployment.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
