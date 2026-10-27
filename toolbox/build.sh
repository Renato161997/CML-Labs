#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
revision="$(git rev-parse HEAD)"
image="cml-labs-toolbox:${revision:0:12}"
mkdir -p dist/toolbox
docker build --platform linux/amd64 --label "org.opencontainers.image.revision=$revision" -t "$image" toolbox
docker run --rm "$image" python3 -c 'import json,ncclient,paramiko,jinja2,requests,yaml; print(json.dumps({m.__name__:m.__version__ for m in (ncclient,paramiko,jinja2,requests,yaml)}))'
docker run --rm "$image" ansible-playbook --version
docker run --rm "$image" sh -c 'git --version; ssh -V; snmpget --version; test "$(id -u)" = 0'
docker run --rm "$image" dpkg-query -W '-f=${Package}\t${Version}\n' > dist/toolbox/packages.tsv
printf '%s\n' "$revision" > dist/toolbox/source-commit.txt
archive="cml-labs-toolbox-${revision:0:12}.tar.gz"
docker save "$image" | gzip -n > "dist/toolbox/$archive"
python3 scripts/toolbox_assets.py --image "$image" --archive "dist/toolbox/$archive" --output dist/toolbox
(cd dist/toolbox && sha256sum "$archive" node-definition.yaml image-definition.yaml packages.tsv source-commit.txt > SHA256SUMS)
