# Syslog And SNMP

## Scope and prerequisites

An IOL-XE router is queried by the native net-tools image and sends syslog to the dedicated syslog-ng reference image. Native eth0 is the CML management interface; only eth1 is cabled to the lab. The SNMP helper uses the installed Net-SNMP binary, authenticates and encrypts each request, checks actual OID values and rechecks availability after the wrong-key negative control. SHA1/AES128 are explicit exercise interoperability choices; the passwords and engine ID are public lab fixtures. A router-to-receiver reachability check precedes the first test event so initial neighbor discovery cannot be mistaken for verified UDP delivery. The syslog listener uses IP_FREEBIND so it can start before CML applies the benchmark-address data interface. It accepts traffic only on that address. UDP delivery and view-based access are tested; physical throughput, durable SIEM storage and external time accuracy are not claimed.

Use licensed reference images for iol-xe, net-tools, syslog in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> TOOLS eth1
- R1 Ethernet0/1 <-> LOG eth1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| TOOLS | eth1 | `198.18.0.2/30` |
| LOG | eth1 | `198.18.1.2/30` |

## Tasks

1. Query a real router with SNMPv3 authPriv and reject incorrect authentication.
2. Exclude only sysName from the view while preserving authenticated uptime access.
3. Collect actual router syslog over UDP and verify selective withdrawal and restoration.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.1.2 repeat 3` | The remote logging path is reachable and its neighbor resolution is complete. |
| TOOLS | `python3 /lab/snmp_probe.py healthy` | Real authPriv uptime remains available; sysName follows the configured view and a wrong key is rejected. |

## Transition: emit baseline syslog

On **R1**:

```ios
send log 6 CML-LAB-SYSLOG-BASELINE
```

- LOG: `grep -c CML-LAB-SYSLOG-BASELINE /var/log/cml-lab.log` -- The receiver records the actual UDP message.

## Transition: hide only sysName

On **R1**:

```ios
configure terminal
snmp-server view LABVIEW 1.3.6.1.2.1.1.5 excluded
end
```

- TOOLS: `python3 /lab/snmp_probe.py restricted` -- Real authPriv uptime remains available; sysName follows the configured view and a wrong key is rejected.

## Transition: restore sysName view

On **R1**:

```ios
configure terminal
snmp-server view LABVIEW 1.3.6.1.2.1.1.5 included
end
```

- TOOLS: `python3 /lab/snmp_probe.py healthy` -- Real authPriv uptime remains available; sysName follows the configured view and a wrong key is rejected.

## Transition: withdraw remote logging

On **R1**:

```ios
configure terminal
no logging host 198.18.1.2 transport udp port 514
end
send log 6 CML-LAB-SYSLOG-WITHDRAWN
```

- R1: `show logging` -- The withdrawn event was generated locally.
- TOOLS: `python3 /lab/snmp_probe.py healthy` -- Real authPriv uptime remains available; sysName follows the configured view and a wrong key is rejected.

## Transition: observe settled logging withdrawal

On **LOG**:

```ios
sleep 3
```

- LOG: `grep -c CML-LAB-SYSLOG-BASELINE /var/log/cml-lab.log` -- The receiver records the actual UDP message.
- LOG: `grep -c CML-LAB-SYSLOG-WITHDRAWN /var/log/cml-lab.log` -- The receiver has no record of the withdrawn-forwarding test event.

## Transition: restore remote logging

On **R1**:

```ios
configure terminal
logging host 198.18.1.2 transport udp port 514
end
send log 6 CML-LAB-SYSLOG-RESTORED
```

- LOG: `grep -c CML-LAB-SYSLOG-RESTORED /var/log/cml-lab.log` -- The receiver records the actual UDP message.
- TOOLS: `python3 /lab/snmp_probe.py healthy` -- Real authPriv uptime remains available; sysName follows the configured view and a wrong key is rejected.

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
interface Ethernet0/0
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
interface Ethernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
ip access-list standard SNMP-SOURCES
 permit 198.18.0.2
 exit
snmp-server engineID local 8000000903AABBCC000001
snmp-server view LABVIEW iso included
snmp-server view LABVIEW 1.3.6.1.2.1.1.5 included
snmp-server group LAB v3 priv read LABVIEW access SNMP-SOURCES
snmp-server user CML-SNMP LAB v3 auth sha Cml-Snmp-Auth-Only-983 priv aes 128 Cml-Snmp-Priv-Only-984
snmp-server location ISOLATED-CML-LAB
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
mkdir -p /lab
echo '{"target":"198.18.0.1"}' > /lab/snmp.json
base64 -d > /lab/snmp_probe.py <<'CML_EMBED_EXAMPLES_MANAGEMENT_SNMP_PROBE_PY'
IiIiUmVhbCBOZXQtU05NUCBwcm9iZXMgZm9yIHRoZSBpc29sYXRlZCBTTk1QdjMgYXV0aFByaXYg
ZXhlcmNpc2UuCgpBbGwgY3JlZGVudGlhbHMgYmVsb3cgYXJlIGRlbGliZXJhdGVseSBwdWJsaWMg
dGVhY2hpbmcgZml4dHVyZXMuIE5vIGluc3RhbGxhdGlvbiwKbmV0d29yayBzY2FuIG9yIHByb2R1
Y3Rpb24gZW5kcG9pbnQgZGlzY292ZXJ5IGlzIHBlcmZvcm1lZCBieSB0aGlzIGNsaWVudC4KIiIi
CgppbXBvcnQgYXJncGFyc2UKaW1wb3J0IGpzb24KaW1wb3J0IHJlCmltcG9ydCBzdWJwcm9jZXNz
CmltcG9ydCBzeXMKZnJvbSBwYXRobGliIGltcG9ydCBQYXRoCgpTWVNOQU1FID0gIi4xLjMuNi4x
LjIuMS4xLjUuMCIKVVBUSU1FID0gIi4xLjMuNi4xLjIuMS4xLjMuMCIKQVVUSCA9ICJDbWwtU25t
cC1BdXRoLU9ubHktOTgzIgpQUklWID0gIkNtbC1Tbm1wLVByaXYtT25seS05ODQiCgoKZGVmIHJl
cXVlc3QodGFyZ2V0LCBvaWQsICosIHdyb25nX2F1dGg9RmFsc2UpOgogICAgY29tbWFuZCA9IFsK
ICAgICAgICAic25tcGdldCIsCiAgICAgICAgIi12MyIsCiAgICAgICAgIi1sIiwKICAgICAgICAi
YXV0aFByaXYiLAogICAgICAgICItdSIsCiAgICAgICAgIkNNTC1TTk1QIiwKICAgICAgICAiLWEi
LAogICAgICAgICJTSEEiLAogICAgICAgICItQSIsCiAgICAgICAgIldyb25nLWF1dGgtb25seS05
OTkiIGlmIHdyb25nX2F1dGggZWxzZSBBVVRILAogICAgICAgICIteCIsCiAgICAgICAgIkFFUyIs
CiAgICAgICAgIi1YIiwKICAgICAgICBQUklWLAogICAgICAgICItdCIsCiAgICAgICAgIjIiLAog
ICAgICAgICItciIsCiAgICAgICAgIjAiLAogICAgICAgICItT24iLAogICAgICAgIHRhcmdldCwK
ICAgICAgICBvaWQsCiAgICBdCiAgICByZXN1bHQgPSBzdWJwcm9jZXNzLnJ1bihjb21tYW5kLCBj
YXB0dXJlX291dHB1dD1UcnVlLCB0ZXh0PVRydWUsIHRpbWVvdXQ9OCwgY2hlY2s9RmFsc2UpCiAg
ICByZXR1cm4gcmVzdWx0LnJldHVybmNvZGUsIChyZXN1bHQuc3Rkb3V0ICsgcmVzdWx0LnN0ZGVy
cikuc3RyaXAoKQoKCmRlZiBwcm9iZSh0YXJnZXQsIG1vZGUpOgogICAgb2JzZXJ2YXRpb25zID0g
W10KCiAgICBkZWYgb2JzZXJ2ZShvaWQsIHByZWRpY2F0ZSwgbGFiZWwsICoqb3B0aW9ucyk6CiAg
ICAgICAgY29kZSwgb3V0cHV0ID0gcmVxdWVzdCh0YXJnZXQsIG9pZCwgKipvcHRpb25zKQogICAg
ICAgIHBhc3NlZCA9IGJvb2wocHJlZGljYXRlKGNvZGUsIG91dHB1dCkpCiAgICAgICAgb2JzZXJ2
YXRpb25zLmFwcGVuZCgKICAgICAgICAgICAgeyJjaGVjayI6IGxhYmVsLCAicGFzc2VkIjogcGFz
c2VkLCAicmV0dXJuY29kZSI6IGNvZGUsICJyZXNwb25zZSI6IG91dHB1dH0KICAgICAgICApCiAg
ICAgICAgaWYgbm90IHBhc3NlZDoKICAgICAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKCJOZXR3
b3JrIGFzc2VydGlvbiBmYWlsZWQ6ICIgKyBsYWJlbCkKCiAgICBvYnNlcnZlKAogICAgICAgIFVQ
VElNRSwKICAgICAgICBsYW1iZGEgYywgczogYyA9PSAwIGFuZCBib29sKHJlLnNlYXJjaChyIlRp
bWV0aWNrczpccypcKFxkK1wpIiwgcykpLAogICAgICAgICJhdXRoZW50aWNhdGVkIGVuY3J5cHRl
ZCB1cHRpbWUiLAogICAgKQogICAgaWYgbW9kZSA9PSAiaGVhbHRoeSI6CiAgICAgICAgb2JzZXJ2
ZSgKICAgICAgICAgICAgU1lTTkFNRSwKICAgICAgICAgICAgbGFtYmRhIGMsIHM6IGMgPT0gMCBh
bmQgYm9vbChyZS5zZWFyY2gocidTVFJJTkc6XHMqIj9SMSI/XHMqJCcsIHMpKSwKICAgICAgICAg
ICAgInZpc2libGUgc3lzTmFtZSIsCiAgICAgICAgKQogICAgZWxzZToKICAgICAgICBvYnNlcnZl
KAogICAgICAgICAgICBTWVNOQU1FLAogICAgICAgICAgICBsYW1iZGEgYywgczogKAogICAgICAg
ICAgICAgICAgYyA9PSAwIGFuZCBib29sKHJlLnNlYXJjaChyIk5vIFN1Y2ggKD86T2JqZWN0fElu
c3RhbmNlKSIsIHMsIHJlLklHTk9SRUNBU0UpKQogICAgICAgICAgICApLAogICAgICAgICAgICAi
dmlldyBleGNsdWRlcyBzeXNOYW1lIiwKICAgICAgICApCiAgICBvYnNlcnZlKAogICAgICAgIFVQ
VElNRSwKICAgICAgICBsYW1iZGEgYywgczogKAogICAgICAgICAgICBjICE9IDAKICAgICAgICAg
ICAgYW5kIGJvb2wocmUuc2VhcmNoKHIiYXV0aGVudGljYXRpb24gZmFpbHVyZXxUaW1lb3V0OiBO
byBSZXNwb25zZSIsIHMsIHJlLklHTk9SRUNBU0UpKQogICAgICAgICksCiAgICAgICAgIndyb25n
IGF1dGhlbnRpY2F0aW9uIGtleSBpcyByZWplY3RlZCIsCiAgICAgICAgd3JvbmdfYXV0aD1UcnVl
LAogICAgKQogICAgb2JzZXJ2ZSgKICAgICAgICBVUFRJTUUsCiAgICAgICAgbGFtYmRhIGMsIHM6
IGMgPT0gMCBhbmQgYm9vbChyZS5zZWFyY2gociJUaW1ldGlja3M6XHMqXChcZCtcKSIsIHMpKSwK
ICAgICAgICAiYWdlbnQgc3RpbGwgYW5zd2VycyB2YWxpZCBjcmVkZW50aWFscyIsCiAgICApCiAg
ICByZXR1cm4geyJzdGF0dXMiOiAicGFzc2VkIiwgIm1vZGUiOiBtb2RlLCAidGFyZ2V0IjogdGFy
Z2V0LCAib2JzZXJ2YXRpb25zIjogb2JzZXJ2YXRpb25zfQoKCmRlZiBtYWluKCk6CiAgICBwYXJz
ZXIgPSBhcmdwYXJzZS5Bcmd1bWVudFBhcnNlcihkZXNjcmlwdGlvbj1fX2RvY19fKQogICAgcGFy
c2VyLmFkZF9hcmd1bWVudCgibW9kZSIsIGNob2ljZXM9KCJoZWFsdGh5IiwgInJlc3RyaWN0ZWQi
KSkKICAgIGFyZ3MgPSBwYXJzZXIucGFyc2VfYXJncygpCiAgICBjb25maWcgPSBqc29uLmxvYWRz
KFBhdGgoIi9sYWIvc25tcC5qc29uIikucmVhZF90ZXh0KGVuY29kaW5nPSJ1dGYtOCIpKQogICAg
dHJ5OgogICAgICAgIHJlcG9ydCA9IHByb2JlKGNvbmZpZ1sidGFyZ2V0Il0sIGFyZ3MubW9kZSkK
ICAgIGV4Y2VwdCAoT1NFcnJvciwgUnVudGltZUVycm9yLCBzdWJwcm9jZXNzLlRpbWVvdXRFeHBp
cmVkKSBhcyBleGM6CiAgICAgICAgcHJpbnQoanNvbi5kdW1wcyh7InN0YXR1cyI6ICJmYWlsZWQi
LCAiZXJyb3IiOiBzdHIoZXhjKX0pKQogICAgICAgIHJldHVybiAxCiAgICBwcmludChqc29uLmR1
bXBzKHJlcG9ydCwgc29ydF9rZXlzPVRydWUpKQogICAgcmV0dXJuIDAKCgppZiBfX25hbWVfXyA9
PSAiX19tYWluX18iOgogICAgc3lzLmV4aXQobWFpbigpKQo=
CML_EMBED_EXAMPLES_MANAGEMENT_SNMP_PROBE_PY
echo READY >/dev/console
exit 0
```

### LOG: syslog-ng.conf

```text
@version: 3.38
options { flush_lines(0); };
source s_network { udp(ip("198.18.1.2") ip-freebind(yes) port(514)); };
destination d_lab { file("/var/log/cml-lab.log"); };
log { source(s_network); destination(d_lab); };
```

### LOG: boot.sh

```bash
#!/bin/bash
set -eu
ip address add 198.18.1.2/30 dev eth1
ip link set eth1 up
mkdir -p /lab
echo READY >/dev/console
exit 0
```

## Readable helper sources

[SNMP network probe](../../examples/management/snmp_probe.py). `python scripts/embed_webhook.py --check` verifies the exact source bytes embedded in the topology; an outdated copy is rejected.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
