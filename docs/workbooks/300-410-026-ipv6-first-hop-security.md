# IPv6 First-Hop Security: RA Guard and Recovery

## Scope and prerequisites

One native three-port software frame guard connects a trusted router, an untrusted advertiser and a separate Ubuntu client. GUARD eth1 is trusted, eth2 connects CLIENT ens2, and eth3 connects ROGUE ens2. The advertisers are actual Ubuntu router VMs with guest IPv6 forwarding enabled, so their kernel Neighbor Advertisements retain router status. RAs carry a 1800-second lifetime to cover manual and serial-console observation windows. Only the three specified point-to-point links exist; management eth0 is unwired. All endpoint IPv6 addresses belong to 2001:db8:1::/64: ROUTER ::1, CLIENT ::2, ROGUE ::66. Explicit link-local addresses are fe80::1, fe80::2 and fe80::66. The client kernel is configured to process router advertisements and router preferences. Both advertisers send actual checksum-valid ICMPv6 RAs with Hop Limit 255 and a source-link-layer option matching their Ethernet source. The trusted router has medium preference; the rogue has high preference.

The guard actually receives and forwards Ethernet frames through packet sockets, learns source locations and filters RAs by incoming port and declared trusted link-local source. It does not stand in for a Cisco switch ASIC. The bounded IPv6 parser walks up to four supported extension headers, validates RA checksum/code/link-local scope/options and rejects fragments, opaque headers and tagged frames outside this untagged exercise. The tested rogue RA includes a real Hop-by-Hop header, so fixed-offset ICMP inspection cannot establish protection. Ordinary IPv6 data and neighbor discovery between all endpoint ports must remain functional.

Acceptance first installs the actual trusted kernel default route. Fresh untrusted extension-bearing RAs must be observed and blocked while a real route lookup still selects fe80::1 and no rogue default exists. Withdrawing only the guard policy must forward those packets: the actual client kernel must install the rogue RA route and select fe80::66 because of its higher preference. Re-enabling the guard does not erase previously learned routing state. Recovery therefore removes only the observed rogue RA default on the owned client, verifies the trusted gateway, and repeats the rogue transmission to prove no reinstatement. The lookup target 2001:db8:ffff::1 is never contacted; no Internet forwarding through either advertiser is claimed. Actual connected IPv6 ping controls remain healthy throughout. Nominal RAM is 6656 MiB (one 512 MiB native guard and three 2048 MiB Ubuntu VMs). This is a specific RA-guard and routing-state lesson, not general IPv6 first-hop, SEND, DHCPv6 or vendor-platform certification.

Use licensed reference images for net-tools, ubuntu in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- GUARD eth1 <-> ROUTER ens2
- GUARD eth2 <-> CLIENT ens2
- GUARD eth3 <-> ROGUE ens2

| Node | Interface | Address |
| --- | --- | --- |
| ROUTER | ens2 | 2001:db8:1::1/64, fe80::1/64 |
| CLIENT | ens2 | 2001:db8:1::2/64, fe80::2/64 |
| ROGUE | ens2 | 2001:db8:1::66/64, fe80::66/64 |
| GUARD | eth1 / eth2 / eth3 | Transparent software ports; no data IP endpoint |

## Tasks

1. Correlate actual trusted/untrusted Ethernet RA traffic, extension-header parsing and real client kernel route selection.
2. Withdraw only ingress RA policy and observe a higher-preference rogue default while connected data forwarding remains healthy.
3. Restore the guard, explicitly remove the previously learned rogue route and prove new untrusted RAs cannot reinstall it.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| CLIENT | `python3 /lab/f.py health` | Actual IPv6 echo traffic reaches both the trusted advertiser and untrusted advertiser; the guard must not simply disable the untrusted data port. |

## Transition: advertise the trusted default router

On **ROUTER**:

```ios
python3 /lab/f.py advertise
```

- CLIENT: `python3 /lab/f.py trusted` -- An actual Linux IPv6 route lookup outside the connected prefix selects the trusted gateway. Trusted acceptance also requires no retained rogue default route.
- CLIENT: `python3 /lab/f.py health` -- Actual IPv6 echo traffic reaches both the trusted advertiser and untrusted advertiser; the guard must not simply disable the untrusted data port.

## Transition: start a fresh guard evidence window

On **GUARD**:

```ios
python3 /lab/f.py reset
```

