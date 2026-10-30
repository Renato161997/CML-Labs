# Secure Admin Plane

## Scope and prerequisites

IOL-XE is administered by a dedicated Ubuntu OpenSSH client on an isolated point-to-point link. CML-LAB-ONLY and the SNMP credentials, when present, are PUBLIC disposable fixtures. The CML serial console stays privileged; network viewer sessions start at privilege1. The SSH helper uses an instance-local known-hosts file, accepts a new key only in this isolated exercise and rejects changed keys. This is not a production host-key enrollment design. Ephemeral RSA2048 key generation is an explicit setup phase. The source ACL contains an explicit deny-any entry so removing its only permit cannot turn an empty ACL into a permissive policy. Denial evidence distinguishes transport rejection from wrong credentials or changed host identity. This case intentionally elevates a fixture viewer to privilege15, proves actual configuration-mode access without changing any configuration through that session, then restores privilege1.

Use licensed reference images for iol-xe, ubuntu in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Prepared management addressing and access policy; initialize the ephemeral host key in the documented setup phase before testing SSH. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- R1 Ethernet0/0 <-> DEVBOX ens2

| Node | Interface | Address |
| --- | --- | --- |
| R1 | Ethernet0/0 | `ip address 198.18.0.1 255.255.255.252` |

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

## Transition: introduce an overprivileged viewer account

On **R1**:

```ios
configure terminal
username viewer privilege 15 algorithm-type scrypt secret CML-LAB-ONLY
end
```

- DEVBOX: `python3 /opt/cml-management/ssh_policy_probe.py elevated` -- The actual network session now has privilege15 and can enter configuration mode without making changes.

## Transition: restore viewer least privilege

On **R1**:

```ios
configure terminal
username viewer privilege 1 algorithm-type scrypt secret CML-LAB-ONLY
end
```

- DEVBOX: `python3 /opt/cml-management/ssh_probe.py` -- Real SSH proves valid viewer login, privilege1, denied configuration, banner, wrong-password rejection and closed Telnet/HTTP ports.
- R1: `show ip ssh` -- The real SSHv2 server remains enabled.

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
end
```

### DEVBOX

The YAML embeds the Ubuntu cloud-init configuration. The real network probe is [ssh_probe.py](../../examples/management/ssh_probe.py); it uses the installed OpenSSH client and only the public, exercise-only account.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
