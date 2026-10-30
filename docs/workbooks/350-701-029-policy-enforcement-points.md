# Policy Enforcement Points

## Scope and prerequisites

The first policy is an interface ingress ACL dropping only INSIDE TCP to the OUTSIDE HTTP service. It must count actual denies while both router-local ICMP probes and the local OUTSIDE server remain healthy. After that ACL is removed, a separate selective CoPP policy must drop only the INSIDE router-local ICMP source while transit HTTP and trusted OUTSIDE management continue. Each rollback must recover the same application/probe. The controls demonstrate different enforcement points rather than presenting one ACL as a complete security architecture. One IOSv router and two official Net-Tools guests separate router-local ICMP from actual transit HTTP. The selector ACL is used by an MQC control-plane policy, not applied as an interface ACL. For a deterministic enforcement demonstration, both conforming and exceeding selected packets are dropped at8000bps; this is not a throughput or burst-capacity benchmark. A directly tested trusted source and transit application remain healthy. IOSv QoS/CoPP behavior is experimental and the evidence applies only to the exact tested image; no production CPU-offload or hardware-rate claim is made. All addresses and plaintext HTTP endpoints are isolated fixtures. Nominal RAM is1536MiB.

Use licensed reference images for iosv, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- INSIDE eth1 <-> FW GigabitEthernet0/0
- OUTSIDE eth1 <-> FW GigabitEthernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| FW | GigabitEthernet0/0 | `ip address 198.18.10.1 255.255.255.0` |
| FW | GigabitEthernet0/1 | `ip address 198.18.20.1 255.255.255.0` |
| FW | Loopback0 | `ip address 192.0.2.80 255.255.255.255` |
| INSIDE | eth1 | `198.18.10.10/24` |
| OUTSIDE | eth1 | `198.18.20.20/24` |

## Tasks

1. Contrast an ingress transit-service ACL with a router-local control-plane selector.
2. Prove independent application and management effects with actual packets and counters.
3. Recover each enforcement point without changing addressing or routes.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| INSIDE | `python3 /lab/t.py probe 198.18.10.10` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| INSIDE | `ping -c 3 -W 1 192.0.2.80` | The actual INSIDE control-plane probe succeeds. |
| OUTSIDE | `ping -c 3 -W 1 192.0.2.80` | The actual OUTSIDE control-plane probe succeeds. |
| INSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |

## Transition: block the forwarded application at ingress

On **FW**:

```ios
configure terminal
ip access-list extended TRANSIT-WEB
deny tcp host 198.18.10.10 host 198.18.20.20 eq 8080
permit ip any any
exit
interface GigabitEthernet0/0
ip access-group TRANSIT-WEB in
end
```

- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -c 3 -W 1 192.0.2.80` -- The actual INSIDE control-plane probe succeeds.
- OUTSIDE: `ping -c 3 -W 1 192.0.2.80` -- The actual OUTSIDE control-plane probe succeeds.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- FW: `show access-lists TRANSIT-WEB` -- The actual transit ingress policy counts dropped TCP requests.

## Transition: restore the forwarded application

On **FW**:

```ios
configure terminal
interface GigabitEthernet0/0
no ip access-group TRANSIT-WEB in
end
```

- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `ping -c 3 -W 1 192.0.2.80` -- The actual INSIDE control-plane probe succeeds.

## Transition: enforce only the selected control-plane source

On **FW**:

```ios
configure terminal
control-plane
service-policy input COPP-GUARD
end
```

- INSIDE: `ping -c 3 -W 1 192.0.2.80` -- The actual INSIDE control-plane probe is dropped.
- FW: `show policy-map control-plane` -- The selected control-plane class counts actual packets.
- OUTSIDE: `ping -c 3 -W 1 192.0.2.80` -- The actual OUTSIDE control-plane probe succeeds.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Transition: restore both management and data baseline

On **FW**:

```ios
configure terminal
control-plane
no service-policy input COPP-GUARD
end
```

- INSIDE: `ping -c 3 -W 1 192.0.2.80` -- The actual INSIDE control-plane probe succeeds.
- OUTSIDE: `ping -c 3 -W 1 192.0.2.80` -- The actual OUTSIDE control-plane probe succeeds.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### FW

```ios
hostname FW
no ip domain-lookup
no service config
ip cef
line console 0
 exec-timeout 0 0
 logging synchronous
 exit
