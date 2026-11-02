# Threat Path: Exposed Management and Scoped Admission

## Scope and prerequisites

This exercise instantiates one specific threat path, rather than claiming a general vulnerability scan. The asset is an IOL-L2 management CLI; DEVBOX is the management-VLAN client and UNTRUST is a separate routed source VLAN. A deliberately public viewer credential grants actual privilege1. Initially the VTY source ACL is unbound, so the independently sourced client with that known credential must establish a real SSH session. The same probe must still reject a wrong password, deny configuration access at privilege1, observe the expected banner, and find disabled Telnet/HTTP/HTTPS listeners. This distinguishes management exposure from credential authentication and privilege impact: an exposed SSH port is not itself proof of authentication bypass or administrative control.

Bind the exact management-source ACL to actual VTY0-4. UNTRUST must now fail by transport policy rather than a bad password/host-key error, the real deny counter must increase, and its management-IP ping must still succeed. DEVBOX must retain actual SSH login and its privilege restrictions. Removing only the binding deliberately reopens the same threat path without changing credentials, privilege or IP reachability. Restore the binding and require the independently observed denial plus healthy authorized/IP controls again. The before/after matrix is an explicit attack-surface and control-effectiveness assessment for this finite lab, not a claim of full device hardening, exploitable CVEs, password strength or complete threat coverage.

The immutable existing OpenSSH probes and their public exercise askpass fixture are reused without source changes. A disposable RSA2048 host key is generated in the copy; first-use host-key learning is restricted to this isolated experiment and is not out-of-band identity validation or a production cryptographic recommendation. No real password, Internet connector, existing user lab or production service is used. Nominal RAM is4096MiB across the switch, Ubuntu DEVBOX and native toolbox UNTRUST. All keys and experimental state disappear when the copy is wiped.


Use licensed reference images for cml-labs-toolbox, ioll2-xe, ubuntu in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> DEVBOX ens2
- R1 Ethernet0/1 <-> UNTRUST eth1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Vlan10 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Vlan20 | `ip address 198.18.1.1 255.255.255.252` |
| UNTRUST | eth1 | `198.18.1.2/30` |

## Threat and evidence matrix

| Question | Independent evidence | Scope |
| --- | --- | --- |
| Can the other VLAN reach management IP? | Actual three-packet IP probe | Reachability alone does not imply SSH authorization. |
| Can a known-credential source enter SSH? | Actual OpenSSH login, not a TCP-open check | Only the declared classroom identity is tested. |
| Does login grant administrative configuration? | Actual privilege1 and denied configuration probe | No exploit or privilege escalation is simulated. |
| Does the source boundary close that path? | Transport-policy denial, real ACL hit counter, trusted SSH and untrusted IP controls | Authentication/host-key errors do not count as source-policy success. |

## Tasks

1. Model a concrete known-credential management-exposure path across independent source VLANs.
2. Distinguish actual transport admission, password authentication and privilege1 configuration denial.
3. Measure closure/reopening/recovery using real SSH outcomes, source-ACL counters and positive reachability controls.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `show interfaces Vlan10` | The management SVI is operational. |
| UNTRUST | `ping -c 3 -W 2 198.18.0.1` | The independent source retains real IP connectivity to the management SVI. |

## Transition: establish identity and measure the initially exposed management path

On **R1**:

```ios
configure terminal
crypto key generate rsa general-keys label CML-LAB-SSH modulus 2048
ip ssh rsa keypair-name CML-LAB-SSH
end
```

- UNTRUST: `python3 /opt/cml-management/ssh_probe.py` -- The same untrusted source actually authenticates and obtains a privilege1 SSH session when the source allowlist is bypassed; password and privilege restrictions remain effective.
- DEVBOX: `python3 /opt/cml-management/ssh_probe.py` -- The authorized management VLAN proves actual SSH login, viewer privilege1, denied configuration, banner, wrong-password rejection and closed legacy/web listeners.
- UNTRUST: `ping -c 3 -W 2 198.18.0.1` -- The independent source retains real IP connectivity to the management SVI.

## Transition: close the identified management-source exposure

On **R1**:

```ios
configure terminal
line vty 0 4
access-class MGMT in
end
```

