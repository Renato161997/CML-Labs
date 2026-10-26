# Syslog SIEM Correlation

## Scope and prerequisites

This vendor-neutral SIEM exercise uses a small inspectable Python collector/correlator on native net-tools, rather than claiming a live commercial SIEM integration. Real traffic causes the IOL-XE ACL log; a real administrative change causes the spare Loopback1 event. The decoder groups by observed UDP source and compares collector monotonic receive times, avoiding assumptions about the router clock. A temporal pair is investigation evidence, not proof of an attack or causal relation. The single-event-family phase is an explicit negative control. UDP sender identity is not authenticated. The collector binds only its benchmark data interface; all archives are disposable lab files and remain until wipe.

Use licensed reference images for iol-xe, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> TOOLS eth1
- R1 Ethernet0/1 <-> LOG eth1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Loopback0 | `ip address 192.0.2.1 255.255.255.255` |
| R1 | Loopback1 | `ip address 192.0.2.99 255.255.255.255` |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| TOOLS | eth1 | `198.18.0.2/30` |
| LOG | eth1 | `198.18.1.2/30` |

## Tasks

1. Collect actual router UDP syslog into a receiver-owned JSONL archive.
2. Generate an ingress ACL denial and verify that one event family alone is not a correlated incident.
3. Administratively disable a spare interface and pair the two real event families within a bounded receive-time window.
4. Restore forwarding and interface state while retaining the historical evidence.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.1.2 repeat 3` | The collector data path and neighbor resolution are ready before emitting security events. |
| LOG | `python3 /lab/correlate.py baseline` | The receive-time correlator validates the baseline event-family condition. |
| TOOLS | `LC_ALL=C ping -c 3 -W 1 192.0.2.1` | All three packets reach the routed endpoint. |
| R1 | `show ip interface brief` | The spare loopback is operational. |

## Transition: apply a logging ingress filter

On **R1**:

```ios
configure terminal
ip access-list extended CML-DENY
deny icmp host 198.18.0.2 host 192.0.2.1 log
permit ip any any
exit
interface Ethernet0/0
ip access-group CML-DENY in
end
```

- TOOLS: `LC_ALL=C ping -c 3 -W 1 192.0.2.1` -- All three packets are blocked by the router ingress ACL.
- R1: `show access-lists CML-DENY` -- The deny counts actual client probes.
- LOG: `python3 /lab/correlate.py single` -- The receive-time correlator validates the single event-family condition.

## Transition: disable only the spare interface

On **R1**:

```ios
configure terminal
interface Loopback1
shutdown
end
```

- R1: `show ip interface brief` -- The spare loopback is administratively disabled.
- LOG: `python3 /lab/correlate.py incident` -- The receive-time correlator validates the incident event-family condition.

## Transition: restore forwarding and spare interface

On **R1**:

```ios
configure terminal
interface Ethernet0/0
no ip access-group CML-DENY in
exit
interface Loopback1
no shutdown
end
```

- TOOLS: `LC_ALL=C ping -c 3 -W 1 192.0.2.1` -- All three packets reach the routed endpoint.
- R1: `show ip interface brief` -- The spare loopback is operational.
- LOG: `python3 /lab/correlate.py incident` -- The receive-time correlator validates the incident event-family condition.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

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
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
 no shutdown
 exit
interface Loopback1
 ip address 192.0.2.99 255.255.255.255
 no shutdown
 exit
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
logging on
logging buffered 32768 informational
logging trap informational
logging source-interface Ethernet0/1
logging host 198.18.1.2 transport udp port 514
end
```

### TOOLS: boot.sh

```bash
#!/bin/bash
set -eu
ip address add 198.18.0.2/30 dev eth1
ip link set eth1 up
ip route add 192.0.2.1/32 via 198.18.0.1 dev eth1
mkdir -p /lab
echo READY >/dev/console
exit 0
```

### LOG: boot.sh

