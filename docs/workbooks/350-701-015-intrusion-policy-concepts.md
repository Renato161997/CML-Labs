# Intrusion Policy Concepts

## Scope and prerequisites

An actual Snort3 container in the separately built CML-Labs Inspection image operates as an AFPacket inline pair between two isolated Net-Tools guests. No Linux bridge or parallel bypass exists. A deliberately benign plaintext HTTP GET is the signature fixture: matching it does not establish maliciousness, a vulnerability or a useful production detection. In the working reference, the alert action records the request without dropping it. An intentionally overbroad flow-block rule blocks both HTTP ports on 198.18.0.20 and an independent HTTP service on 198.18.0.21:8081. Local probes prove both servers remain healthy, and ICMP still forwards. The HTTP-method buffer associates the rule with the HTTP service, which can supersede signature-header port matching in the tested engine: the tuned rule therefore deliberately constrains destination host 198.18.0.20. Both HTTP ports on that host must stay blocked, while the independent 198.18.0.21 service must recover. This teaches why signature port scope must not be assumed equivalent to an access-control policy. The complete measured network scope and final recovery are required; no unrelated-service outage is accepted as success. Restoring alert recovers both services. Each rule reload clears the phase alert file and requires the previous engine to exit. This teaches IDS/IPS action, false-positive scope and rollback; it is not Cisco Secure Firewall, a threat feed or a malware benchmark. Nominal RAM is 2048 MiB. Primary references: https://docs.snort.org/start/inspection and https://docs.snort.org/rules/options/payload/http/method . The signature selects the actual HTTP-method sticky buffer and established client-to-server direction; it does not search a file/body buffer for an HTTP request method. Checksum validation stays enabled. The rule uses Snort3 block to stop the current packet and subsequent flow packets; drop alone affects only the current packet and is not treated as a persistent HTTP-session restriction. Action reference: https://docs.snort.org/rules/headers/actions and https://docs.snort.org/rules/options/general/service .

Use licensed reference images for cml-labs-inspection, net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- INSIDE eth1 <-> SENSOR eth1
- OUTSIDE eth1 <-> SENSOR eth2

| Node | Interface | Address |
| --- | --- | --- |
| INSIDE | eth1 | `198.18.0.10/24` |
| OUTSIDE | eth1 | `198.18.0.20/24` |
| OUTSIDE | eth1 | `198.18.0.21/24` |

## Tasks

1. Observe a real Snort3 alert while a deliberately benign matching request still succeeds.
2. Enable an overbroad inline flow block and distinguish application policy from link or server failure.
3. Narrow the rule by destination address so an independent virtual service recovers, then restore alert-only behavior.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| SENSOR | `cat /lab/start.status` | The actual Snort engine starts successfully before traffic checks. |
| SENSOR | `snort-cml -V` | The actual isolated inspection image supplies Snort3, not a mocked IDS API. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.0.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| OUTSIDE | `python3 /lab/t.py probe 198.18.0.21 --port 8081` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| INSIDE | `python3 /lab/t.py probe 198.18.0.20` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| INSIDE | `python3 /lab/t.py probe 198.18.0.20 --port 8081` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| INSIDE | `python3 /lab/t.py probe 198.18.0.21 --port 8081` | The actual plain-HTTP connection succeeds with the expected observed peer. |
| SENSOR | `grep -c '1000001' /lab/alert_fast.txt` | The real Snort alert file contains the selected signature from the current freshly reset phase. |
| INSIDE | `ping -c 3 -W 1 198.18.0.20` | Unrelated ICMP traverses the live inline sensor. |

## Transition: apply the overbroad inline flow block

On **SENSOR**:

```ios
/lab/mode broad
```

- SENSOR: `kill -0 $(cat /lab/snort.pid) && echo ENGINE_ALIVE` -- The current Snort process remains alive.
- INSIDE: `python3 /lab/t.py probe 198.18.0.20` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `python3 /lab/t.py probe 198.18.0.20 --port 8081` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `python3 /lab/t.py probe 198.18.0.21 --port 8081` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- SENSOR: `grep -c '1000001' /lab/alert_fast.txt` -- The real Snort alert file contains the selected signature from the current freshly reset phase.
- INSIDE: `ping -c 3 -W 1 198.18.0.20` -- Unrelated ICMP traverses the live inline sensor.
- OUTSIDE: `python3 /lab/t.py probe 198.18.0.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.0.21 --port 8081` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Transition: repair the rule scope without disabling enforcement

On **SENSOR**:

```ios
/lab/mode tuned
```

