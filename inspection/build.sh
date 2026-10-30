#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
revision="$(git rev-parse HEAD)"
image="cml-labs-inspection:${revision:0:12}"
mkdir -p dist/inspection
docker build --platform linux/amd64 --label "org.opencontainers.image.revision=$revision" -t "$image" inspection
docker run --rm --network none "$image" sh -c 'test "$(id -u)" = 0; test -f "$(cat /opt/cml-inspection/config-path)"'
docker run --rm --network none "$image" snort-cml -V >dist/inspection/snort-version.txt 2>&1
grep -E 'Version 3\.' dist/inspection/snort-version.txt
docker run --rm --network none "$image" snort-cml --daq-list >dist/inspection/daq-modules.txt 2>&1
grep -F afpacket dist/inspection/daq-modules.txt
docker run --rm --network none "$image" dpkg-query -W '-f=${Package}\t${Version}\n' >dist/inspection/packages.tsv
printf '%s\n' "$revision" >dist/inspection/source-commit.txt
head -n 1 inspection/Dockerfile >dist/inspection/base-image.txt
archive="cml-labs-inspection-${revision:0:12}.tar.gz"
docker save "$image" | gzip -n >"dist/inspection/$archive"
python3 scripts/inspection_assets.py --image "$image" --archive "dist/inspection/$archive" --output dist/inspection
(cd dist/inspection && sha256sum "$archive" node-definition.yaml image-definition.yaml packages.tsv source-commit.txt base-image.txt snort-version.txt daq-modules.txt >SHA256SUMS)
