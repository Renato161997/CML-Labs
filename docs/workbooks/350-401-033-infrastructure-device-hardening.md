# Infrastructure Hardening: AAA, Accounting and VTY Policy

## Scope and prerequisites

A real IOL-XE SSH server authenticates viewer sessions against separate native FreeRADIUS and tac_plus services. CLIENT uses actual OpenSSH, not a mocked authentication API. The public viewer credential starts at privilege1 and cannot enter configuration mode. There is no local viewer account and no local/if-authenticated fallback in the network method lists. The serial console deliberately remains unauthenticated and privileged so the owner can repair the disposable exercise. Both services emit actual exec accounting: evidence requires fresh viewer Start/Stop records sharing a session ID, with owned logs truncated immediately before each test session. Truncation preserves existing ownership/mode and never creates a substitute file. Repeated log copies are not extra sessions. Shell command accounting and commercial Cisco ISE are not claimed.

NAS front Ethernet0/0 is 198.18.0.1, RADIUS Ethernet0/1 is 198.18.1.1 and TACACS+ Ethernet0/2 is 198.18.2.1. Only declared data links are wired; native eth0 management is unwired. FreeRADIUS allowlists the single NAS source and requires Message-Authenticator for Access-Request authentication. The RAD-GROUP authentication method retains send-ma and validate-ma; a separate RAD-ACCT group sends legacy accounting with its normal Request Authenticator. Sending MA from the initial combined IOL group caused accounting packets to be rejected with an invalid-Message-Authenticator diagnostic in this tested image combination. The accepted separation must produce actual correlated Start/Stop records; authentication password logging is disabled. Teaching shared keys and passwords are public isolated fixtures. RADIUS is not RadSec, and this legacy TACACS+ interoperability fixture is not a modern secure transport recommendation. Ephemeral RSA3072 identity and accept-new per-instance client trust are classroom initialization only; changed host identities are rejected. No external credentials or Internet connection is used. A wrong TACACS+ key must cause actual SSH authentication denial while TCP22 and independent IP paths remain healthy, followed by recovered sessions and fresh accounting. Stop/wipe only this imported copy to reset. The hardening variant adds a separately routed untrusted client on Ethernet0/3. Removing only the VTY source binding must admit its actual privilege1 session; restoring the binding must reject its transport while the authorized client still works.

Use licensed reference images for cml-labs-toolbox, iol-xe, radius, tacplus in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> CLIENT eth1
- R1 Ethernet0/1 <-> RADIUS eth1
- R1 Ethernet0/2 <-> TACACS eth1
- R1 Ethernet0/3 <-> UNTRUST eth1

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |
| R1 | Ethernet0/1 | `ip address 198.18.1.1 255.255.255.252` |
| R1 | Ethernet0/2 | `ip address 198.18.2.1 255.255.255.252` |
| R1 | Ethernet0/3 | `ip address 198.18.3.1 255.255.255.252` |
| RADIUS | eth1 | `198.18.1.2/30` |
| TACACS | eth1 | `198.18.2.2/30` |
| CLIENT | eth1 | `198.18.0.2/30` |
| UNTRUST | eth1 | `198.18.3.2/30` |

## Tasks