- SENSOR: `kill -0 $(cat /lab/snort.pid) && echo ENGINE_ALIVE` -- The current Snort process remains alive.
- INSIDE: `python3 /lab/t.py probe 198.18.0.21 --port 8081` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.0.20` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- INSIDE: `python3 /lab/t.py probe 198.18.0.20 --port 8081` -- The actual plain-HTTP connection is blocked while its separately checked server stays healthy.
- SENSOR: `grep -c '1000001' /lab/alert_fast.txt` -- The real Snort alert file contains the selected signature from the current freshly reset phase.
- INSIDE: `ping -c 3 -W 1 198.18.0.20` -- Unrelated ICMP traverses the live inline sensor.
- OUTSIDE: `python3 /lab/t.py probe 198.18.0.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.0.21 --port 8081` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Transition: restore alert-only inspection

On **SENSOR**:

```ios
/lab/mode ids
```

- SENSOR: `kill -0 $(cat /lab/snort.pid) && echo ENGINE_ALIVE` -- The current Snort process remains alive.
- INSIDE: `python3 /lab/t.py probe 198.18.0.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.0.20 --port 8081` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- INSIDE: `python3 /lab/t.py probe 198.18.0.21 --port 8081` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- SENSOR: `grep -c '1000001' /lab/alert_fast.txt` -- The real Snort alert file contains the selected signature from the current freshly reset phase.
- INSIDE: `ping -c 3 -W 1 198.18.0.20` -- Unrelated ICMP traverses the live inline sensor.
- OUTSIDE: `python3 /lab/t.py probe 198.18.0.20` -- The actual plain-HTTP connection succeeds with the expected observed peer.
- OUTSIDE: `python3 /lab/t.py probe 198.18.0.21 --port 8081` -- The actual plain-HTTP connection succeeds with the expected observed peer.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### SENSOR: boot.sh

```bash
#!/bin/bash
set -eu
mkdir -p /lab
ip link set eth1 up
ip link set eth2 up
ip link set eth1 promisc on
ip link set eth2 promisc on
cat >/lab/mode <<'CML_SNORT_MODE'
#!/bin/bash
set -eu
case "${1:-}" in
 ids) action=alert; target=198.18.0.20; destination=8080 ;;
 broad) action=block; target=any; destination=any ;;
 tuned) action=block; target=198.18.0.20; destination=8080 ;;
 *) echo INVALID_MODE; exit 2 ;;
esac
if [ -f /lab/snort.pid ]; then
 old=$(cat /lab/snort.pid)
 kill "$old" 2>/dev/null || true
 for i in $(seq 1 30); do
  if ! kill -0 "$old" 2>/dev/null; then break; fi
  sleep 0.1
 done
 if kill -0 "$old" 2>/dev/null; then echo OLD_ENGINE_RUNNING; exit 1; fi
fi
printf '%s tcp any any -> %s %s (msg:"CML benign HTTP fixture"; flow:to_server,established; http_method; content:"GET",fast_pattern; sid:1000001; rev:1;)\n' "$action" "$target" "$destination" >/lab/local.rules
: >/lab/alert_fast.txt
config=$(cat /opt/cml-inspection/config-path)
cd "$(dirname "$config")"
snort-cml -c "$config" -R /lab/local.rules -Q --daq afpacket -i eth1:eth2 -A alert_fast -l /lab --lua 'alert_fast={file=true}' >/lab/engine.log 2>&1 &
pid=$!
echo "$pid" >/lab/snort.pid
sleep 2
kill -0 "$pid"
echo SNORT_READY
CML_SNORT_MODE
chmod 700 /lab/mode
if ! /lab/mode ids >/lab/start.status 2>&1; then cat /lab/engine.log >>/lab/start.status; fi
echo READY >/dev/console
exit 0
```

### INSIDE: boot.sh

```bash
#!/bin/bash
set -eu
ip address add 198.18.0.10/24 dev eth1
ip link set eth1 up
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
python3 /lab/t.py serve 198.18.0.10 --label INSIDE >/lab/http.log 2>&1 &
python3 /lab/t.py serve 198.18.0.10 --port 8081 --label INSIDE >/lab/http-alt.log 2>&1 &
echo READY >/dev/console
exit 0
```

### OUTSIDE: boot.sh

```bash
#!/bin/bash
set -eu
ip address add 198.18.0.20/24 dev eth1
ip link set eth1 up
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
ip address add 198.18.0.21/24 dev eth1
python3 /lab/t.py serve 198.18.0.20 --label OUTSIDE >/lab/http.log 2>&1 &
python3 /lab/t.py serve 198.18.0.20 --port 8081 --label OUTSIDE >/lab/http-alt.log 2>&1 &
python3 /lab/t.py serve 198.18.0.21 --port 8081 --label OUTSIDE >/lab/http-control.log 2>&1 &
echo READY >/dev/console
exit 0
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