- CLIENT: `python3 /lab/f.py trusted` -- An actual Linux IPv6 route lookup outside the connected prefix selects the trusted gateway. Trusted acceptance also requires no retained rogue default route.

## Transition: send the untrusted RA behind a Hop-by-Hop header

On **ROGUE**:

```ios
python3 /lab/f.py advertise --extension
```

- GUARD: `python3 /lab/f.py blocked` -- Fresh-generation guard counters observe at least five actual extension-bearing RAs and the declared block/forward decision.
- CLIENT: `python3 /lab/f.py trusted` -- An actual Linux IPv6 route lookup outside the connected prefix selects the trusted gateway. Trusted acceptance also requires no retained rogue default route.
- CLIENT: `python3 /lab/f.py health` -- Actual IPv6 echo traffic reaches both the trusted advertiser and untrusted advertiser; the guard must not simply disable the untrusted data port.

## Transition: withdraw only RA filtering

On **GUARD**:

```ios
python3 /lab/f.py policy-off
```

- CLIENT: `python3 /lab/f.py trusted` -- An actual Linux IPv6 route lookup outside the connected prefix selects the trusted gateway. Trusted acceptance also requires no retained rogue default route.

## Transition: observe actual rogue-route installation and selection

On **ROGUE**:

```ios
python3 /lab/f.py advertise --extension
```

- GUARD: `python3 /lab/f.py forwarded` -- Fresh-generation guard counters observe at least five actual extension-bearing RAs and the declared block/forward decision.
- CLIENT: `python3 /lab/f.py rogue` -- An actual Linux IPv6 route lookup outside the connected prefix selects the rogue gateway. Trusted acceptance also requires no retained rogue default route.
- CLIENT: `python3 /lab/f.py health` -- Actual IPv6 echo traffic reaches both the trusted advertiser and untrusted advertiser; the guard must not simply disable the untrusted data port.

## Transition: restore filtering before clearing learned state

On **GUARD**:

```ios
python3 /lab/f.py policy-on
```

- CLIENT: `python3 /lab/f.py health` -- Actual IPv6 echo traffic reaches both the trusted advertiser and untrusted advertiser; the guard must not simply disable the untrusted data port.

## Transition: remove only the previously learned rogue RA route

On **CLIENT**:

```ios
python3 /lab/f.py recover
```

- CLIENT: `python3 /lab/f.py trusted` -- An actual Linux IPv6 route lookup outside the connected prefix selects the trusted gateway. Trusted acceptance also requires no retained rogue default route.
- CLIENT: `python3 /lab/f.py health` -- Actual IPv6 echo traffic reaches both the trusted advertiser and untrusted advertiser; the guard must not simply disable the untrusted data port.

## Transition: prove fresh untrusted advertisements stay blocked

On **ROGUE**:

```ios
python3 /lab/f.py advertise --extension
```

- GUARD: `python3 /lab/f.py blocked` -- Fresh-generation guard counters observe at least five actual extension-bearing RAs and the declared block/forward decision.
- CLIENT: `python3 /lab/f.py trusted` -- An actual Linux IPv6 route lookup outside the connected prefix selects the trusted gateway. Trusted acceptance also requires no retained rogue default route.
- CLIENT: `python3 /lab/f.py health` -- Actual IPv6 echo traffic reaches both the trusted advertiser and untrusted advertiser; the guard must not simply disable the untrusted data port.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Readable implementation and protocol references

The [frame guard and kernel-route probes](../../examples/security/ra_guard.py) are embedded byte-for-byte. The own guard worker is separate from the serial console; its counters and log stay under `/lab`. Policy generations isolate fresh evidence windows. Reset by stopping/wiping only the imported copy.

[RFC7113](https://www.rfc-editor.org/rfc/rfc7113) describes extension-header considerations for RA guard. [RFC6980](https://www.rfc-editor.org/rfc/rfc6980) addresses fragmented Neighbor Discovery. [RFC4861](https://www.rfc-editor.org/rfc/rfc4861) defines the RA validity and neighbor-discovery context. The fixture has its explicitly bounded parser and untagged lab scope; its fresh CML receipts establish the exact tested behavior.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

### Reproduce the explicit RAM reservation

Replace the example URL with your own certificate-verified CML endpoint. The password is prompted locally; do not put it in command history. This single 6656 MiB exercise needs at least twice that reservation free.

```bash
python scripts/cml_smoke.py --url https://cml.example.test --phase functional --console websocket --lab 026-ipv6-first-hop-security --max-lab-ram-mib 6656
```
