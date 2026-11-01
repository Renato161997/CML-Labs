# Secure API Client: Verified Peers and Backend Recovery

## Scope and prerequisites

A real CSR1000v 17.3.8a and the open-source CML-Labs toolbox exchange NETCONF and RESTCONF over an isolated benchmark network. Nominal RAM is 3072+1024 MiB, with two router vCPUs. The registered iosxe-api-v1 preparation is implementation-digest-bound: it creates fresh RSA3072 keys and an explicit DNS-SAN certificate, sets only the disposable guest clock, waits for YANG daemons, exports public trust material over authenticated CML serial, matches ssh-keyscan against those serial-derived public keys, and checksum-verifies transfer to the client. No private key or CML administrator credential enters the guest client. TLS verification remains enabled, and NETCONF uses an explicit key pin plus a strict IOSXE ncclient handler: the stock ncclient0.6.17 IOSXE callback accepts unknown keys and is deliberately overridden. Wrong-password, wrong-hostname and wrong-key negative controls precede a fresh valid connection. All credentials in this file are public isolated training fixtures. This tested legacy CSR reference platform is an interoperability exercise, not a production cryptographic recommendation. No Internet, external connector or existing lab is used; stop/wipe only your imported copy to reset. The harness performs preparation automatically; its source scripts/iosxe_prepare.py also documents the serial steps and the known certificate-enrollment dialogue. Do not bypass verification if a certificate or key differs.

Use the independently obtained certificate and SSH public keys, exercise actual wrong-credential/identity controls, make a bounded hostname change over NETCONF, read it back and restore it in a finally-protected operation. The HTTPS-only fault must not be confused with lost NETCONF or an unavailable router. This is not a least-privilege production account: the explicit public classroom device credential has privilege 15.

Use licensed reference images for cml-labs-toolbox, csr1000v in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- API GigabitEthernet1 <-> TOOLS eth1

| Node | Interface | Address |
| --- | --- | --- |
| API | GigabitEthernet1 | `ip address 198.18.0.1 255.255.255.252` |
| TOOLS | eth1 | `198.18.0.2/30` |

## Tasks

1. Obtain trust through the isolated serial preparation and reject incorrect network peer identities and credentials.
2. Perform the documented real RESTCONF/NETCONF operation with actual device readback.
3. Withdraw only HTTPS, preserve explicitly verified NETCONF evidence, and recover a fresh verified connection.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| TOOLS | `python3 /lab/api_probe.py manage baseline` | The unchanged client performs actual peer-verified RESTCONF and pinned NETCONF operations, rejects the declared wrong identities/credentials and observes the expected HTTPS availability. |

## Transition: withdraw only the actual HTTPS listener

On **API**:

```ios
configure terminal
no ip http secure-server
end
```

- TOOLS: `python3 /lab/api_probe.py manage https-off` -- The unchanged client performs actual peer-verified RESTCONF and pinned NETCONF operations, rejects the declared wrong identities/credentials and observes the expected HTTPS availability.

## Transition: restore peer-verified HTTPS and fresh device evidence

On **API**:

```ios
configure terminal
ip http secure-server
end
```

- TOOLS: `python3 /lab/api_probe.py manage recovered` -- The unchanged client performs actual peer-verified RESTCONF and pinned NETCONF operations, rejects the declared wrong identities/credentials and observes the expected HTTPS availability.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### API

```ios
hostname API
no ip domain-lookup
ip domain name cml-lab.example
username CML-LAB privilege 15 secret Cml-lab-only-984
aaa new-model
aaa authentication login default local
aaa authorization exec default local
aaa authentication login CONSOLE none
line console 0
 login authentication CONSOLE
 privilege level 15
 exec-timeout 0 0
 logging synchronous
 exit
interface GigabitEthernet1
 ip address 198.18.0.1 255.255.255.252
 no shutdown
 exit
no ip http server
no ip http secure-server
ip http authentication local
ip ssh version 2
line vty 0 4
 login authentication default
 transport input ssh
 exit
end
```

### Inspectable client and serial trust preparation

The [unchanged verified client](../../examples/automation/api_probe.py) performs the real protocol checks. The [digest-bound preparation](../../scripts/iosxe_prepare.py) creates guest keys/certificates and exports only public trust material. No CML administrator password enters this client. The tested legacy CSR and its public privilege-15 device account are classroom fixtures.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
