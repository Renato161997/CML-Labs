# Guest WLAN: Service Segmentation and Recovery

## Scope and prerequisites

A real native CML Ubuntu Wireless AP and guest use WPA2-PSK/CCMP over the simulated radio. The GUEST wlan0 address is 198.18.10.2/24, with AP wlan0 gateway 198.18.10.1/24. Only AP ens2 is wired: its 198.18.20.1/30 uplink reaches the independent INSIDE net-tools service at 198.18.20.2/30. INSIDE has an explicit return route to the guest subnet. An allowed shared HTTP endpoint lives on AP loopback 192.0.2.80/32. Every HTTP request carries a new nonce; response identity and nonce must match. Guest requests bind their actual WLAN source address.

The AP enables IPv4 forwarding and one exact ingress routing-policy rule: priority 12345, incoming wlan0, destination 198.18.20.0/30, action prohibit. The test reads actual kernel rules, including the separately reported destination prefix length. Three fresh internal connections must receive explicit network-policy rejection; service refusal, timeout or an HTTP authentication error cannot count as isolation. Shared service access, completed WPA2 association and CCMP must remain healthy. Separate AP-to-internal HTTP/ICMP and internal-server controls prove the protected endpoint is alive. Removing only the rule must allow real guest HTTP and three ICMP replies. Restoring it must restore explicit denial and preserve all healthy controls.

This is an IPv4 forwarded-service segmentation exercise using Linux routing policy, not a stateful firewall, general NAC, peer-station isolation or Cisco controller implementation. The higher-priority local routing table handles addresses on the AP itself; the forwarding rule does not harden AP management or host input. IPv6 is outside the asserted policy. The classroom PSK is public. RF performance and production security are not claimed. See the ip-rule primary manual for selector/action and local-table semantics. Nominal RAM is 4608 MiB (two 2 GiB radio VMs and one 512 MiB server), requiring the reserved larger-case mode.

Use licensed reference images for net-tools, wireless-ap, wireless-client in CML 2.10.1. All addresses are educational. No Internet, external connector or production credentials are required. Starting state: Working isolated reference baseline. Functional status and exact tested images: [results](../../validation/RESULTS.md).

## Topology and addressing

- AP ens2 <-> INSIDE eth1

| Node | Interface | Address |
| --- | --- | --- |
| AP | wlan0 | 198.18.10.1/24 |
| AP | ens2 | 198.18.20.1/30 |
| AP | lo shared endpoint | 192.0.2.80/32 |
| GUEST | wlan0 | 198.18.10.2/24 |
| INSIDE | eth1 | `198.18.20.2/30` |

## Tasks

1. Correlate actual WPA2/CCMP association, allowed shared service and independent internal endpoint health.
2. Verify explicit network-policy rejection of forwarded guest traffic without confusing outage or bad authentication with isolation.
3. Withdraw only the exact ingress rule, prove actual internal access, then restore scoped IPv4 segmentation.

## Baseline acceptance

| Node | Command | Observable result |
| --- | --- | --- |
| INSIDE | `python3 /lab/g.py check` | The protected server independently answers a fresh nonce request. |
| AP | `python3 /lab/g.py check` | Actual AP state and exact kernel ingress rule agree; independent AP-to-internal HTTP and packet controls stay healthy. |
| GUEST | `python3 /lab/g.py check` | Actual completed WPA2/CCMP and a fresh shared HTTP endpoint stay healthy, while internal service access is explicitly rejected at the network layer in three fresh connections and receives no ping replies. |

## Transition: withdraw only guest-to-internal forwarding policy

On **AP**:

```ios
python3 /lab/g.py policy-off
```

- INSIDE: `python3 /lab/g.py check` -- The protected server independently answers a fresh nonce request.
- AP: `python3 /lab/g.py check --policy off` -- Actual AP state and exact kernel ingress rule agree; independent AP-to-internal HTTP and packet controls stay healthy.
- GUEST: `python3 /lab/g.py check --expect allow` -- Actual completed WPA2/CCMP and a fresh shared HTTP endpoint stay healthy, while internal service access is allowed with real HTTP and three packets.

## Transition: restore explicit guest forwarding prohibition

On **AP**:

```ios
python3 /lab/g.py policy-on
```

- INSIDE: `python3 /lab/g.py check` -- The protected server independently answers a fresh nonce request.
- AP: `python3 /lab/g.py check` -- Actual AP state and exact kernel ingress rule agree; independent AP-to-internal HTTP and packet controls stay healthy.
- GUEST: `python3 /lab/g.py check` -- Actual completed WPA2/CCMP and a fresh shared HTTP endpoint stay healthy, while internal service access is explicitly rejected at the network layer in three fresh connections and receives no ping replies.

## Reference configuration and recovery

The checked-in topology carries the reference configurations below. To reset a disposable exercise, stop and wipe only your imported copy, then restart or import the YAML again. Never apply the fault actions to a production device. Fault transitions restore the routing baseline; file-copy exercises may leave their documented output until wipe. Repeat the applicable acceptance checks before ending the exercise.

### Readable implementation and policy scope

The YAML embeds the immutable [radio checks](../../examples/wireless/radio_probe.py) and [guest service/policy fixture](../../examples/wireless/guest_probe.py). The only Ethernet cable joins AP and INSIDE; the guest has no wired path. Wiping the imported copy removes its policy, public teaching PSK and endpoint state.

The [ip-rule manual](https://man7.org/linux/man-pages/man8/ip-rule.8.html) explains ingress selectors, prohibit actions and the earlier local-table lookup. The [iproute2 implementation](https://github.com/iproute2/iproute2/blob/main/ip/iprule.c) shows destination address and prefix length as distinct JSON fields. These references describe the mechanism; fresh CML receipts establish the exact tested behavior.

## Platform scope

Use the [reference-platform guide](../PLATFORMS.md) for the node models named by this workbook. Exact tested CML and image versions are recorded in the [results](../../validation/RESULTS.md). The checks verify the listed protocol and forwarding behavior, not hardware throughput, physical failure timing or complete certification coverage.
