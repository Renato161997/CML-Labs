# IOS XE API exercises

The API exercises use an actual CSR1000v 17.3.8a and the separate open-source
automation toolbox. They are isolated guest systems, with public training
credentials and no external connector. The router gets 3072 MiB RAM / 2 vCPUs;
the toolbox gets 1024 MiB / 1 vCPU. These are nominal guest allocations, and the
controller needs its own resources as well. The harness keeps its 4096 MiB
nominal-lab limit.

Install the toolbox using [its release and checksum instructions](TOOLBOX.md).
Use the image revisions recorded in each lab's runtime evidence when reproducing
a result; a different installed default needs a new test. Cisco images are not
redistributed by this repository.

## Preparation and trust

The `iosxe-api-v1` operation is part of the acceptance plan and binds the exact
preparation implementation SHA-256. On a **newly imported disposable lab only**,
the harness performs these actions before baseline checks:

1. Refuse to replace an existing named LABSSH/LABTLS key.
2. Set only the guest router's UTC clock, then generate fresh RSA3072 keys.
3. Enroll a self-signed SHA-256 certificate with an explicit
   `api.cml-lab.example` DNS SAN. Only the known certificate-generation question
   receives a fixed answer; ordinary command framing stays strict.
4. Enable HTTPS, RESTCONF and NETCONF, and wait for the YANG processes.
5. Obtain the public certificate and public RSA keys over authenticated CML
   serial. Deduplicate repeated certificate exports and reject ambiguity,
   missing SAN, invalid dates and inadequate RSA keys.
6. Compare the network-observed SSH key with those serial-derived public keys.
   A key scan alone is never a trust source.
7. Transfer only public trust material into the toolbox, verifying its checksum.

The client receives `/lab/peer-ca.pem` and `/lab/peer-ssh.json`. No router private
key or CML administrator credential is copied to the client. Neither the host
system clock nor its trust store is changed. Each exercise copy is stopped,
wiped and removed after an automated test.

## Client behavior

Requests uses an explicit CA file and normal hostname verification. NETCONF uses
an explicit serial-verified public-key pin and `hostkey_verify=True`. Negative
controls reject a wrong HTTP password, a wrong TLS hostname, a wrong NETCONF
password and a mismatching SSH key; a final valid connection checks recovery.

The toolbox contains ncclient 0.6.17. Its stock IOS XE device hook replaces the
unknown-host callback with one that accepts unknown keys. The example therefore
uses `StrictIOSXE`, retaining IOS XE XML handling while replacing that hook with
an unconditional rejection. Setting `hostkey_verify=True` alone is insufficient
with that stock handler. The negative key test is mandatory.

These are interoperability exercises against a legacy reference platform, not
production crypto or credential settings. Do not copy the fixture passwords,
publish its services or suppress certificate/key validation to bypass an error.

## Results and limits

Preparation completion is required in functional evidence, including its
implementation digest. A boot state, imported YAML, configured string or passing
Docker build alone cannot count as a successful API exercise. Only the checks
and controlled transitions actually recorded for a lab are claimed. The schema
exercise retrieves a real device YANG module but does not publish that module in
this repository.

References: [Cisco container build guidance](https://blogs.cisco.com/learning/building-custom-containers-for-cisco-modeling-labs-cml-a-practical-guide),
[ncclient 0.6.17 IOS XE handler](https://github.com/ncclient/ncclient/blob/v0.6.17/ncclient/devices/iosxe.py).

## Routing configuration and forwarding

The ENARSI routing and Python troubleshooter exercises use an actual Linux
loopback destination. A NETCONF list-entry change is not enough for a pass:
independent IOS routing/ICMP checks must observe delivery, selective withdrawal
and recovery, while the connected management path remains healthy. The broken
case classifies its configured off-link next hop against the subnet read through
RESTCONF before replacing it. Only one isolated /32 route is modified.

For client-driven transitions, `command_pattern` requires an explicit successful
structured result before later state checks. The evidence validator also checks
that result in the recorded output; a green flag cannot replace it.