```bash
#!/bin/bash
set -eu
ip address add 198.18.1.2/30 dev eth1
ip link set eth1 up
mkdir -p /lab
base64 -d > /lab/syslog_receiver.py <<'CML_EMBED_EXAMPLES_VISIBILITY_SYSLOG_RECEIVER_PY'
IiIiSXNvbGF0ZWQgVURQIGNvbGxlY3RvcjsgcmVjb3JkcyByZWNlaXZlIHRpbWUgYW5kIHNvdXJj
ZSB3aXRob3V0IHRydXN0aW5nIGhlYWRlcnMuIiIiCgppbXBvcnQganNvbgppbXBvcnQgc29ja2V0
CmltcG9ydCB0aW1lCmZyb20gZGF0ZXRpbWUgaW1wb3J0IFVUQywgZGF0ZXRpbWUKZnJvbSBwYXRo
bGliIGltcG9ydCBQYXRoCgoKZGVmIG1haW4oKToKICAgIGNvbmZpZyA9IGpzb24ubG9hZHMoUGF0
aCgiL2xhYi9zeXNsb2cuanNvbiIpLnJlYWRfdGV4dChlbmNvZGluZz0idXRmLTgiKSkKICAgIHdp
dGggc29ja2V0LnNvY2tldChzb2NrZXQuQUZfSU5FVCwgc29ja2V0LlNPQ0tfREdSQU0pIGFzIHNl
cnZlcjoKICAgICAgICBzZXJ2ZXIuYmluZCgoY29uZmlnWyJiaW5kIl0sIDUxNCkpCiAgICAgICAg
d2l0aCBQYXRoKCIvbGFiL2V2ZW50cy5qc29ubCIpLm9wZW4oImEiLCBlbmNvZGluZz0idXRmLTgi
LCBidWZmZXJpbmc9MSkgYXMgbG9nOgogICAgICAgICAgICBQYXRoKCIvbGFiL3JlY2VpdmVyLXJl
YWR5Iikud3JpdGVfdGV4dCgiQk9VTkRcbiIsIGVuY29kaW5nPSJ1dGYtOCIpCiAgICAgICAgICAg
IHdoaWxlIFRydWU6CiAgICAgICAgICAgICAgICBkYXRhLCBzZW5kZXIgPSBzZXJ2ZXIucmVjdmZy
b20oODE5MykKICAgICAgICAgICAgICAgIGxvZy53cml0ZSgKICAgICAgICAgICAgICAgICAgICBq
c29uLmR1bXBzKAogICAgICAgICAgICAgICAgICAgICAgICB7CiAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAic291cmNlIjogc2VuZGVyWzBdLAogICAgICAgICAgICAgICAgICAgICAgICAgICAg
InJlY2VpdmVkX21vbm90b25pYyI6IHRpbWUubW9ub3RvbmljKCksCiAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAicmVjZWl2ZWRfdXRjIjogZGF0ZXRpbWUubm93KFVUQykuaXNvZm9ybWF0KCks
CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAidHJ1bmNhdGVkIjogbGVuKGRhdGEpID4gODE5
MiwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICJtZXNzYWdlIjogZGF0YS5kZWNvZGUoInV0
Zi04IiwgZXJyb3JzPSJyZXBsYWNlIikuc3RyaXAoKSwKICAgICAgICAgICAgICAgICAgICAgICAg
fSwKICAgICAgICAgICAgICAgICAgICAgICAgZW5zdXJlX2FzY2lpPVRydWUsCiAgICAgICAgICAg
ICAgICAgICAgKQogICAgICAgICAgICAgICAgICAgICsgIlxuIgogICAgICAgICAgICAgICAgKQoK
CmlmIF9fbmFtZV9fID09ICJfX21haW5fXyI6CiAgICBtYWluKCkK
CML_EMBED_EXAMPLES_VISIBILITY_SYSLOG_RECEIVER_PY
base64 -d > /lab/correlate.py <<'CML_EMBED_EXAMPLES_VISIBILITY_CORRELATE_PY'
IiIiQ29ycmVsYXRlIHJlYWwgbGFiIEFDTCBhbmQgaW50ZXJmYWNlIGV2ZW50czsgdGVtcG9yYWwg
cGFpcmluZyBpcyBub3QgY2F1c2FsaXR5LiIiIgoKaW1wb3J0IGFyZ3BhcnNlCmltcG9ydCBqc29u
CmltcG9ydCByZQppbXBvcnQgc3lzCmZyb20gcGF0aGxpYiBpbXBvcnQgUGF0aAoKCmRlZiBjb3Jy
ZWxhdGUoZXZlbnRzLCBzb3VyY2UsIHdpbmRvdz0xMjApOgogICAgZmFtaWxpZXMgPSB7InBhY2tl
dF9kZW5pZWQiOiBbXSwgImludGVyZmFjZV9kaXNhYmxlZCI6IFtdfQogICAgZm9yIGV2ZW50IGlu
IGV2ZW50czoKICAgICAgICBpZiBldmVudC5nZXQoInNvdXJjZSIpICE9IHNvdXJjZSBvciBldmVu
dC5nZXQoInRydW5jYXRlZCIpOgogICAgICAgICAgICBjb250aW51ZQogICAgICAgIG1lc3NhZ2Ug
PSBldmVudFsibWVzc2FnZSJdCiAgICAgICAgc3RhbXAgPSBldmVudFsicmVjZWl2ZWRfbW9ub3Rv
bmljIl0KICAgICAgICBpZiBub3QgaXNpbnN0YW5jZShzdGFtcCwgKGZsb2F0LCBpbnQpKSBvciBu
b3QgaXNpbnN0YW5jZShtZXNzYWdlLCBzdHIpOgogICAgICAgICAgICByYWlzZSBUeXBlRXJyb3Io
IkludmFsaWQgY29sbGVjdG9yIHJlY29yZCIpCiAgICAgICAgaWYgcmUuc2VhcmNoKHIiSVBBQ0NF
U1NMT0cuKkNNTC1ERU5ZLipkZW5pZWRccytpY21wIiwgbWVzc2FnZSwgcmUuSUdOT1JFQ0FTRSk6
CiAgICAgICAgICAgIGZhbWlsaWVzWyJwYWNrZXRfZGVuaWVkIl0uYXBwZW5kKGV2ZW50KQogICAg
ICAgIGlmIHJlLnNlYXJjaChyIiVMSU5LLVxkLS4qTG9vcGJhY2sxLiphZG1pbmlzdHJhdGl2ZWx5
IGRvd24iLCBtZXNzYWdlLCByZS5JR05PUkVDQVNFKToKICAgICAgICAgICAgZmFtaWxpZXNbImlu
dGVyZmFjZV9kaXNhYmxlZCJdLmFwcGVuZChldmVudCkKICAgIHBhaXJzID0gWwogICAgICAgIHsi
cGFja2V0X2RlbmllZCI6IGEsICJpbnRlcmZhY2VfZGlzYWJsZWQiOiBifQogICAgICAgIGZvciBh
IGluIGZhbWlsaWVzWyJwYWNrZXRfZGVuaWVkIl0KICAgICAgICBmb3IgYiBpbiBmYW1pbGllc1si
aW50ZXJmYWNlX2Rpc2FibGVkIl0KICAgICAgICBpZiBhYnMoYVsicmVjZWl2ZWRfbW9ub3Rvbmlj
Il0gLSBiWyJyZWNlaXZlZF9tb25vdG9uaWMiXSkgPD0gd2luZG93CiAgICBdCiAgICByZXR1cm4g
ewogICAgICAgICJzb3VyY2UiOiBzb3VyY2UsCiAgICAgICAgIndpbmRvd19zZWNvbmRzIjogd2lu
ZG93LAogICAgICAgICJldmVudF9jb3VudHMiOiB7bmFtZTogbGVuKHJvd3MpIGZvciBuYW1lLCBy
b3dzIGluIGZhbWlsaWVzLml0ZW1zKCl9LAogICAgICAgICJjb3JyZWxhdGlvbnMiOiBwYWlyc1s6
NF0sCiAgICAgICAgImNvcnJlbGF0aW9uX2NvdW50IjogbGVuKHBhaXJzKSwKICAgIH0KCgpkZWYg
bWFpbigpOgogICAgcGFyc2VyID0gYXJncGFyc2UuQXJndW1lbnRQYXJzZXIoZGVzY3JpcHRpb249
X19kb2NfXykKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIm1vZGUiLCBjaG9pY2VzPSgiYmFzZWxp
bmUiLCAic2luZ2xlIiwgImluY2lkZW50IikpCiAgICBhcmdzID0gcGFyc2VyLnBhcnNlX2FyZ3Mo
KQogICAgdHJ5OgogICAgICAgIGlmIG5vdCBQYXRoKCIvbGFiL3JlY2VpdmVyLXJlYWR5IikuZXhp
c3RzKCk6CiAgICAgICAgICAgIHJhaXNlIFJ1bnRpbWVFcnJvcigiQ29sbGVjdG9yIGhhcyBub3Qg
Ym91bmQgaXRzIFVEUCBsaXN0ZW5lciIpCiAgICAgICAgZXZlbnRzID0gWwogICAgICAgICAgICBq
c29uLmxvYWRzKGxpbmUpCiAgICAgICAgICAgIGZvciBsaW5lIGluIFBhdGgoIi9sYWIvZXZlbnRz
Lmpzb25sIikucmVhZF90ZXh0KGVuY29kaW5nPSJ1dGYtOCIpLnNwbGl0bGluZXMoKQogICAgICAg
IF0KICAgICAgICByZXBvcnQgPSBjb3JyZWxhdGUoZXZlbnRzLCAiMTk4LjE4LjEuMSIpCiAgICAg
ICAgY291bnRzID0gcmVwb3J0WyJldmVudF9jb3VudHMiXQogICAgICAgIGlmIGFyZ3MubW9kZSA9
PSAiYmFzZWxpbmUiIGFuZCAoY291bnRzWyJwYWNrZXRfZGVuaWVkIl0gb3IgY291bnRzWyJpbnRl
cmZhY2VfZGlzYWJsZWQiXSk6CiAgICAgICAgICAgIHJhaXNlIFJ1bnRpbWVFcnJvcigiVW5leHBl
Y3RlZCBpbml0aWFsIGV2ZW50IGZhbWlsaWVzIikKICAgICAgICBpZiBhcmdzLm1vZGUgPT0gInNp
bmdsZSIgYW5kICgKICAgICAgICAgICAgbm90IGNvdW50c1sicGFja2V0X2RlbmllZCJdCiAgICAg
ICAgICAgIG9yIGNvdW50c1siaW50ZXJmYWNlX2Rpc2FibGVkIl0KICAgICAgICAgICAgb3IgcmVw
b3J0WyJjb3JyZWxhdGlvbl9jb3VudCJdCiAgICAgICAgKToKICAgICAgICAgICAgcmFpc2UgUnVu
dGltZUVycm9yKCJTaW5nbGUtZmFtaWx5IG5lZ2F0aXZlIGNvbnRyb2wgZmFpbGVkIikKICAgICAg
ICBpZiBhcmdzLm1vZGUgPT0gImluY2lkZW50IiBhbmQgbm90IHJlcG9ydFsiY29ycmVsYXRpb25f
Y291bnQiXToKICAgICAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCJCb3RoIGFjdHVhbCBldmVu
dCBmYW1pbGllcyBhcmUgcmVxdWlyZWQgaW4gdGhlIHJlY2VpdmUgd2luZG93IikKICAgICAgICBy
ZXBvcnQudXBkYXRlKHN0YXR1cz0icGFzc2VkIiwgbW9kZT1hcmdzLm1vZGUpCiAgICAgICAgcHJp
bnQoanNvbi5kdW1wcyhyZXBvcnQsIHNvcnRfa2V5cz1UcnVlKSkKICAgICAgICByZXR1cm4gMAog
ICAgZXhjZXB0IChPU0Vycm9yLCBWYWx1ZUVycm9yLCBUeXBlRXJyb3IsIFJ1bnRpbWVFcnJvciwg
S2V5RXJyb3IpIGFzIGV4YzoKICAgICAgICBwcmludChqc29uLmR1bXBzKHsic3RhdHVzIjogImZh
aWxlZCIsICJlcnJvciI6IHN0cihleGMpfSkpCiAgICAgICAgcmV0dXJuIDEKCgppZiBfX25hbWVf
XyA9PSAiX19tYWluX18iOgogICAgc3lzLmV4aXQobWFpbigpKQo=
CML_EMBED_EXAMPLES_VISIBILITY_CORRELATE_PY
echo '{"bind":"198.18.1.2"}' > /lab/syslog.json
python3 /lab/syslog_receiver.py >/lab/receiver.log 2>&1 &
echo READY >/dev/console
exit 0
```

## Readable helper sources

[UDP collector](../../examples/visibility/syslog_receiver.py) and [event correlator](../../examples/visibility/correlate.py). `python scripts/embed_webhook.py --check` verifies the exact source bytes embedded in the topology; an outdated copy is rejected.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
