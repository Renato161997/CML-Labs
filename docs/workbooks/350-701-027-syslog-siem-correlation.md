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
cGFpcmluZyBpcyBub3QgY2F1c2FsaXR5LiIiIg0KDQppbXBvcnQgYXJncGFyc2UNCmltcG9ydCBq
c29uDQppbXBvcnQgcmUNCmltcG9ydCBzeXMNCmZyb20gcGF0aGxpYiBpbXBvcnQgUGF0aA0KDQoN
CmRlZiBjb3JyZWxhdGUoZXZlbnRzLCBzb3VyY2UsIHdpbmRvdz0xMjApOg0KICAgIGZhbWlsaWVz
ID0geyJwYWNrZXRfZGVuaWVkIjogW10sICJpbnRlcmZhY2VfZGlzYWJsZWQiOiBbXX0NCiAgICBm
b3IgZXZlbnQgaW4gZXZlbnRzOg0KICAgICAgICBpZiBldmVudC5nZXQoInNvdXJjZSIpICE9IHNv
dXJjZSBvciBldmVudC5nZXQoInRydW5jYXRlZCIpOg0KICAgICAgICAgICAgY29udGludWUNCiAg
ICAgICAgbWVzc2FnZSA9IGV2ZW50WyJtZXNzYWdlIl0NCiAgICAgICAgc3RhbXAgPSBldmVudFsi
cmVjZWl2ZWRfbW9ub3RvbmljIl0NCiAgICAgICAgaWYgbm90IGlzaW5zdGFuY2Uoc3RhbXAsIChm
bG9hdCwgaW50KSkgb3Igbm90IGlzaW5zdGFuY2UobWVzc2FnZSwgc3RyKToNCiAgICAgICAgICAg
IHJhaXNlIFR5cGVFcnJvcigiSW52YWxpZCBjb2xsZWN0b3IgcmVjb3JkIikNCiAgICAgICAgaWYg
cmUuc2VhcmNoKHIiSVBBQ0NFU1NMT0cuKkNNTC1ERU5ZLipkZW5pZWRccytpY21wIiwgbWVzc2Fn
ZSwgcmUuSUdOT1JFQ0FTRSk6DQogICAgICAgICAgICBmYW1pbGllc1sicGFja2V0X2RlbmllZCJd
LmFwcGVuZChldmVudCkNCiAgICAgICAgaWYgcmUuc2VhcmNoKHIiJUxJTkstXGQtLipMb29wYmFj
azEuKmFkbWluaXN0cmF0aXZlbHkgZG93biIsIG1lc3NhZ2UsIHJlLklHTk9SRUNBU0UpOg0KICAg
ICAgICAgICAgZmFtaWxpZXNbImludGVyZmFjZV9kaXNhYmxlZCJdLmFwcGVuZChldmVudCkNCiAg
ICBwYWlycyA9IFsNCiAgICAgICAgeyJwYWNrZXRfZGVuaWVkIjogYSwgImludGVyZmFjZV9kaXNh
YmxlZCI6IGJ9DQogICAgICAgIGZvciBhIGluIGZhbWlsaWVzWyJwYWNrZXRfZGVuaWVkIl0NCiAg
ICAgICAgZm9yIGIgaW4gZmFtaWxpZXNbImludGVyZmFjZV9kaXNhYmxlZCJdDQogICAgICAgIGlm
IGFicyhhWyJyZWNlaXZlZF9tb25vdG9uaWMiXSAtIGJbInJlY2VpdmVkX21vbm90b25pYyJdKSA8
PSB3aW5kb3cNCiAgICBdDQogICAgcmV0dXJuIHsNCiAgICAgICAgInNvdXJjZSI6IHNvdXJjZSwN
CiAgICAgICAgIndpbmRvd19zZWNvbmRzIjogd2luZG93LA0KICAgICAgICAiZXZlbnRfY291bnRz
Ijoge25hbWU6IGxlbihyb3dzKSBmb3IgbmFtZSwgcm93cyBpbiBmYW1pbGllcy5pdGVtcygpfSwN
CiAgICAgICAgImNvcnJlbGF0aW9ucyI6IHBhaXJzWzo0XSwNCiAgICAgICAgImNvcnJlbGF0aW9u
X2NvdW50IjogbGVuKHBhaXJzKSwNCiAgICB9DQoNCg0KZGVmIG1haW4oKToNCiAgICBwYXJzZXIg
PSBhcmdwYXJzZS5Bcmd1bWVudFBhcnNlcihkZXNjcmlwdGlvbj1fX2RvY19fKQ0KICAgIHBhcnNl
ci5hZGRfYXJndW1lbnQoIm1vZGUiLCBjaG9pY2VzPSgiYmFzZWxpbmUiLCAic2luZ2xlIiwgImlu
Y2lkZW50IikpDQogICAgYXJncyA9IHBhcnNlci5wYXJzZV9hcmdzKCkNCiAgICB0cnk6DQogICAg
ICAgIGlmIG5vdCBQYXRoKCIvbGFiL3JlY2VpdmVyLXJlYWR5IikuZXhpc3RzKCk6DQogICAgICAg
ICAgICByYWlzZSBSdW50aW1lRXJyb3IoIkNvbGxlY3RvciBoYXMgbm90IGJvdW5kIGl0cyBVRFAg
bGlzdGVuZXIiKQ0KICAgICAgICBldmVudHMgPSBbDQogICAgICAgICAgICBqc29uLmxvYWRzKGxp
bmUpDQogICAgICAgICAgICBmb3IgbGluZSBpbiBQYXRoKCIvbGFiL2V2ZW50cy5qc29ubCIpLnJl
YWRfdGV4dChlbmNvZGluZz0idXRmLTgiKS5zcGxpdGxpbmVzKCkNCiAgICAgICAgXQ0KICAgICAg
ICByZXBvcnQgPSBjb3JyZWxhdGUoZXZlbnRzLCAiMTk4LjE4LjEuMSIpDQogICAgICAgIGNvdW50
cyA9IHJlcG9ydFsiZXZlbnRfY291bnRzIl0NCiAgICAgICAgaWYgYXJncy5tb2RlID09ICJiYXNl
bGluZSIgYW5kIChjb3VudHNbInBhY2tldF9kZW5pZWQiXSBvciBjb3VudHNbImludGVyZmFjZV9k
aXNhYmxlZCJdKToNCiAgICAgICAgICAgIHJhaXNlIFJ1bnRpbWVFcnJvcigiVW5leHBlY3RlZCBp
bml0aWFsIGV2ZW50IGZhbWlsaWVzIikNCiAgICAgICAgaWYgYXJncy5tb2RlID09ICJzaW5nbGUi
IGFuZCAoDQogICAgICAgICAgICBub3QgY291bnRzWyJwYWNrZXRfZGVuaWVkIl0NCiAgICAgICAg
ICAgIG9yIGNvdW50c1siaW50ZXJmYWNlX2Rpc2FibGVkIl0NCiAgICAgICAgICAgIG9yIHJlcG9y
dFsiY29ycmVsYXRpb25fY291bnQiXQ0KICAgICAgICApOg0KICAgICAgICAgICAgcmFpc2UgUnVu
dGltZUVycm9yKCJTaW5nbGUtZmFtaWx5IG5lZ2F0aXZlIGNvbnRyb2wgZmFpbGVkIikNCiAgICAg
ICAgaWYgYXJncy5tb2RlID09ICJpbmNpZGVudCIgYW5kIG5vdCByZXBvcnRbImNvcnJlbGF0aW9u
X2NvdW50Il06DQogICAgICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoIkJvdGggYWN0dWFsIGV2
ZW50IGZhbWlsaWVzIGFyZSByZXF1aXJlZCBpbiB0aGUgcmVjZWl2ZSB3aW5kb3ciKQ0KICAgICAg
ICByZXBvcnQudXBkYXRlKHN0YXR1cz0icGFzc2VkIiwgbW9kZT1hcmdzLm1vZGUpDQogICAgICAg
IHByaW50KGpzb24uZHVtcHMocmVwb3J0LCBzb3J0X2tleXM9VHJ1ZSkpDQogICAgICAgIHJldHVy
biAwDQogICAgZXhjZXB0IChPU0Vycm9yLCBWYWx1ZUVycm9yLCBUeXBlRXJyb3IsIFJ1bnRpbWVF
cnJvciwgS2V5RXJyb3IpIGFzIGV4YzoNCiAgICAgICAgcHJpbnQoanNvbi5kdW1wcyh7InN0YXR1
cyI6ICJmYWlsZWQiLCAiZXJyb3IiOiBzdHIoZXhjKX0pKQ0KICAgICAgICByZXR1cm4gMQ0KDQoN
CmlmIF9fbmFtZV9fID09ICJfX21haW5fXyI6DQogICAgc3lzLmV4aXQobWFpbigpKQ0K
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
