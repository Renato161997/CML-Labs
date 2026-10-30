# ACL NAT Inspection

## Scope and prerequisites

Stateful zones and interface-overload PAT are combined on the same virtual edge. The outside guest intentionally has a route to the inside subnet. With PAT enabled, the HTTP server must observe the firewall outside address and the TCP translation table must agree. Disabling only the inside NAT classification and clearing dynamic translations must keep routed inside-initiated HTTP working, but its actual observed source must become the inside host address. Unsolicited reverse HTTP remains blocked by the zone policy in both states. Thus NAT removal is not incorrectly equated with either a broken return route or removal of the security boundary. One IOSv router and two official Net-Tools guests exchange real HTTP packets on isolated benchmark subnets. The endpoint server reports the peer address it actually observes. Both local servers are independently checked, and both guests have explicit routes through the firewall, so a blocked reverse request is not explained by a missing route or stopped service. HTTP is deliberately plaintext, including the published8443 port in the capstone; no TLS or application-security product is implied. Cisco lists IOSv ZBFW as a feature that may work rather than an officially supported feature; the recorded result applies only to the exact tested image and behavior: https://developer.cisco.com/docs/modeling-labs/iosv/ . Nominal RAM is1536MiB. This is virtual software forwarding, not throughput or a vendor-appliance benchmark.

Use licensed reference images for iosv, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- INSIDE eth1 <-> FW GigabitEthernet0/0
- OUTSIDE eth1 <-> FW GigabitEthernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| FW | GigabitEthernet0/0 | `ip address 198.18.10.1 255.255.255.0` |
| FW | GigabitEthernet0/1 | `ip address 198.18.20.1 255.255.255.0` |
| INSIDE | eth1 | `198.18.10.10/24` |
| OUTSIDE | eth1 | `198.18.20.20/24` |

## Tasks

1. Correlate the server-observed source address with an actual PAT translation and stateful inspection.
2. Disable NAT without removing routing and show that translation is separate from firewall authorization.
3. Restore PAT and preserve the independently enforced reverse-connection block.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| INSIDE | `python3 /lab/t.py probe 198.18.10.10` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| OUTSIDE | `ip route get 198.18.10.10` | The outside endpoint has an actual route to inside through the firewall. |
| INSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| FW | `show ip nat translations` | The actual TCP translation maps the inside source to the outside interface. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.10.10` | The actual plain-HTTP connection is blocked while its separately checked server stays healthy. |
| FW | `show policy-map type inspect zone-pair` | The stateful policy reports actual created inspection sessions. |

## Transition: disable source translation while retaining routing

On **FW**:

```ios
configure terminal
interface GigabitEthernet0/0
no ip nat inside
exit
do clear ip nat translation *
end
```

- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.10.10` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `python3 /lab/t.py probe 198.18.10.10` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- FW: `show policy-map type inspect zone-pair` -- The stateful policy reports actual created inspection sessions.

## Transition: restore actual PAT behavior

On **FW**:

```ios
configure terminal
interface GigabitEthernet0/0
ip nat inside
end
```

- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- FW: `show ip nat translations` -- The actual TCP translation maps the inside source to the outside interface.
- OUTSIDE: `python3 /lab/t.py probe 198.18.10.10` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- FW: `show policy-map type inspect zone-pair` -- The stateful policy reports actual created inspection sessions.

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
zone security INSIDE
zone security OUTSIDE
class-map type inspect match-any CLIENT-TRAFFIC
 match protocol tcp
 match protocol icmp
 exit
policy-map type inspect STATEFUL-OUT
 class type inspect CLIENT-TRAFFIC
  inspect
  exit
 class class-default
  drop
  exit
 exit
policy-map type inspect STATELESS-OUT
 class type inspect CLIENT-TRAFFIC
  pass
  exit
 class class-default
  drop
  exit
 exit
zone-pair security INSIDE-OUT source INSIDE destination OUTSIDE
 service-policy type inspect STATEFUL-OUT
 exit
ip access-list standard INSIDE-NAT
 permit 198.18.10.0 0.0.0.255
 exit
ip nat inside source list INSIDE-NAT interface GigabitEthernet0/1 overload
interface GigabitEthernet0/0
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 zone-member security INSIDE
 ip nat inside
 exit
interface GigabitEthernet0/1
 ip address 198.18.20.1 255.255.255.0
 no shutdown
 zone-member security OUTSIDE
 ip nat outside
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

## Inspectable packet fixture

[HTTP traffic fixture](../../examples/security/traffic_fixture.py) performs real local HTTP requests and reports the server-observed peer address. Its CLI accepts only benchmark/loopback IPv4 addresses. Registered embedded source is checked byte-for-byte.
