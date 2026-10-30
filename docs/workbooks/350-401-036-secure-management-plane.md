# Secure Management Plane

## Scope and prerequisites

IOL-XE is administered by a dedicated Ubuntu OpenSSH client on an isolated point-to-point link. CML-LAB-ONLY and the SNMP credentials, when present, are PUBLIC disposable fixtures. The CML serial console stays privileged; network viewer sessions start at privilege1. The SSH helper uses an instance-local known-hosts file, accepts a new key only in this isolated exercise and rejects changed keys. This is not a production host-key enrollment design. Ephemeral RSA2048 key generation is an explicit setup phase. The source ACL contains an explicit deny-any entry so removing its only permit cannot turn an empty ACL into a permissive policy. Denial evidence distinguishes transport rejection from wrong credentials or changed host identity. This case withdraws and restores only the allowed VTY source while IP reachability and the actual enabled SSHv2 server remain healthy. A separate native Net-SNMP client authenticates/encrypts real requests on Ethernet0/1; SSH and SNMP view faults are tested independently. SHA1/AES128 are reference-image interoperability fixtures.

Use licensed reference images for iol-xe, net-tools, ubuntu in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Prepared management addressing and access policy; initialize the ephemeral host key in the documented setup phase before testing SSH. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> DEVBOX ens2
- R1 Ethernet0/1 <-> TOOLS eth1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| TOOLS | eth1 | `198.18.1.2/30` |

## Tasks

1. Initialize a fresh SSH host identity and validate actual network authentication, least privilege and closed legacy/web services.
2. Measure the intended management-policy failure while keeping independent positive controls healthy.
3. Restore the policy and verify authenticated service recovery using the same per-instance host identity.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.0.2 repeat 3` | The management IP path remains healthy independently of SSH admission. |

## Transition: initialize ephemeral management host key

On **R1**:

```ios
configure terminal
crypto key generate rsa general-keys label CML-LAB-SSH modulus 2048
ip ssh rsa keypair-name CML-LAB-SSH
end
```

- DEVBOX: `python3 /opt/cml-management/ssh_probe.py` -- Real SSH proves valid viewer login, privilege1, denied configuration, banner, wrong-password rejection and closed Telnet/HTTP ports.
- R1: `show ip ssh` -- The real SSHv2 server remains enabled.
- R1: `show running-config | include username viewer` -- The public fixture password is stored as a type9 secret.
- TOOLS: `python3 /lab/snmp_identity_probe.py healthy` -- Independent SNMPv3 authPriv remains healthy, including wrong-key rejection.

## Transition: withdraw the sole allowed SSH source

On **R1**:

```ios
configure terminal
ip access-list standard MGMT
no permit host 198.18.0.2
end
```

- DEVBOX: `python3 /opt/cml-management/ssh_policy_probe.py denied` -- The existing correct lab credential cannot establish SSH after the source policy is withdrawn; bad password or changed host key cannot count as this result.
- R1: `show access-lists MGMT` -- The explicit deny rule counts actual denied management attempts.
- R1: `ping 198.18.0.2 repeat 3` -- The management IP path remains healthy independently of SSH admission.
- R1: `show ip ssh` -- The real SSHv2 server remains enabled.
- TOOLS: `python3 /lab/snmp_identity_probe.py healthy` -- Independent SNMPv3 authPriv remains healthy, including wrong-key rejection.

## Transition: restore authorized SSH source

On **R1**:

```ios
configure terminal
ip access-list standard MGMT
10 permit host 198.18.0.2
end
```

- DEVBOX: `python3 /opt/cml-management/ssh_probe.py` -- Real SSH proves valid viewer login, privilege1, denied configuration, banner, wrong-password rejection and closed Telnet/HTTP ports.
- R1: `show ip ssh` -- The real SSHv2 server remains enabled.
- TOOLS: `python3 /lab/snmp_identity_probe.py healthy` -- Independent SNMPv3 authPriv remains healthy, including wrong-key rejection.

## Transition: restrict only SNMP identity visibility

On **R1**:

```ios
configure terminal
snmp-server view LABVIEW 1.3.6.1.2.1.1.5 excluded
end
```

- TOOLS: `python3 /lab/snmp_identity_probe.py restricted` -- Only sysName is excluded while authenticated uptime remains available.
- DEVBOX: `python3 /opt/cml-management/ssh_probe.py` -- Real SSH proves valid viewer login, privilege1, denied configuration, banner, wrong-password rejection and closed Telnet/HTTP ports.

## Transition: restore SNMP identity visibility

On **R1**:

```ios
configure terminal
snmp-server view LABVIEW 1.3.6.1.2.1.1.5 included
end
```

- TOOLS: `python3 /lab/snmp_identity_probe.py healthy` -- Independent SNMPv3 authPriv remains healthy, including wrong-key rejection.
- DEVBOX: `python3 /opt/cml-management/ssh_probe.py` -- Real SSH proves valid viewer login, privilege1, denied configuration, banner, wrong-password rejection and closed Telnet/HTTP ports.

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
ip domain name lab.example
username viewer privilege 1 algorithm-type scrypt secret CML-LAB-ONLY
no ip http server
no ip http secure-server
ip ssh version 2
ip ssh time-out 30
ip ssh authentication-retries 1
security passwords min-length 12
login on-failure log
ip access-list standard MGMT
 permit host 198.18.0.2
 exit
banner login @
CML-SSH-LAB
@
line console 0
 privilege level 15
 exit
line vty 0 4
 login local
 transport input ssh
 access-class MGMT in
 exec-timeout 5 0
 exit
no logging console
ip access-list standard MGMT
 deny any
 exit
interface Ethernet0/1
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
ip access-list standard SNMP-SOURCES
 permit 198.18.1.2
 exit
snmp-server engineID local 8000000903AABBCC000001
snmp-server view LABVIEW iso included
snmp-server view LABVIEW 1.3.6.1.2.1.1.5 included
snmp-server group LAB v3 priv read LABVIEW access SNMP-SOURCES
snmp-server user CML-SNMP LAB v3 auth sha Cml-Snmp-Auth-Only-983 priv aes 128 Cml-Snmp-Priv-Only-984
snmp-server location ISOLATED-CML-LAB
end
```

