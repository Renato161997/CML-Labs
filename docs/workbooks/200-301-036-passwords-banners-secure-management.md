# Passwords Banners Secure Management

## Scope and prerequisites

Requires IOL-XE and the Ubuntu 24.04 reference image with its installed OpenSSH client. DEVBOX ens2 is 198.18.0.2/30 and R1 Ethernet0/0 is 198.18.0.1/30. CML-LAB-ONLY is a PUBLIC disposable exercise password, never a production credential. Serial console access remains privileged for the CML administrator; network viewer access is privilege 1. The probe uses a per-instance known-hosts file and accepts a new host key only inside this isolated point-to-point fixture. It refuses changed host keys. No vendor images or private keys are embedded.

Use licensed reference images for iol-xe, ubuntu in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Prepared addressing and access policy; generate the ephemeral host key in the documented setup phase before testing SSH. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> DEVBOX ens2

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Ethernet0/0 | `198.18.0.1/30` |
| DEVBOX | ens2 | `198.18.0.2/30` |

## Tasks

1. Initialize an ephemeral RSA host key on the isolated device.
2. Authenticate through real SSH as a privilege-1 viewer and reject an incorrect password.
3. Verify the login banner, denied configuration privilege and closed Telnet/HTTP services.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| R1 | `ping 198.18.0.2 repeat 3` | The Ubuntu client network is ready. |

## Transition: initialize SSH host identity

On **R1**:

```ios
configure terminal
crypto key generate rsa general-keys label CML-LAB-SSH modulus 2048
ip ssh rsa keypair-name CML-LAB-SSH
end
```

- R1: `show running-config | section line vty` -- All available VTY lines use the intended local SSH access policy.
- R1: `show running-config | include username viewer` -- The lab-only password is stored as a type-9 secret.
- R1: `show ip ssh` -- The actual server is enabled for SSHv2.
- DEVBOX: `python3 /opt/cml-management/ssh_probe.py --banner CML-AUTHORIZED-USERS` -- Real OpenSSH verifies login, privilege 1, denied configuration, wrong-password rejection, banner and closed legacy/web ports.

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
CML-AUTHORIZED-USERS
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
end
```

### DEVBOX

The YAML embeds the Ubuntu cloud-init configuration. The real network probe is [ssh_probe.py](../../examples/management/ssh_probe.py); it uses the installed OpenSSH client and only the public, exercise-only account.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.

The askpass helper supplies only the public lab password through an environment variable; it does not use the CML application password. See [OpenSSH environment handling](https://man.openbsd.org/ssh#ENVIRONMENT). This fixture is not a production host-key enrollment procedure.
