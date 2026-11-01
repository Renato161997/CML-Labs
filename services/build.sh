#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
revision="$(git rev-parse HEAD)"
image="cml-labs-services:${revision:0:12}"
mkdir -p dist/services
docker build --platform linux/amd64 --label "org.opencontainers.image.revision=$revision" -t "$image" services
docker run --rm "$image" python3 -c 'import importlib.metadata,json,cryptography,jsonschema; print(json.dumps({m:importlib.metadata.version(m) for m in ("cryptography","jsonschema")}))'
docker run --rm --network none "$image" python3 /opt/cml-services/check_drivers.py >dist/services/wired-drivers.txt
docker run --rm "$image" sh -c 'openssl version; command -v bridge; command -v tcpdump; test "$(id -u)" = 0'
docker run --rm "$image" dpkg-query -W '-f=${Package}\t${Version}\n' >dist/services/packages.tsv
printf '%s\n' "$revision" >dist/services/source-commit.txt
head -n 1 services/Dockerfile >dist/services/base-image.txt
archive="cml-labs-services-${revision:0:12}.tar.gz"
docker save "$image" | gzip -n >"dist/services/$archive"
python3 scripts/services_assets.py --image "$image" --archive "dist/services/$archive" --output dist/services
(cd dist/services && sha256sum "$archive" node-definition.yaml image-definition.yaml packages.tsv source-commit.txt base-image.txt wired-drivers.txt >SHA256SUMS)
