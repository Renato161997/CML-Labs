# Secrets: OS Ownership, Scoped Injection and Live Rotation

## Scope and prerequisites

One isolated native Linux guest runs actual processes with service UID/GID 1500 and untrusted UID/GID 1501, both without supplementary groups. The service key is freshly generated inside each imported copy; no production key or CML credential enters this exercise. Its parent directory is root-owned 0755, and the root-owned key is group 1500 readable with mode 0440. Both non-root identities must be unable to open the file for writing. Symbolic links, multiple hard links, unexpected ownership and modes outside the explicit exercise states are refused.

A real loopback HTTP service runs as UID 1500, reads the current key on every protected request and verifies the exact canonical Bearer value. The legitimate UID reads the key from the file and reaches HTTP 200; UID 1501 cannot read it and gets HTTP 401 without a key. The service checks its actual own process command line/environment for the active key and returns only a boolean plus its observed UID. Clean child environments and argument vectors contain no key; the captured old key is delegated for replay only through a process stdin pipe, never argv/environment.

The controlled fault changes only mode 0440 to 0444. UID 1501 must now genuinely read the file and authenticate with HTTP 200; both identities still lack write permission. A root-private 0600 copy records the now-compromised training key solely for the recovery probe. Repair restores 0440 and atomically installs a different fresh root-owned/group-readable value while the same service process remains running. UID 1501 must again fail to read the replacement, and its actually cached old key must get 401. The legitimate reader gets 200 with the new value. The obsolete root-private replay fixture remains only until the imported node is wiped.

This teaches local OS ownership, scoped file-based injection and live rotation/revocation consequences. The loopback API is a bounded authentication fixture, not OAuth, an OpenBao/Vault server, an external identity provider or a real Cisco management API. HTTP is restricted to this guest loopback; TLS, remote secret transport, encryption at rest, KMS/HSM, multi-tenant container security and a production secret broker are outside scope. Numeric identities are disposable process credentials, not host/user accounts. Native guests share their execution kernel. No external connector, installed host agent or Internet service is needed. Only the imported copy may be stopped/wiped.


Use licensed reference images for net-tools in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing


| Node | Interface | Address |
| --- | --- | --- |

## Tasks

1. Verify real read/write access decisions under distinct OS identities, plus live authenticated requests.
2. Observe an actual credential exposure through an intentionally widened file read mode.
3. Restore scoped access, rotate atomically and reject replay of the captured old value without stopping the service.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| TOOLS | `python3 /lab/s.py baseline` | Real OS processes use separate UIDs/groups. The service reads its root-owned group-readable key and authenticates; the untrusted process cannot read or write it and receives HTTP 401. The service cannot write the key either. Actual service metadata must not contain the active key. |

## Transition: expose only the fixture credential read mode

On **TOOLS**:

```ios
python3 /lab/s.py expose
```

- TOOLS: `python3 /lab/s.py exposed` -- The separate untrusted UID actually reads the deliberately world-readable credential and successfully authenticates against the live service; a permission string alone cannot pass.

## Transition: restore scoped file access and rotate the compromised value

On **TOOLS**:

```ios
python3 /lab/s.py repair
```

- TOOLS: `python3 /lab/s.py baseline` -- Real OS processes use separate UIDs/groups. The service reads its root-owned group-readable key and authenticates; the untrusted process cannot read or write it and receives HTTP 401. The service cannot write the key either. Actual service metadata must not contain the active key.
- TOOLS: `python3 /lab/s.py recovered` -- Restored ownership/mode denies fresh untrusted reads; replay of the actually captured prior key fails at the live service while the legitimate reader authenticates with the replacement.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Inspectable credential lifecycle fixture

The [file ownership, real UID process, API and rotation implementation](../../examples/security/secret_files.py) is embedded unchanged. Inspect only permissions/ownership and the acceptance output; do not print key contents, request headers or the private replay file. `ls -ld /lab/secret-demo` and `ls -l /lab/secret-demo/runtime.key` expose metadata only. Wiping your imported node removes all generated key material and processes.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
