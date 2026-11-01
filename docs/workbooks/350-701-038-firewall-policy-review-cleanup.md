# Firewall Policy Review: Shadowed Rules, Cleanup and Rollback

## Scope and prerequisites

A real IOL-XE router forwards between two native Linux HTTP fixtures. The outside endpoint runs two actual listeners, 8080(application) and 9090(administration); both must answer locally before a blocked transit result can count. The application reports the original inside peer. An independent three-reply ICMP control and the actual ingress binding remain part of every observed matrix.

The initial ACL has a broader application permit 10 before its narrower permit 20, and a broader administration deny 30 before its narrower deny 40. The same source/destination/protocol/port/action relationship, sequence ordering and prefix inclusion make these two later rules unreachable for their declared matches. Actual hits must appear on 10/30 and not 20/40. This is an explicitly supplied finite policy, not a general shadow-analysis engine. Zero hits alone never justify removal: an independently checked legacy ACL is removed only because it is not bound anywhere in this fixture configuration.

First remove only LEGACY-NOT-BOUND. Then remove only the known shadowed sequences 20/40. Local service availability, application allow, administration deny, ICMP control and policy binding must retain the same observed outcomes after each cleanup. As a distinct negative control, withdraw the retained application permit 10: application traffic must now fail at the default deny while administration remains denied and ICMP/local listeners stay healthy. Restore that exact permit and recover the full clean matrix. The final policy stays cleaned; the test does not reintroduce obsolete objects.

The matrix covers the explicitly generated flows, not every source address, TCP state, fragment, IPv6 packet, NAT path, vendor firewall manager or production policy. Known fixture prefix/action ordering supplies the redundancy argument; counters and successful sample probes alone do not constitute a universal equivalence proof. This is an IOS extended ingress ACL exercise, not stateful NGFW, hardware throughput or a production auto-deletion recommendation. No external connector, Internet service, production policy or credential is used. Only the disposable imported copy may be stopped/wiped.


Use licensed reference images for iol-xe, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- INSIDE eth1 <-> FW Ethernet0/0
- OUTSIDE eth1 <-> FW Ethernet0/1

| Node | Interface | Address |
| --- | --- | --- |
| FW | Ethernet0/0 | `ip address 198.18.10.1 255.255.255.0` |
| FW | Ethernet0/1 | `ip address 198.18.20.1 255.255.255.0` |
| INSIDE | eth1 | `198.18.10.10/24` |
| OUTSIDE | eth1 | `198.18.20.20/24` |

## Tasks

1. Distinguish an actually bound policy from a known unbound object and prove both HTTP services exist.
2. Use the supplied match/action/ordering relationship to identify the two shadowed rules; preserve a measured flow matrix during cleanup.
3. Demonstrate that removing a retained necessary permit is a functional change, then recover without undoing cleanup.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| OUTSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.20.20 --port 9090` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| INSIDE | `python3 /lab/t.py probe 198.18.20.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| INSIDE | `python3 /lab/t.py probe 198.18.20.20 --port 9090` | The actual plain-HTTP connection is blocked while its separately checked server stays healthy. |
| INSIDE | `ping -c 3 -W 1 198.18.20.20` | The independent routed ICMP control continues to receive all three replies. |
| FW | `show running-config | include ip access-group` | The actual ingress remains bound to the reviewed policy; the legacy fixture is not applied. |
| FW | `show access-lists REVIEW-IN` | The first broader rules count actual allowed/denied traffic; the later narrower rules are present but cannot be reached for their covered tuple. |
| FW | `show ip access-lists` | Both reviewed and explicitly unbound legacy ACL objects exist in the initial source. |

## Transition: remove only the explicitly unbound legacy ACL

On **FW**:

```ios
configure terminal
no ip access-list extended LEGACY-NOT-BOUND
end
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -c 3 -W 1 198.18.20.20` -- The independent routed ICMP control continues to receive all three replies.
- FW: `show running-config | include ip access-group` -- The actual ingress remains bound to the reviewed policy; the legacy fixture is not applied.
- FW: `show ip access-lists` -- The live reviewed policy remains while only the unbound legacy object disappears.

## Transition: remove only the two known shadowed sequences

On **FW**:

```ios
configure terminal
ip access-list extended REVIEW-IN
no 20
no 40
end
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -c 3 -W 1 198.18.20.20` -- The independent routed ICMP control continues to receive all three replies.
- FW: `show running-config | include ip access-group` -- The actual ingress remains bound to the reviewed policy; the legacy fixture is not applied.
- FW: `show ip access-lists` -- The live reviewed policy remains while only the unbound legacy object disappears.
- FW: `show access-lists REVIEW-IN` -- The retained allow, deny, control and default-deny entries remain; only the known shadowed sequences were removed.

## Transition: withdraw a retained necessary application permit

On **FW**:

```ios
configure terminal
ip access-list extended REVIEW-IN
no 10
end
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -c 3 -W 1 198.18.20.20` -- The independent routed ICMP control continues to receive all three replies.
- FW: `show running-config | include ip access-group` -- The actual ingress remains bound to the reviewed policy; the legacy fixture is not applied.
- FW: `show access-lists REVIEW-IN` -- The actual default-deny counter observes the application requests after the required permit disappears.

## Transition: restore the clean required application behavior

On **FW**:

```ios
configure terminal
ip access-list extended REVIEW-IN
10 permit tcp 198.18.10.0 0.0.0.255 host 198.18.20.20 eq 8080
end
```

- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.20.20 --port 9090` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `ping -c 3 -W 1 198.18.20.20` -- The independent routed ICMP control continues to receive all three replies.
- FW: `show running-config | include ip access-group` -- The actual ingress remains bound to the reviewed policy; the legacy fixture is not applied.
- FW: `show ip access-lists` -- The live reviewed policy remains while only the unbound legacy object disappears.
- FW: `show access-lists REVIEW-IN` -- The retained allow, deny, control and default-deny entries remain; only the known shadowed sequences were removed.

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
interface range Ethernet0/0 - 3
 no ip address
 shutdown
 exit
no logging console
ip access-list extended REVIEW-IN
 10 permit tcp 198.18.10.0 0.0.0.255 host 198.18.20.20 eq 8080
 20 permit tcp host 198.18.10.10 host 198.18.20.20 eq 8080
 30 deny tcp 198.18.10.0 0.0.0.255 host 198.18.20.20 eq 9090
 40 deny tcp host 198.18.10.10 host 198.18.20.20 eq 9090
 50 permit icmp any any
 60 deny ip any any
 exit
ip access-list extended LEGACY-NOT-BOUND
 permit ip host 192.0.2.1 host 192.0.2.2
 exit
interface Ethernet0/0
 ip address 198.18.10.1 255.255.255.0
 no shutdown
 ip access-group REVIEW-IN in
 exit
interface Ethernet0/1
 ip address 198.18.20.1 255.255.255.0
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
python3 /lab/t.py serve 198.18.20.20 --port 9090 --label OUTSIDE >/lab/admin-http.log 2>&1 &
echo READY >/dev/console
exit 0
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

## Real packet fixtures

The [unchanged HTTP peer/health fixture](../../examples/security/traffic_fixture.py) runs two independent listeners on OUTSIDE. A denied request is never accepted without the local listener positive control. Inspect only the disposable router policy and its named counters. Never infer global policy equivalence from this finite traffic matrix.