- UNTRUST: `python3 /opt/cml-management/ssh_policy_probe.py denied` -- The independently sourced client is rejected by transport policy, not a bad password or a host-key error.
- R1: `show access-lists MGMT` -- The actual source-deny rule counts attempts from the untrusted VLAN.
- DEVBOX: `python3 /opt/cml-management/ssh_probe.py` -- The authorized management VLAN proves actual SSH login, viewer privilege1, denied configuration, banner, wrong-password rejection and closed legacy/web listeners.
- UNTRUST: `ping -c 3 -W 2 198.18.0.1` -- The independent source retains real IP connectivity to the management SVI.

## Transition: reproduce the exposure by removing only its source binding

On **R1**:

```ios
configure terminal
line vty 0 4
no access-class MGMT in
end
```

- UNTRUST: `python3 /opt/cml-management/ssh_probe.py` -- The same untrusted source actually authenticates and obtains a privilege1 SSH session when the source allowlist is bypassed; password and privilege restrictions remain effective.
- DEVBOX: `python3 /opt/cml-management/ssh_probe.py` -- The authorized management VLAN proves actual SSH login, viewer privilege1, denied configuration, banner, wrong-password rejection and closed legacy/web listeners.
- UNTRUST: `ping -c 3 -W 2 198.18.0.1` -- The independent source retains real IP connectivity to the management SVI.

## Transition: restore the source boundary and validate residual access

On **R1**:

```ios
configure terminal
line vty 0 4
access-class MGMT in
end
```

- UNTRUST: `python3 /opt/cml-management/ssh_policy_probe.py denied` -- The independently sourced client is rejected by transport policy, not a bad password or a host-key error.
- R1: `show access-lists MGMT` -- The actual source-deny rule counts attempts from the untrusted VLAN.
- DEVBOX: `python3 /opt/cml-management/ssh_probe.py` -- The authorized management VLAN proves actual SSH login, viewer privilege1, denied configuration, banner, wrong-password rejection and closed legacy/web listeners.
- UNTRUST: `ping -c 3 -W 2 198.18.0.1` -- The independent source retains real IP connectivity to the management SVI.

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
vtp mode transparent
spanning-tree mode rapid-pvst
interface range Ethernet0/0 - 3
 shutdown
 exit
no logging console
ip routing
ip domain name lab.example
username viewer privilege 1 algorithm-type scrypt secret CML-LAB-ONLY
security passwords min-length 12
no ip http server
no ip http secure-server
ip ssh version 2
ip ssh time-out 30
ip ssh authentication-retries 1
ip access-list standard MGMT
 10 permit host 198.18.0.2
 20 deny any
 exit
banner login @
CML-SSH-LAB
@
vlan 10
 name MANAGEMENT
 exit
vlan 20
 name OTHER
 exit
interface Ethernet0/0
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 no shutdown
 exit
interface Ethernet0/1
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
 no shutdown
 exit
interface Vlan10
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
interface Vlan20
 ip address 198.18.1.1 255.255.255.252
 no shutdown
 exit
line console 0
 privilege level 15
 exit
line vty 0 4
 login local
 transport input ssh
 exec-timeout 5 0
 exit
