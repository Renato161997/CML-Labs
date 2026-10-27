FROM debian:trixie-slim@sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad

LABEL org.opencontainers.image.source="https://github.com/Renato161997/CML-Labs" \
      org.opencontainers.image.title="CML-Labs automation toolbox"

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       ansible ca-certificates curl dnsutils git iproute2 iputils-ping \
       openssh-client openssl procps python3 python3-cryptography python3-jinja2 \
       python3-jmespath python3-ncclient python3-paramiko python3-requests \
       python3-yaml snmp socat tcpdump tini \
    && rm -rf /var/lib/apt/lists/*

# Keep package copyright files: the archive contains Debian-packaged software.
COPY entrypoint.sh /usr/local/bin/cml-toolbox-entrypoint
RUN chmod 0755 /usr/local/bin/cml-toolbox-entrypoint
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/cml-toolbox-entrypoint"]
