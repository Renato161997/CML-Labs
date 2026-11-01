# Isolated protocol-services image

This optional `cml-labs-services` guest supplies Debian-packaged hostapd,
wpa_supplicant, OpenSSL, Python cryptography, JSON Schema validation and packet
tools for future wired-authentication and API-contract exercises. Budget 1 GiB
RAM per node. It defines a separate kind and does not replace stock nodes,
the automation toolbox or any existing lab's image selection.

`bash services/build.sh` builds from the pinned Debian base, checks actual
Python imports and wired-driver availability, records packages and source
revision, and produces the archive, definitions and `SHA256SUMS`. Packages
come from Debian's signed repositories; rebuilding later is not bit-reproducible.
Copyright files stay in the image. No Cisco image, private credential, SSH
server, nested container daemon, host network or additional host mount is added.
Capabilities are inherited unchanged from the existing isolated toolbox kind.

On pull requests, the workflow builds and checks without release-writing
permission. On main, it publishes the exact verified artifact under an
immutable `services-<source revision>` release; it refuses replacement.
These build checks are not an IEEE 802.1X interoperability or CML runtime proof.
Runtime claims require the corresponding completed lab receipt.

To import a published release:

1. Download every asset from the same release and run `sha256sum -c SHA256SUMS`.
2. Check `source-commit.txt`, `base-image.txt`, `packages.tsv` and `wired-drivers.txt`.
3. Import the new node definition, upload its archive, then import its image definition.
4. Confirm the image is associated only with `cml-labs-services`.
5. Pin the exact image ID when running a future exercise.

The image-definition SHA256 is Docker's **image config digest**, which the
asset generator checks against the archive manifest and linux/amd64 metadata.
It differs from the compressed archive checksum in `SHA256SUMS`.