end
```

### DEVBOX

The YAML embeds the Ubuntu cloud-init configuration. The real network probe is [ssh_probe.py](../../examples/management/ssh_probe.py); it uses the installed OpenSSH client and only the public, exercise-only account.

### UNTRUST: boot.sh

```bash
#!/bin/bash
set -eu
ip address add 198.18.1.2/30 dev eth1
ip link set eth1 up
ip route add 198.18.0.0/30 via 198.18.1.1
mkdir -p /lab /opt/cml-management
base64 -d > /opt/cml-management/askpass.sh <<'ASKPASS'
IyEvYmluL3NoCnByaW50ZiAnJXNcbicgIiRDTUxfVEVTVF9QQVNTV09SRCIK
ASKPASS
chmod 700 /opt/cml-management/askpass.sh
base64 -d > /opt/cml-management/ssh_probe.py <<'CML_EMBED_EXAMPLES_MANAGEMENT_SSH_PROBE_PY'
IiIiRXhlcmNpc2Utb25seSBPcGVuU1NIIHByb2JlOyBubyBwcm9kdWN0aW9uIGNyZWRlbnRpYWxz
IG9yIHByaXZhdGUga2V5cy4iIiIKCmltcG9ydCBhcmdwYXJzZQppbXBvcnQgaXBhZGRyZXNzCmlt
cG9ydCBqc29uCmltcG9ydCBvcwppbXBvcnQgcmUKaW1wb3J0IHNvY2tldAppbXBvcnQgc3VicHJv
Y2Vzcwpmcm9tIHBhdGhsaWIgaW1wb3J0IFBhdGgKCkRFTU9fUEFTU1dPUkQgPSAiQ01MLUxBQi1P
TkxZIgoKCmRlZiBzZXNzaW9uKGhvc3QsIHBhc3N3b3JkLCBjb21tYW5kcyk6CiAgICBlbnZpcm9u
bWVudCA9IHsKICAgICAgICAqKm9zLmVudmlyb24sCiAgICAgICAgIlNTSF9BU0tQQVNTX1JFUVVJ
UkUiOiAiZm9yY2UiLAogICAgICAgICJTU0hfQVNLUEFTUyI6ICIvb3B0L2NtbC1tYW5hZ2VtZW50
L2Fza3Bhc3Muc2giLAogICAgICAgICJDTUxfVEVTVF9QQVNTV09SRCI6IHBhc3N3b3JkLAogICAg
fQogICAgYXJncyA9IFsKICAgICAgICAic3NoIiwKICAgICAgICAiLXR0IiwKICAgICAgICAiLUYi
LAogICAgICAgICJub25lIiwKICAgICAgICAiLW8iLAogICAgICAgICJTdHJpY3RIb3N0S2V5Q2hl
Y2tpbmc9YWNjZXB0LW5ldyIsCiAgICAgICAgIi1vIiwKICAgICAgICAiVXNlcktub3duSG9zdHNG
aWxlPS90bXAvY21sLW1hbmFnZW1lbnQta25vd24taG9zdHMiLAogICAgICAgICItbyIsCiAgICAg
ICAgIlByZWZlcnJlZEF1dGhlbnRpY2F0aW9ucz1wYXNzd29yZCIsCiAgICAgICAgIi1vIiwKICAg
ICAgICAiUHVia2V5QXV0aGVudGljYXRpb249bm8iLAogICAgICAgICItbyIsCiAgICAgICAgIk51
bWJlck9mUGFzc3dvcmRQcm9tcHRzPTEiLAogICAgICAgICItbyIsCiAgICAgICAgIkNvbm5lY3RU
aW1lb3V0PTUiLAogICAgICAgIGYidmlld2VyQHtob3N0fSIsCiAgICBdCiAgICByZXN1bHQgPSBz
dWJwcm9jZXNzLnJ1bigKICAgICAgICBhcmdzLAogICAgICAgIGlucHV0PSJcciIuam9pbihjb21t
YW5kcykgKyAiXHIiLAogICAgICAgIGNhcHR1cmVfb3V0cHV0PVRydWUsCiAgICAgICAgdGV4dD1U
cnVlLAogICAgICAgIHRpbWVvdXQ9MTIsCiAgICAgICAgZW52PWVudmlyb25tZW50LAogICAgICAg
IHN0YXJ0X25ld19zZXNzaW9uPVRydWUsCiAgICAgICAgY2hlY2s9RmFsc2UsCiAgICApCiAgICBy
ZXR1cm4gcmVzdWx0LnJldHVybmNvZGUsIHJlc3VsdC5zdGRvdXQgKyByZXN1bHQuc3RkZXJyCgoK
ZGVmIGNsb3NlZChob3N0LCBwb3J0KToKICAgIHRyeToKICAgICAgICB3aXRoIHNvY2tldC5jcmVh
dGVfY29ubmVjdGlvbigoaG9zdCwgcG9ydCksIHRpbWVvdXQ9Mik6CiAgICAgICAgICAgIHJldHVy
biBGYWxzZQogICAgZXhjZXB0IE9TRXJyb3I6CiAgICAgICAgcmV0dXJuIFRydWUKCgpkZWYgbWFp
bigpOgogICAgcGFyc2VyID0gYXJncGFyc2UuQXJndW1lbnRQYXJzZXIoZGVzY3JpcHRpb249X19k
b2NfXykKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0taG9zdCIsIGRlZmF1bHQ9IjE5OC4xOC4w
LjEiKQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLS1iYW5uZXIiLCBkZWZhdWx0PSJDTUwtU1NI
LUxBQiIpCiAgICBhcmdzID0gcGFyc2VyLnBhcnNlX2FyZ3MoKQogICAgYWRkcmVzcyA9IGlwYWRk
cmVzcy5pcF9hZGRyZXNzKGFyZ3MuaG9zdCkKICAgIGlmIGFkZHJlc3Mgbm90IGluIGlwYWRkcmVz
cy5pcF9uZXR3b3JrKCIxOTguMTguMC4wLzE1Iik6CiAgICAgICAgcGFyc2VyLmVycm9yKCJUaGlz
IGZpeHR1cmUgaXMgcmVzdHJpY3RlZCB0byBpdHMgaXNvbGF0ZWQgYmVuY2htYXJrLWFkZHJlc3Mg
bGFiIikKICAgIGNvbW1hbmRzID0gWwogICAgICAgICJ0ZXJtaW5hbCBsZW5ndGggMCIsCiAgICAg
ICAgInNob3cgcHJpdmlsZWdlIiwKICAgICAgICAic2hvdyBjbG9jayIsCiAgICAgICAgImNvbmZp
Z3VyZSB0ZXJtaW5hbCIsCiAgICAgICAgImV4aXQiLAogICAgICAgICJleGl0IiwKICAgIF0KICAg
IGdvb2RfY29kZSwgZ29vZF9vdXRwdXQgPSBzZXNzaW9uKHN0cihhZGRyZXNzKSwgREVNT19QQVNT
V09SRCwgY29tbWFuZHMpCiAgICBiYWRfY29kZSwgYmFkX291dHB1dCA9IHNlc3Npb24oc3RyKGFk
ZHJlc3MpLCAiSU5DT1JSRUNULUxBQi1QQVNTV09SRCIsIFsiZXhpdCJdKQogICAgY2hlY2tzID0g
ewogICAgICAgICJ2YWxpZF9wYXNzd29yZF9zZXNzaW9uIjogZ29vZF9jb2RlID09IDAsCiAgICAg
ICAgInZpZXdlcl9wcml2aWxlZ2Vfb25lIjogYm9vbChyZS5zZWFyY2gociJDdXJyZW50IHByaXZp
bGVnZSBsZXZlbCBpc1xzKzFcYiIsIGdvb2Rfb3V0cHV0KSksCiAgICAgICAgImV4ZWNfY2xvY2tf
cmVzcG9uc2UiOiBib29sKHJlLnNlYXJjaChyIlxkezJ9OlxkezJ9OlxkezJ9IiwgZ29vZF9vdXRw
dXQpKSwKICAgICAgICAiY29uZmlndXJhdGlvbl9kZW5pZWQiOiBib29sKAogICAgICAgICAgICBy
ZS5zZWFyY2goCiAgICAgICAgICAgICAgICByIkludmFsaWQgaW5wdXR8bm90IGF1dGhvcml6ZWR8
YXV0aG9yaXphdGlvbiBmYWlsZWQiLCBnb29kX291dHB1dCwgcmUuSUdOT1JFQ0FTRQogICAgICAg
ICAgICApCiAgICAgICAgKSwKICAgICAgICAibG9naW5fYmFubmVyIjogYXJncy5iYW5uZXIgaW4g
Z29vZF9vdXRwdXQsCiAgICAgICAgIndyb25nX3Bhc3N3b3JkX3JlamVjdGVkIjogYmFkX2NvZGUg
IT0gMAogICAgICAgIGFuZCBib29sKHJlLnNlYXJjaChyIlBlcm1pc3Npb24gZGVuaWVkfEF1dGhl
bnRpY2F0aW9uIGZhaWxlZCIsIGJhZF9vdXRwdXQsIHJlLklHTk9SRUNBU0UpKSwKICAgICAgICAi
dGVsbmV0X2Nsb3NlZCI6IGNsb3NlZChzdHIoYWRkcmVzcyksIDIzKSwKICAgICAgICAiaHR0cF9j
bG9zZWQiOiBjbG9zZWQoc3RyKGFkZHJlc3MpLCA4MCksCiAgICAgICAgImh0dHBzX2Nsb3NlZCI6
IGNsb3NlZChzdHIoYWRkcmVzcyksIDQ0MyksCiAgICB9CiAgICBpZiBub3QgYWxsKGNoZWNrcy52
YWx1ZXMoKSk6CiAgICAgICAgUGF0aCgiL3RtcC9jbWwtbWFuYWdlbWVudC1kZWJ1Zy5qc29uIiku
d3JpdGVfdGV4dCgKICAgICAgICAgICAganNvbi5kdW1wcygKICAgICAgICAgICAgICAgIHsKICAg
ICAgICAgICAgICAgICAgICAiZ29vZF9jb2RlIjogZ29vZF9jb2RlLAogICAgICAgICAgICAgICAg
ICAgICJnb29kX291dHB1dCI6IGdvb2Rfb3V0cHV0LAogICAgICAgICAgICAgICAgICAgICJiYWRf
Y29kZSI6IGJhZF9jb2RlLAogICAgICAgICAgICAgICAgICAgICJiYWRfb3V0cHV0IjogYmFkX291
dHB1dCwKICAgICAgICAgICAgICAgIH0sCiAgICAgICAgICAgICAgICBpbmRlbnQ9MiwKICAgICAg
ICAgICAgKQogICAgICAgICAgICArICJcbiIsCiAgICAgICAgICAgIGVuY29kaW5nPSJ1dGYtOCIs
CiAgICAgICAgKQogICAgcHJpbnQoanNvbi5kdW1wcyh7InBhc3NlZCI6IGFsbChjaGVja3MudmFs
dWVzKCkpLCAiY2hlY2tzIjogY2hlY2tzfSwgc29ydF9rZXlzPVRydWUpKQogICAgcmV0dXJuIDAg
aWYgYWxsKGNoZWNrcy52YWx1ZXMoKSkgZWxzZSAxCgoKaWYgX19uYW1lX18gPT0gIl9fbWFpbl9f
IjoKICAgIHJhaXNlIFN5c3RlbUV4aXQobWFpbigpKQo=
CML_EMBED_EXAMPLES_MANAGEMENT_SSH_PROBE_PY
base64 -d > /opt/cml-management/ssh_policy_probe.py <<'CML_EMBED_EXAMPLES_MANAGEMENT_SSH_POLICY_PROBE_PY'
IiIiT2JzZXJ2ZSBkaXNwb3NhYmxlIGxhYiBTU0ggcG9saWN5OyBuZXZlciBwcmludCBzZXNzaW9u
IG91dHB1dCBvciBjcmVkZW50aWFscy4iIiIKCmltcG9ydCBhcmdwYXJzZQppbXBvcnQgaXBhZGRy
ZXNzCmltcG9ydCBqc29uCmltcG9ydCByZQppbXBvcnQgc3VicHJvY2VzcwoKZnJvbSBzc2hfcHJv
YmUgaW1wb3J0IERFTU9fUEFTU1dPUkQsIHNlc3Npb24KCgpkZWYgYXNzZXNzKG1vZGUsIGNvZGUs
IG91dHB1dCk6CiAgICBpZiBtb2RlID09ICJkZW5pZWQiOgogICAgICAgIHJldHVybiB7CiAgICAg
ICAgICAgICJzZXNzaW9uX3JlamVjdGVkIjogY29kZSAhPSAwLAogICAgICAgICAgICAidHJhbnNw
b3J0X3BvbGljeV9yZWplY3Rpb24iOiBib29sKAogICAgICAgICAgICAgICAgcmUuc2VhcmNoKHIi
Y29ubmVjdGlvbiAoPzpjbG9zZWR8cmVzZXR8cmVmdXNlZHx0aW1lZCBvdXQpIiwgb3V0cHV0LCBy
ZS5JR05PUkVDQVNFKQogICAgICAgICAgICApLAogICAgICAgICAgICAibm90X2FuX2F1dGhlbnRp
Y2F0aW9uX29yX2hvc3Rfa2V5X2ZhaWx1cmUiOiBub3QgYm9vbCgKICAgICAgICAgICAgICAgIHJl
LnNlYXJjaCgKICAgICAgICAgICAgICAgICAgICByInBlcm1pc3Npb24gZGVuaWVkfGF1dGhlbnRp
Y2F0aW9uIGZhaWxlZHxpZGVudGlmaWNhdGlvbiBoYXMgY2hhbmdlZCIKICAgICAgICAgICAgICAg
ICAgICByInxob3N0IGtleSB2ZXJpZmljYXRpb24gZmFpbGVkfGN1cnJlbnQgcHJpdmlsZWdlIGxl
dmVsfFIxWz4jXSIsCiAgICAgICAgICAgICAgICAgICAgb3V0cHV0LAogICAgICAgICAgICAgICAg
ICAgIHJlLklHTk9SRUNBU0UsCiAgICAgICAgICAgICAgICApCiAgICAgICAgICAgICksCiAgICAg
ICAgfQogICAgaWYgbW9kZSA9PSAiZWxldmF0ZWQiOgogICAgICAgIHJldHVybiB7CiAgICAgICAg
ICAgICJhdXRoZW50aWNhdGVkX3Nlc3Npb24iOiBjb2RlID09IDAsCiAgICAgICAgICAgICJwcml2
aWxlZ2VfZmlmdGVlbiI6IGJvb2wocmUuc2VhcmNoKHIiQ3VycmVudCBwcml2aWxlZ2UgbGV2ZWwg
aXNccysxNVxiIiwgb3V0cHV0KSksCiAgICAgICAgICAgICJjb25maWd1cmF0aW9uX21vZGVfYWNj
ZXNzIjogYm9vbChyZS5zZWFyY2gociIoP20pXlIxXChjb25maWdcKSMiLCBvdXRwdXQpKSwKICAg
ICAgICB9CiAgICByYWlzZSBWYWx1ZUVycm9yKCJVbmtub3duIGV4ZXJjaXNlIHBvbGljeSBtb2Rl
IikKCgpkZWYgbWFpbigpOgogICAgcGFyc2VyID0gYXJncGFyc2UuQXJndW1lbnRQYXJzZXIoZGVz
Y3JpcHRpb249X19kb2NfXykKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIm1vZGUiLCBjaG9pY2Vz
PSgiZGVuaWVkIiwgImVsZXZhdGVkIikpCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItLWhvc3Qi
LCBkZWZhdWx0PSIxOTguMTguMC4xIikKICAgIGFyZ3MgPSBwYXJzZXIucGFyc2VfYXJncygpCiAg
ICBhZGRyZXNzID0gaXBhZGRyZXNzLmlwX2FkZHJlc3MoYXJncy5ob3N0KQogICAgaWYgYWRkcmVz
cyBub3QgaW4gaXBhZGRyZXNzLmlwX25ldHdvcmsoIjE5OC4xOC4wLjAvMTUiKToKICAgICAgICBw
YXJzZXIuZXJyb3IoIk9ubHkgaXNvbGF0ZWQgYmVuY2htYXJrLWFkZHJlc3MgZml4dHVyZXMgYXJl
IHN1cHBvcnRlZCIpCiAgICBjb21tYW5kcyA9IFsidGVybWluYWwgbGVuZ3RoIDAiLCAic2hvdyBw
cml2aWxlZ2UiXQogICAgaWYgYXJncy5tb2RlID09ICJlbGV2YXRlZCI6CiAgICAgICAgY29tbWFu
ZHMgKz0gWyJjb25maWd1cmUgdGVybWluYWwiLCAiZW5kIl0KICAgIGNvbW1hbmRzLmFwcGVuZCgi
ZXhpdCIpCiAgICB0cnk6CiAgICAgICAgY29kZSwgb3V0cHV0ID0gc2Vzc2lvbihzdHIoYWRkcmVz
cyksIERFTU9fUEFTU1dPUkQsIGNvbW1hbmRzKQogICAgICAgIGNoZWNrcyA9IGFzc2Vzcyhhcmdz
Lm1vZGUsIGNvZGUsIG91dHB1dCkKICAgIGV4Y2VwdCBzdWJwcm9jZXNzLlRpbWVvdXRFeHBpcmVk
OgogICAgICAgIGNoZWNrcyA9IHsicHJvYmVfZmluaXNoZWRfd2l0aF9vYnNlcnZhYmxlX3Jlc3Vs
dCI6IEZhbHNlfQogICAgcGFzc2VkID0gYWxsKGNoZWNrcy52YWx1ZXMoKSkKICAgIHByaW50KGpz
b24uZHVtcHMoeyJwYXNzZWQiOiBwYXNzZWQsICJtb2RlIjogYXJncy5tb2RlLCAiY2hlY2tzIjog
Y2hlY2tzfSwgc29ydF9rZXlzPVRydWUpKQogICAgcmV0dXJuIDAgaWYgcGFzc2VkIGVsc2UgMQoK
CmlmIF9fbmFtZV9fID09ICJfX21haW5fXyI6CiAgICByYWlzZSBTeXN0ZW1FeGl0KG1haW4oKSkK
CML_EMBED_EXAMPLES_MANAGEMENT_SSH_POLICY_PROBE_PY
echo READY >/dev/console
exit 0
```

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
