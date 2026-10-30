# Isolated inspection image

The Cisco Talos tutorial container runs as `snorty` and does not supply `sudo`.
The project therefore builds a separate `cml-labs-inspection` guest from a pinned
[official Cisco Talos base](https://hub.docker.com/r/ciscotalos/snort3). Stock CML
Snort definitions and images are preserved. Root applies inside the disposable
training guest; no host Docker socket, host network or privileged flag is used.
The node requests only NET_ADMIN and NET_RAW for its own data interfaces.
Never connect an untrusted teaching lab to a production external connector.

## Build and verify

`bash inspection/build.sh` verifies actual UID zero, Snort3 execution, configuration
presence and the AFPacket DAQ module before exporting an amd64 archive. It records
the pinned base, source revision, engine version, DAQ list, Debian package inventory
and independent archive checksums. The CML image identity uses the validated Docker
config digest, not the compressed archive checksum. Base/tutorial contents remain
under their upstream licenses; Snort is [open source](https://www.snort.org/license).
This derivative is a project teaching image, not an official Cisco CML reference.

The existing Automation toolbox workflow can build an inspection preview through
its manual `image: inspection` option, using read-only repository permissions.
Preview assets are temporary CI artifacts. A preview is not a supported release or
proof of CML provisioning, inline traffic, signature matching or policy recovery.
Those require separate live CML evidence before publication of the exercise.

## Import

Use all assets from a single versioned `inspection-*` release. Verify SHA256SUMS,
inspect source/base/version metadata, import its new node definition, upload its
versioned archive, then import its matching image definition. Refuse conflicting
existing definitions rather than overwriting a stock node. The isolated root
console is port zero; four interfaces are eth0..eth3, with eth0 reserved for
management. Budget 1024 MiB per inspection guest.

The Snort exercise uses deliberately benign HTTP text as a signature fixture.
A match does not establish maliciousness or a vulnerability. Actual alert, inline
drop, scope repair and service recovery must all be observed on the tested image.