no logging console
ip access-list extended CPU-SOURCES
 10 permit icmp host 198.18.10.10 host 192.0.2.80 echo
 exit
class-map match-all CPU-SELECT
 match access-group name CPU-SOURCES
 exit
policy-map COPP-GUARD
 class CPU-SELECT
  police 8000 conform-action drop exceed-action drop
  exit
 exit
interface GigabitEthernet0/0
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 exit
interface GigabitEthernet0/1
 ip address 198.18.20.1 255.255.255.0
 no shutdown
 exit
interface Loopback0
 ip address 192.0.2.80 255.255.255.255
 no shutdown
 exit
end
```

### INSIDE: boot.sh

```bash
#!/bin/bash
set -eu
ip address add 198.18.10.10/24 dev eth1
ip link set eth1 up
ip route add 198.18.20.0/24 via 198.18.10.1 dev eth1
ip route add 192.0.2.80/32 via 198.18.10.1 dev eth1
mkdir -p /lab
base64 -d > /lab/t.py <<'CML_EMBED_EXAMPLES_SECURITY_TRAFFIC_FIXTURE_PY'
IiIiUGxhaW4gSFRUUCBwYWNrZXQvcGVlciBmaXh0dXJlIHJlc3RyaWN0ZWQgdG8gaXNvbGF0ZWQg
YmVuY2htYXJrIG9yIGxvb3BiYWNrIElQcy4iIiIKCmZyb20gX19mdXR1cmVfXyBpbXBvcnQgYW5u
b3RhdGlvbnMKCmltcG9ydCBhcmdwYXJzZQppbXBvcnQgaHR0cC5jbGllbnQKaW1wb3J0IGh0dHAu
c2VydmVyCmltcG9ydCBpcGFkZHJlc3MKaW1wb3J0IGpzb24KCgpkZWYgZml4dHVyZV9hZGRyZXNz
KHZhbHVlKToKICAgIGFkZHJlc3MgPSBpcGFkZHJlc3MuSVB2NEFkZHJlc3ModmFsdWUpCiAgICBp
ZiBub3QgKGFkZHJlc3MgaW4gaXBhZGRyZXNzLklQdjROZXR3b3JrKCIxOTguMTguMC4wLzE1Iikg
b3IgYWRkcmVzcy5pc19sb29wYmFjayk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiT25seSBi
ZW5jaG1hcmsvbG9vcGJhY2sgZml4dHVyZSBJUHY0IHRhcmdldHMgYXJlIGFjY2VwdGVkIikKICAg
IHJldHVybiBzdHIoYWRkcmVzcykKCgpjbGFzcyBIYW5kbGVyKGh0dHAuc2VydmVyLkJhc2VIVFRQ
UmVxdWVzdEhhbmRsZXIpOgogICAgZGVmIGxvZ19tZXNzYWdlKHNlbGYsICpfYXJncyk6CiAgICAg
ICAgcGFzcwoKICAgIGRlZiBkb19HRVQoc2VsZik6CiAgICAgICAgaWYgc2VsZi5wYXRoICE9ICIv
aGVhbHRoIjoKICAgICAgICAgICAgc2VsZi5zZW5kX2Vycm9yKDQwNCkKICAgICAgICAgICAgcmV0
dXJuCiAgICAgICAgZGF0YSA9IGpzb24uZHVtcHMoCiAgICAgICAgICAgIHsic2VydmVyIjogc2Vs
Zi5zZXJ2ZXIuZml4dHVyZV9sYWJlbCwgInBlZXIiOiBzZWxmLmNsaWVudF9hZGRyZXNzWzBdfSwK
ICAgICAgICAgICAgc29ydF9rZXlzPVRydWUsCiAgICAgICAgKS5lbmNvZGUoInV0Zi04IikKICAg
ICAgICBzZWxmLnNlbmRfcmVzcG9uc2UoMjAwKQogICAgICAgIHNlbGYuc2VuZF9oZWFkZXIoIkNv
bnRlbnQtVHlwZSIsICJhcHBsaWNhdGlvbi9qc29uIikKICAgICAgICBzZWxmLnNlbmRfaGVhZGVy
KCJDb250ZW50LUxlbmd0aCIsIHN0cihsZW4oZGF0YSkpKQogICAgICAgIHNlbGYuZW5kX2hlYWRl
cnMoKQogICAgICAgIHNlbGYud2ZpbGUud3JpdGUoZGF0YSkKCgpkZWYgc2VydmVyKGFkZHJlc3Ms
IHBvcnQsIGxhYmVsKToKICAgIHZhbHVlID0gaHR0cC5zZXJ2ZXIuVGhyZWFkaW5nSFRUUFNlcnZl
cigoZml4dHVyZV9hZGRyZXNzKGFkZHJlc3MpLCBwb3J0KSwgSGFuZGxlcikKICAgIHZhbHVlLmZp
eHR1cmVfbGFiZWwgPSBsYWJlbAogICAgdmFsdWUuZGFlbW9uX3RocmVhZHMgPSBUcnVlCiAgICBy
ZXR1cm4gdmFsdWUKCgpkZWYgcHJvYmUoYWRkcmVzcywgcG9ydD04MDgwLCB0aW1lb3V0PTMpOgog
ICAgYWRkcmVzcyA9IGZpeHR1cmVfYWRkcmVzcyhhZGRyZXNzKQogICAgY29ubmVjdGlvbiA9IGh0
dHAuY2xpZW50LkhUVFBDb25uZWN0aW9uKGFkZHJlc3MsIHBvcnQsIHRpbWVvdXQ9dGltZW91dCkK
ICAgIHRyeToKICAgICAgICBjb25uZWN0aW9uLnJlcXVlc3QoIkdFVCIsICIvaGVhbHRoIikKICAg
ICAgICByZXNwb25zZSA9IGNvbm5lY3Rpb24uZ2V0cmVzcG9uc2UoKQogICAgICAgIGJvZHkgPSBy
ZXNwb25zZS5yZWFkKDQwOTcpCiAgICAgICAgaWYgbGVuKGJvZHkpID4gNDA5NjoKICAgICAgICAg
ICAgcmFpc2UgVmFsdWVFcnJvcigiT3ZlcnNpemVkIGZpeHR1cmUgcmVzcG9uc2UiKQogICAgICAg
IHZhbHVlID0ganNvbi5sb2Fkcyhib2R5KQogICAgICAgIGlmIHNldCh2YWx1ZSkgIT0geyJwZWVy
IiwgInNlcnZlciJ9OgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJVbmV4cGVjdGVkIGZp
eHR1cmUgc2NoZW1hIikKICAgICAgICByZXR1cm4geyJyZWFjaGFibGUiOiBUcnVlLCAic3RhdHVz
IjogcmVzcG9uc2Uuc3RhdHVzLCAqKnZhbHVlfQogICAgZXhjZXB0IFRpbWVvdXRFcnJvcjoKICAg
ICAgICByZXR1cm4geyJyZWFjaGFibGUiOiBGYWxzZSwgInJlYXNvbiI6ICJ0aW1lb3V0In0KICAg
IGV4Y2VwdCBDb25uZWN0aW9uUmVmdXNlZEVycm9yOgogICAgICAgIHJldHVybiB7InJlYWNoYWJs
ZSI6IEZhbHNlLCAicmVhc29uIjogImNvbm5lY3Rpb25fcmVmdXNlZCJ9CiAgICBleGNlcHQgT1NF
cnJvcjoKICAgICAgICByZXR1cm4geyJyZWFjaGFibGUiOiBGYWxzZSwgInJlYXNvbiI6ICJuZXR3
b3JrX3JlamVjdGVkIn0KICAgIGZpbmFsbHk6CiAgICAgICAgY29ubmVjdGlvbi5jbG9zZSgpCgoK
ZGVmIG1haW4oKToKICAgIHBhcnNlciA9IGFyZ3BhcnNlLkFyZ3VtZW50UGFyc2VyKGRlc2NyaXB0
aW9uPV9fZG9jX18pCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCJhY3Rpb24iLCBjaG9pY2VzPSgi
c2VydmUiLCAicHJvYmUiKSkKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoImFkZHJlc3MiLCB0eXBl
PWZpeHR1cmVfYWRkcmVzcykKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0tcG9ydCIsIHR5cGU9
aW50LCBkZWZhdWx0PTgwODApCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItLWxhYmVsIiwgY2hv
aWNlcz0oIklOU0lERSIsICJPVVRTSURFIiksIGRlZmF1bHQ9Ik9VVFNJREUiKQogICAgYXJncyA9
IHBhcnNlci5wYXJzZV9hcmdzKCkKICAgIGlmIG5vdCAxMDI0IDw9IGFyZ3MucG9ydCA8PSA2NTUz
NToKICAgICAgICBwYXJzZXIuZXJyb3IoIlVzZSBhbiB1bnByaXZpbGVnZWQgZml4dHVyZSBwb3J0
IikKICAgIGlmIGFyZ3MuYWN0aW9uID09ICJzZXJ2ZSI6CiAgICAgICAgd2l0aCBzZXJ2ZXIoYXJn
cy5hZGRyZXNzLCBhcmdzLnBvcnQsIGFyZ3MubGFiZWwpIGFzIGxpc3RlbmVyOgogICAgICAgICAg
ICBsaXN0ZW5lci5zZXJ2ZV9mb3JldmVyKHBvbGxfaW50ZXJ2YWw9MC4xKQogICAgZWxzZToKICAg
ICAgICBwcmludChqc29uLmR1bXBzKHByb2JlKGFyZ3MuYWRkcmVzcywgYXJncy5wb3J0KSwgc29y
dF9rZXlzPVRydWUpKQoKCmlmIF9fbmFtZV9fID09ICJfX21haW5fXyI6CiAgICBtYWluKCkK
CML_EMBED_EXAMPLES_SECURITY_TRAFFIC_FIXTURE_PY
python3 /lab/t.py serve 198.18.10.10 --label INSIDE >/lab/http.log 2>&1 &
echo READY >/dev/console
exit 0
```

### OUTSIDE: boot.sh

```bash
#!/bin/bash
set -eu
ip address add 198.18.20.20/24 dev eth1
ip link set eth1 up
ip route add 198.18.10.0/24 via 198.18.20.1 dev eth1
ip route add 192.0.2.80/32 via 198.18.20.1 dev eth1
mkdir -p /lab
base64 -d > /lab/t.py <<'CML_EMBED_EXAMPLES_SECURITY_TRAFFIC_FIXTURE_PY'
IiIiUGxhaW4gSFRUUCBwYWNrZXQvcGVlciBmaXh0dXJlIHJlc3RyaWN0ZWQgdG8gaXNvbGF0ZWQg
YmVuY2htYXJrIG9yIGxvb3BiYWNrIElQcy4iIiIKCmZyb20gX19mdXR1cmVfXyBpbXBvcnQgYW5u
b3RhdGlvbnMKCmltcG9ydCBhcmdwYXJzZQppbXBvcnQgaHR0cC5jbGllbnQKaW1wb3J0IGh0dHAu
c2VydmVyCmltcG9ydCBpcGFkZHJlc3MKaW1wb3J0IGpzb24KCgpkZWYgZml4dHVyZV9hZGRyZXNz
KHZhbHVlKToKICAgIGFkZHJlc3MgPSBpcGFkZHJlc3MuSVB2NEFkZHJlc3ModmFsdWUpCiAgICBp
ZiBub3QgKGFkZHJlc3MgaW4gaXBhZGRyZXNzLklQdjROZXR3b3JrKCIxOTguMTguMC4wLzE1Iikg
b3IgYWRkcmVzcy5pc19sb29wYmFjayk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiT25seSBi
ZW5jaG1hcmsvbG9vcGJhY2sgZml4dHVyZSBJUHY0IHRhcmdldHMgYXJlIGFjY2VwdGVkIikKICAg
IHJldHVybiBzdHIoYWRkcmVzcykKCgpjbGFzcyBIYW5kbGVyKGh0dHAuc2VydmVyLkJhc2VIVFRQ
UmVxdWVzdEhhbmRsZXIpOgogICAgZGVmIGxvZ19tZXNzYWdlKHNlbGYsICpfYXJncyk6CiAgICAg
ICAgcGFzcwoKICAgIGRlZiBkb19HRVQoc2VsZik6CiAgICAgICAgaWYgc2VsZi5wYXRoICE9ICIv
aGVhbHRoIjoKICAgICAgICAgICAgc2VsZi5zZW5kX2Vycm9yKDQwNCkKICAgICAgICAgICAgcmV0
dXJuCiAgICAgICAgZGF0YSA9IGpzb24uZHVtcHMoCiAgICAgICAgICAgIHsic2VydmVyIjogc2Vs
Zi5zZXJ2ZXIuZml4dHVyZV9sYWJlbCwgInBlZXIiOiBzZWxmLmNsaWVudF9hZGRyZXNzWzBdfSwK
ICAgICAgICAgICAgc29ydF9rZXlzPVRydWUsCiAgICAgICAgKS5lbmNvZGUoInV0Zi04IikKICAg
ICAgICBzZWxmLnNlbmRfcmVzcG9uc2UoMjAwKQogICAgICAgIHNlbGYuc2VuZF9oZWFkZXIoIkNv
bnRlbnQtVHlwZSIsICJhcHBsaWNhdGlvbi9qc29uIikKICAgICAgICBzZWxmLnNlbmRfaGVhZGVy
KCJDb250ZW50LUxlbmd0aCIsIHN0cihsZW4oZGF0YSkpKQogICAgICAgIHNlbGYuZW5kX2hlYWRl
cnMoKQogICAgICAgIHNlbGYud2ZpbGUud3JpdGUoZGF0YSkKCgpkZWYgc2VydmVyKGFkZHJlc3Ms
IHBvcnQsIGxhYmVsKToKICAgIHZhbHVlID0gaHR0cC5zZXJ2ZXIuVGhyZWFkaW5nSFRUUFNlcnZl
cigoZml4dHVyZV9hZGRyZXNzKGFkZHJlc3MpLCBwb3J0KSwgSGFuZGxlcikKICAgIHZhbHVlLmZp
eHR1cmVfbGFiZWwgPSBsYWJlbAogICAgdmFsdWUuZGFlbW9uX3RocmVhZHMgPSBUcnVlCiAgICBy
ZXR1cm4gdmFsdWUKCgpkZWYgcHJvYmUoYWRkcmVzcywgcG9ydD04MDgwLCB0aW1lb3V0PTMpOgog
ICAgYWRkcmVzcyA9IGZpeHR1cmVfYWRkcmVzcyhhZGRyZXNzKQogICAgY29ubmVjdGlvbiA9IGh0
dHAuY2xpZW50LkhUVFBDb25uZWN0aW9uKGFkZHJlc3MsIHBvcnQsIHRpbWVvdXQ9dGltZW91dCkK
ICAgIHRyeToKICAgICAgICBjb25uZWN0aW9uLnJlcXVlc3QoIkdFVCIsICIvaGVhbHRoIikKICAg
ICAgICByZXNwb25zZSA9IGNvbm5lY3Rpb24uZ2V0cmVzcG9uc2UoKQogICAgICAgIGJvZHkgPSBy
ZXNwb25zZS5yZWFkKDQwOTcpCiAgICAgICAgaWYgbGVuKGJvZHkpID4gNDA5NjoKICAgICAgICAg
ICAgcmFpc2UgVmFsdWVFcnJvcigiT3ZlcnNpemVkIGZpeHR1cmUgcmVzcG9uc2UiKQogICAgICAg
IHZhbHVlID0ganNvbi5sb2Fkcyhib2R5KQogICAgICAgIGlmIHNldCh2YWx1ZSkgIT0geyJwZWVy
IiwgInNlcnZlciJ9OgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJVbmV4cGVjdGVkIGZp
eHR1cmUgc2NoZW1hIikKICAgICAgICByZXR1cm4geyJyZWFjaGFibGUiOiBUcnVlLCAic3RhdHVz
IjogcmVzcG9uc2Uuc3RhdHVzLCAqKnZhbHVlfQogICAgZXhjZXB0IFRpbWVvdXRFcnJvcjoKICAg
ICAgICByZXR1cm4geyJyZWFjaGFibGUiOiBGYWxzZSwgInJlYXNvbiI6ICJ0aW1lb3V0In0KICAg
IGV4Y2VwdCBDb25uZWN0aW9uUmVmdXNlZEVycm9yOgogICAgICAgIHJldHVybiB7InJlYWNoYWJs
ZSI6IEZhbHNlLCAicmVhc29uIjogImNvbm5lY3Rpb25fcmVmdXNlZCJ9CiAgICBleGNlcHQgT1NF
cnJvcjoKICAgICAgICByZXR1cm4geyJyZWFjaGFibGUiOiBGYWxzZSwgInJlYXNvbiI6ICJuZXR3
b3JrX3JlamVjdGVkIn0KICAgIGZpbmFsbHk6CiAgICAgICAgY29ubmVjdGlvbi5jbG9zZSgpCgoK
ZGVmIG1haW4oKToKICAgIHBhcnNlciA9IGFyZ3BhcnNlLkFyZ3VtZW50UGFyc2VyKGRlc2NyaXB0
aW9uPV9fZG9jX18pCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCJhY3Rpb24iLCBjaG9pY2VzPSgi
c2VydmUiLCAicHJvYmUiKSkKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoImFkZHJlc3MiLCB0eXBl
PWZpeHR1cmVfYWRkcmVzcykKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0tcG9ydCIsIHR5cGU9
aW50LCBkZWZhdWx0PTgwODApCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItLWxhYmVsIiwgY2hv
aWNlcz0oIklOU0lERSIsICJPVVRTSURFIiksIGRlZmF1bHQ9Ik9VVFNJREUiKQogICAgYXJncyA9
IHBhcnNlci5wYXJzZV9hcmdzKCkKICAgIGlmIG5vdCAxMDI0IDw9IGFyZ3MucG9ydCA8PSA2NTUz
NToKICAgICAgICBwYXJzZXIuZXJyb3IoIlVzZSBhbiB1bnByaXZpbGVnZWQgZml4dHVyZSBwb3J0
IikKICAgIGlmIGFyZ3MuYWN0aW9uID09ICJzZXJ2ZSI6CiAgICAgICAgd2l0aCBzZXJ2ZXIoYXJn
cy5hZGRyZXNzLCBhcmdzLnBvcnQsIGFyZ3MubGFiZWwpIGFzIGxpc3RlbmVyOgogICAgICAgICAg
ICBsaXN0ZW5lci5zZXJ2ZV9mb3JldmVyKHBvbGxfaW50ZXJ2YWw9MC4xKQogICAgZWxzZToKICAg
ICAgICBwcmludChqc29uLmR1bXBzKHByb2JlKGFyZ3MuYWRkcmVzcywgYXJncy5wb3J0KSwgc29y
dF9rZXlzPVRydWUpKQoKCmlmIF9fbmFtZV9fID09ICJfX21haW5fXyI6CiAgICBtYWluKCkK
CML_EMBED_EXAMPLES_SECURITY_TRAFFIC_FIXTURE_PY
python3 /lab/t.py serve 198.18.20.20 --label OUTSIDE >/lab/http.log 2>&1 &
echo READY >/dev/console
exit 0
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

## Packet fixture

[Inspectable HTTP packet/peer fixture](../../examples/security/traffic_fixture.py). Linux ICMP probes are separate from HTTP and require exact received-packet/loss results; a substring matching100percent loss is never accepted as zero loss.