### DEVBOX

The YAML embeds the Ubuntu cloud-init configuration. The real network probe is [ssh_probe.py](../../examples/management/ssh_probe.py); it uses the installed OpenSSH client and only the public, exercise-only account.

### TOOLS: boot.sh

```bash
#!/bin/bash
set -eu
ip address add 198.18.1.2/30 dev eth1
ip link set eth1 up
mkdir -p /lab
echo '{"target":"198.18.1.1","expected_sysname":"R1.lab.example"}' > /lab/snmp.json
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
base64 -d > /lab/snmp_identity_probe.py <<'CML_EMBED_EXAMPLES_MANAGEMENT_SNMP_IDENTITY_PROBE_PY'
IiIiU05NUHYzIHZpZXcgY2hlY2tzIHdpdGggdGhlIGV4YWN0IGNvbmZpZ3VyZWQgbGFiIGRldmlj
ZSBpZGVudGl0eS4iIiIKCmltcG9ydCBhcmdwYXJzZQppbXBvcnQgaXBhZGRyZXNzCmltcG9ydCBq
c29uCmltcG9ydCByZQppbXBvcnQgc3VicHJvY2Vzcwpmcm9tIHBhdGhsaWIgaW1wb3J0IFBhdGgK
CmZyb20gc25tcF9wcm9iZSBpbXBvcnQgU1lTTkFNRSwgVVBUSU1FLCByZXF1ZXN0CgoKZGVmIHBy
b2JlKHRhcmdldCwgbW9kZSwgZXhwZWN0ZWRfbmFtZSk6CiAgICBvYnNlcnZhdGlvbnMgPSBbXQoK
ICAgIGRlZiBvYnNlcnZlKG9pZCwgcHJlZGljYXRlLCBsYWJlbCwgKipvcHRpb25zKToKICAgICAg
ICBjb2RlLCByZXNwb25zZSA9IHJlcXVlc3QodGFyZ2V0LCBvaWQsICoqb3B0aW9ucykKICAgICAg
ICBwYXNzZWQgPSBib29sKHByZWRpY2F0ZShjb2RlLCByZXNwb25zZSkpCiAgICAgICAgb2JzZXJ2
YXRpb25zLmFwcGVuZCh7ImNoZWNrIjogbGFiZWwsICJwYXNzZWQiOiBwYXNzZWQsICJyZXNwb25z
ZSI6IHJlc3BvbnNlfSkKICAgICAgICBpZiBub3QgcGFzc2VkOgogICAgICAgICAgICByYWlzZSBS
dW50aW1lRXJyb3IobGFiZWwgKyAiOiAiICsgcmVzcG9uc2UpCgogICAgdXB0aW1lID0gbGFtYmRh
IGNvZGUsIHRleHQ6IGNvZGUgPT0gMCBhbmQgYm9vbChyZS5zZWFyY2gociJUaW1ldGlja3M6XHMq
XChcZCtcKSIsIHRleHQpKQogICAgb2JzZXJ2ZShVUFRJTUUsIHVwdGltZSwgImF1dGhlbnRpY2F0
ZWQgZW5jcnlwdGVkIHVwdGltZSIpCiAgICBpZiBtb2RlID09ICJoZWFsdGh5IjoKICAgICAgICBv
YnNlcnZlKAogICAgICAgICAgICBTWVNOQU1FLAogICAgICAgICAgICBsYW1iZGEgY29kZSwgdGV4
dDogKAogICAgICAgICAgICAgICAgY29kZSA9PSAwCiAgICAgICAgICAgICAgICBhbmQgYm9vbChy
ZS5zZWFyY2gocidTVFJJTkc6XHMqIj8nICsgcmUuZXNjYXBlKGV4cGVjdGVkX25hbWUpICsgcici
P1xzKiQnLCB0ZXh0KSkKICAgICAgICAgICAgKSwKICAgICAgICAgICAgImV4YWN0IGNvbmZpZ3Vy
ZWQgc3lzTmFtZSIsCiAgICAgICAgKQogICAgZWxzZToKICAgICAgICBvYnNlcnZlKAogICAgICAg
ICAgICBTWVNOQU1FLAogICAgICAgICAgICBsYW1iZGEgY29kZSwgdGV4dDogKAogICAgICAgICAg
ICAgICAgY29kZSA9PSAwIGFuZCBib29sKHJlLnNlYXJjaChyIk5vIFN1Y2ggKD86T2JqZWN0fElu
c3RhbmNlKSIsIHRleHQsIHJlLklHTk9SRUNBU0UpKQogICAgICAgICAgICApLAogICAgICAgICAg
ICAiaWRlbnRpdHkgZXhjbHVkZWQgYnkgdmlldyIsCiAgICAgICAgKQogICAgb2JzZXJ2ZSgKICAg
ICAgICBVUFRJTUUsCiAgICAgICAgbGFtYmRhIGNvZGUsIHRleHQ6ICgKICAgICAgICAgICAgY29k
ZSAhPSAwCiAgICAgICAgICAgIGFuZCBib29sKHJlLnNlYXJjaChyImF1dGhlbnRpY2F0aW9uIGZh
aWx1cmV8VGltZW91dDogTm8gUmVzcG9uc2UiLCB0ZXh0LCByZS5JR05PUkVDQVNFKSkKICAgICAg
ICApLAogICAgICAgICJ3cm9uZyBrZXkgcmVqZWN0ZWQiLAogICAgICAgIHdyb25nX2F1dGg9VHJ1
ZSwKICAgICkKICAgIG9ic2VydmUoVVBUSU1FLCB1cHRpbWUsICJ2YWxpZCBjcmVkZW50aWFscyBz
dGlsbCB3b3JrIikKICAgIHJldHVybiB7InN0YXR1cyI6ICJwYXNzZWQiLCAibW9kZSI6IG1vZGUs
ICJvYnNlcnZhdGlvbnMiOiBvYnNlcnZhdGlvbnN9CgoKZGVmIG1haW4oKToKICAgIHBhcnNlciA9
IGFyZ3BhcnNlLkFyZ3VtZW50UGFyc2VyKGRlc2NyaXB0aW9uPV9fZG9jX18pCiAgICBwYXJzZXIu
YWRkX2FyZ3VtZW50KCJtb2RlIiwgY2hvaWNlcz0oImhlYWx0aHkiLCAicmVzdHJpY3RlZCIpKQog
ICAgYXJncyA9IHBhcnNlci5wYXJzZV9hcmdzKCkKICAgIGNvbmZpZyA9IGpzb24ubG9hZHMoUGF0
aCgiL2xhYi9zbm1wLmpzb24iKS5yZWFkX3RleHQoZW5jb2Rpbmc9InV0Zi04IikpCiAgICBpZiBp
cGFkZHJlc3MuaXBfYWRkcmVzcyhjb25maWdbInRhcmdldCJdKSBub3QgaW4gaXBhZGRyZXNzLmlw
X25ldHdvcmsoIjE5OC4xOC4wLjAvMTUiKToKICAgICAgICBwYXJzZXIuZXJyb3IoIk9ubHkgaXNv
bGF0ZWQgYmVuY2htYXJrLWFkZHJlc3MgZml4dHVyZXMgYXJlIHN1cHBvcnRlZCIpCiAgICB0cnk6
CiAgICAgICAgcmVwb3J0ID0gcHJvYmUoY29uZmlnWyJ0YXJnZXQiXSwgYXJncy5tb2RlLCBjb25m
aWdbImV4cGVjdGVkX3N5c25hbWUiXSkKICAgIGV4Y2VwdCAoT1NFcnJvciwgUnVudGltZUVycm9y
LCBzdWJwcm9jZXNzLlRpbWVvdXRFeHBpcmVkKSBhcyBleGM6CiAgICAgICAgcHJpbnQoanNvbi5k
dW1wcyh7InN0YXR1cyI6ICJmYWlsZWQiLCAiZXJyb3IiOiBzdHIoZXhjKX0pKQogICAgICAgIHJl
dHVybiAxCiAgICBwcmludChqc29uLmR1bXBzKHJlcG9ydCwgc29ydF9rZXlzPVRydWUpKQogICAg
cmV0dXJuIDAKCgppZiBfX25hbWVfXyA9PSAiX19tYWluX18iOgogICAgcmFpc2UgU3lzdGVtRXhp
dChtYWluKCkpCg==
CML_EMBED_EXAMPLES_MANAGEMENT_SNMP_IDENTITY_PROBE_PY
echo READY >/dev/console
exit 0
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
