FROM ciscotalos/snort3@sha256:f15f714fd61ade114b1039687dd43352cae26cd6401b89f2b03404e0d21e322f
# Dedicated isolated teaching node: never change Cisco's stock Snort definition.
USER root
RUN set -eu; \
    binary="$(find /home/snorty /usr/local -type f -name snort -perm /111 | head -n 1)"; \
    config="$(find /home/snorty /usr/local -type f -name snort.lua | head -n 1)"; \
    test -n "$binary"; test -n "$config"; \
    ln -s "$binary" /usr/local/bin/snort-cml; \
    mkdir -p /opt/cml-inspection; \
    printf '%s\n' "$config" >/opt/cml-inspection/config-path; \
    find /home/snorty -type f -name 'libdaq.so*' -printf '%h\n' | sort -u >/etc/ld.so.conf.d/cml-inspection.conf; \
    ldconfig
WORKDIR /root
ENTRYPOINT []
CMD ["/bin/bash"]
