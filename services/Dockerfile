FROM debian:trixie-slim@sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad

LABEL org.opencontainers.image.source="https://github.com/Renato161997/CML-Labs" \
      org.opencontainers.image.title="CML-Labs protocol services"

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       ca-certificates curl hostapd iproute2 iputils-ping openssl procps \
       python3 python3-cryptography python3-jsonschema socat tcpdump tini wpasupplicant \
    && rm -rf /var/lib/apt/lists/*

# Preserve Debian copyright information; no host networking or nested daemon.
COPY entrypoint.sh /usr/local/bin/cml-services-entrypoint
COPY check_drivers.py /opt/cml-services/check_drivers.py
RUN chmod 0755 /usr/local/bin/cml-services-entrypoint
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/cml-services-entrypoint"]
