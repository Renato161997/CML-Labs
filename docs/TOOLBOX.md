# Automation toolbox

This optional open-source client supplies Git, Ansible, Jinja2, ncclient,
Paramiko, Requests, Net-SNMP and standard Linux networking tools to an isolated
CML node. It contains no Cisco disk images, human credentials or SSH server.
It is a separate `cml-labs-toolbox` node kind: stock `net-tools` definitions and
defaults are not replaced. Budget 1 GiB RAM for each running toolbox node.

## Build and provenance

`bash toolbox/build.sh` builds an amd64 image from a digest-pinned Debian base,
tests actual imports and installed commands, and exports a Docker archive with
separate node/image definitions. A package inventory and full source revision
accompany `SHA256SUMS`. Packages are obtained from Debian's signed repositories;
the base is pinned but package updates mean rebuilding is not bit-reproducible.
Published releases are immutable; the workflow refuses to overwrite a tag.
Package copyright information remains inside the image under `/usr/share/doc`.

The CML image definition's `sha256` is the **Docker image config digest**, not
the compressed archive checksum. The generator verifies the manifest tag,
config content digest and linux/amd64 platform. `SHA256SUMS` separately verifies
the downloaded archive. These are different identities and must not be swapped.

The **Automation toolbox** workflow builds/tests pull requests with read-only
repository permissions. On `main`, it repeats the build/tests and publishes
release assets using a dedicated job with release-writing permissions. No
homelab runner, secret, CML account or remote network is used by that job.

## Import

1. Download all assets from the same `toolbox-*` release.
2. Run `sha256sum -c SHA256SUMS`; inspect the source revision and package list.
3. In CML, import `node-definition.yaml` as a new node definition.
4. Upload the versioned `cml-labs-toolbox-*.tar.gz` and import `image-definition.yaml`.
5. Confirm the image is associated only with `cml-labs-toolbox`.

Do not overwrite an existing definition with conflicting content. Day-zero
configuration uses an editable `boot.sh`, with four physical ports `eth0` to
`eth3` and an interactive root console. CML provides the isolation boundary:
only use training credentials, and do not attach untrusted labs to a production
external connector. The container has no host Docker socket, host network mode
or privileged flag. NET_ADMIN/NET_RAW apply to its own virtual network namespace.

CI image tests do **not** prove CML console/provisioning or a specific network
exercise. Those require separately recorded CML runtime evidence before a lab
is labelled functional. No existing lab status is promoted by adding this image.

References: [CML node-definition schema](https://github.com/CiscoDevNet/cml-community/blob/master/validation_schemas/node_definition.json),
[Debian ncclient package](https://packages.debian.org/stable/python/python3-ncclient).
The native image digest convention follows [Cisco's container build templates](https://github.com/CiscoLearning/cml-docker-containers/blob/main/templates/definitions.mk).