1. Use real centrally authenticated SSH sessions with least-privilege checks.
2. Correlate fresh exec accounting Start/Stop by session identifier for both server types.
3. Break one shared-key relationship, observe correct-credential rejection and recover.
4. Withdraw and restore only VTY source admission with two real clients.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.1.2 repeat 3` | The RADIUS path is healthy. |
| R1 | `ping 198.18.2.2 repeat 3` | The independent TACACS+ path is healthy. |
| R1 | `show running-config | section aaa group server radius` | The NAS requests and validates the RADIUS Message-Authenticator. |
| R1 | `show running-config | include aaa accounting exec VTY-RAD` | Actual exec accounting selects its separate legacy accounting group. |
| R1 | `show running-config | section line vty` | The actual supported VTY0-4 lines bind login, exec authorization, accounting and the source filter before any network session. |

## Transition: generate the disposable SSH identity

On **R1**:

```ios
configure terminal
crypto key generate rsa general-keys label CML-LAB-SSH modulus 3072
ip ssh rsa keypair-name CML-LAB-SSH
end
```

- R1: `show ip ssh` -- The fresh host identity enables actual SSHv2.

## Transition: clear RADIUS accounting window 1

On **RADIUS**:

```ios
bash /lab/a.sh clear
```

- RADIUS: `bash /lab/a.sh check` -- The owned backend has no completed viewer session left in the fresh evidence window.

## Transition: authenticate and account an actual RADIUS viewer session

On **CLIENT**:

```ios
python3 /opt/cml-management/ssh_probe.py
```

- RADIUS: `bash /lab/a.sh check` -- Fresh viewer Start and Stop records have the same actual session identifier; historical records were cleared immediately before this session.

## Transition: switch network sessions to TACACS+

On **R1**:

```ios
configure terminal
line vty 0 4
login authentication VTY-TAC
authorization exec VTY-TAC
accounting exec VTY-TAC
exit
end
```

- R1: `show running-config | section line vty` -- All three VTY methods select the TACACS+ backend.

## Transition: clear TACACS accounting window 1

On **TACACS**:

```ios
bash /lab/a.sh clear
```

- TACACS: `bash /lab/a.sh check` -- The owned backend has no completed viewer session left in the fresh evidence window.

## Transition: authenticate and account an actual TACACS+ viewer session

On **CLIENT**:

```ios
python3 /opt/cml-management/ssh_probe.py
```

- TACACS: `bash /lab/a.sh check` -- Fresh viewer Start and Stop records have the same actual session identifier; historical records were cleared immediately before this session.

## Transition: break only the TACACS+ shared-key relationship

On **R1**:

```ios
configure terminal
tacacs server LAB-TACACS
key 0 Wrong-tacacs-only-999
end
```

- CLIENT: `python3 /opt/cml-management/aaa_client.py` -- SSH remains reachable, but the same correct public fixture credential receives an actual authentication denial; a timeout, transport failure or changed host key cannot pass.
- R1: `ping 198.18.1.2 repeat 3` -- The RADIUS path is healthy.
- R1: `ping 198.18.2.2 repeat 3` -- The independent TACACS+ path is healthy.
- R1: `test aaa group RAD-GROUP viewer CML-LAB-ONLY new-code` -- Independent RADIUS authentication still succeeds during the isolated TACACS+ key fault.

## Transition: restore the original TACACS+ shared key

On **R1**:

```ios
configure terminal
tacacs server LAB-TACACS
key 0 Cml-Tacacs-Lab-Only-983
end
```

- R1: `test aaa group TAC-GROUP viewer CML-LAB-ONLY legacy` -- The restored TACACS+ relationship accepts a fresh actual authentication request.

## Transition: clear TACACS accounting window 2

On **TACACS**:

```ios
bash /lab/a.sh clear
```

- TACACS: `bash /lab/a.sh check` -- The owned backend has no completed viewer session left in the fresh evidence window.

## Transition: verify recovered TACACS+ session accounting

On **CLIENT**:

```ios
python3 /opt/cml-management/ssh_probe.py
```

- TACACS: `bash /lab/a.sh check` -- Fresh viewer Start and Stop records have the same actual session identifier; historical records were cleared immediately before this session.

## Transition: restore RADIUS as the original VTY backend

On **R1**:

```ios
configure terminal
line vty 0 4
login authentication VTY-RAD
authorization exec VTY-RAD
accounting exec VTY-RAD
exit
end
```

- R1: `show running-config | section line vty` -- All three VTY methods again select RADIUS.

## Transition: clear RADIUS accounting window 2

On **RADIUS**:

```ios
bash /lab/a.sh clear
```

- RADIUS: `bash /lab/a.sh check` -- The owned backend has no completed viewer session left in the fresh evidence window.

## Transition: verify restored RADIUS session accounting

On **CLIENT**:

```ios
python3 /opt/cml-management/ssh_probe.py
```

- RADIUS: `bash /lab/a.sh check` -- Fresh viewer Start and Stop records have the same actual session identifier; historical records were cleared immediately before this session.

## Transition: observe the rejected independent management source

On **UNTRUST**:

```ios
python3 /opt/cml-management/ssh_policy_probe.py denied
```

- R1: `ping 198.18.3.2 repeat 3` -- The untrusted data link is reachable.
- CLIENT: `python3 /opt/cml-management/ssh_probe.py` -- Actual OpenSSH verifies central login, privilege1, denied configuration, banner, wrong-password rejection and closed web/Telnet ports.

## Transition: withdraw only the VTY source filter

On **R1**:

```ios
configure terminal
line vty 0 4
no access-class MGMT in
exit
end
```

- UNTRUST: `python3 /opt/cml-management/ssh_probe.py` -- Actual OpenSSH verifies central login, privilege1, denied configuration, banner, wrong-password rejection and closed web/Telnet ports.
- CLIENT: `python3 /opt/cml-management/ssh_probe.py` -- Actual OpenSSH verifies central login, privilege1, denied configuration, banner, wrong-password rejection and closed web/Telnet ports.

## Transition: restore the VTY source filter

On **R1**:

```ios
configure terminal
line vty 0 4
access-class MGMT in
exit
end
```

- UNTRUST: `python3 /opt/cml-management/ssh_policy_probe.py denied` -- An independently routed source cannot enter SSH despite the same valid public user credential.
- R1: `ping 198.18.3.2 repeat 3` -- The untrusted data link is reachable.
- CLIENT: `python3 /opt/cml-management/ssh_probe.py` -- Actual OpenSSH verifies central login, privilege1, denied configuration, banner, wrong-password rejection and closed web/Telnet ports.

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
interface Ethernet0/2
 ip address 198.18.2.1 255.255.255.252
 no shutdown
 exit
aaa new-model
aaa authentication login CONSOLE none
line console 0
 login authentication CONSOLE
 privilege level 15
 exit
ip radius source-interface Ethernet0/1
ip tacacs source-interface Ethernet0/2
radius server LAB-RADIUS
 address ipv4 198.18.1.2 auth-port 1812 acct-port 1813
 timeout 2
 retransmit 0
 key 0 Cml-Radius-Lab-Only-983
 exit
tacacs server LAB-TACACS
 address ipv4 198.18.2.2
 timeout 2
 key 0 Cml-Tacacs-Lab-Only-983
 exit
aaa group server radius RAD-GROUP
 server name LAB-RADIUS
 send-ma
 validate-ma
 exit
aaa group server tacacs+ TAC-GROUP
 server name LAB-TACACS
 exit
aaa group server radius RAD-ACCT
 server name LAB-RADIUS
 no send-ma
 exit
aaa authentication login VTY-RAD group RAD-GROUP
aaa authorization exec VTY-RAD group RAD-GROUP
aaa accounting exec VTY-RAD start-stop group RAD-ACCT
aaa authentication login VTY-TAC group TAC-GROUP
aaa authorization exec VTY-TAC group TAC-GROUP
aaa accounting exec VTY-TAC start-stop group TAC-GROUP
no logging console
ip domain name lab.example
ip ssh version 2
ip ssh time-out 5
ip ssh authentication-retries 1
no ip http server
no ip http secure-server
banner motd ^CML-SSH-LAB^
ip access-list standard MGMT
 permit host 198.18.0.2
 deny any
 exit
line vty 0 4
 transport input ssh
 login authentication VTY-RAD
 authorization exec VTY-RAD
 accounting exec VTY-RAD
 access-class MGMT in
 exit
interface Ethernet0/3
 ip address 198.18.3.1 255.255.255.252
 no shutdown
 exit
end
```

### Readable native fixtures

The [accounting parser](../../examples/management/aaa_accounting.sh), [OpenSSH probe](../../examples/management/ssh_probe.py) and [AAA denial probe](../../examples/management/aaa_client.py) are embedded byte-for-byte. All fixtures are public disposable examples. Accounting output reports only the backend and count of correlated completed viewer sessions. Cisco documents [privilege assignment](https://www.cisco.com/c/en/us/support/docs/security-vpn/remote-authentication-dial-user-service-radius/13860-PRIV.html); [RFC8907](https://www.rfc-editor.org/rfc/rfc8907) describes the legacy TACACS+ protocol. The exercise uses the stated legacy image implementation and is not a modern production transport design.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
