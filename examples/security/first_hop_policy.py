"""A finite trusted-port DORA/ARP/IPv4 source-binding inspection model.

The eventual live worker supplies actual ingress port and monotonic time.
There is no configuration action that directly installs an admission binding.
"""

import struct

import first_hop_wire as wire


class Gate:
    def __init__(self):
        self.pending = None
        self.binding = None
        self.last_lease = None
        self.counts = {
            name: 0
            for name in (
                "discover_seen",
                "offer_seen",
                "request_seen",
                "ack_learned",
                "untrusted_server_drop",
                "dhcp_sequence_drop",
                "arp_binding_drop",
                "ip_binding_drop",
                "malformed_drop",
                "unsupported_drop",
                "lease_expired",
                "forwarded",
            )
        }

    def drop(self, reason):
        self.counts[reason] += 1
        return False

    def forward(self):
        self.counts["forwarded"] += 1
        return True

    def expire(self, now):
        if self.pending is not None and now >= self.pending["expires"]:
            self.pending = None
        if self.binding is not None and now >= self.binding["expires"]:
            self.binding = None
            self.counts["lease_expired"] += 1

    def dhcp(self, side, value, now):
        kind = value["message"]
        if side == 1 and kind in (2, 5):
            return self.drop("untrusted_server_drop")
        if side == 2 and kind in (1, 3):
            return self.drop("dhcp_sequence_drop")
        if kind in (1, 3) and value["client_mac"] != value["src_mac"]:
            return self.drop("dhcp_sequence_drop")
        if kind == 1:
            self.pending = {
                "xid": value["xid"],
                "mac": value["client_mac"],
                "stage": 1,
                "expires": now + 20,
            }
            self.counts["discover_seen"] += 1
            return self.forward()
        state = self.pending
        if state is None or (state["xid"], state["mac"]) != (
            value["xid"],
            value["client_mac"],
        ):
            return self.drop("dhcp_sequence_drop")
        if kind == 2 and state["stage"] == 1:
            state.update(stage=2, lease=value["lease"])
            self.counts["offer_seen"] += 1
        elif kind == 3 and state["stage"] in (2, 3):
            state["stage"] = 3
            self.counts["request_seen"] += 1
        elif kind == 5 and state["stage"] == 3 and state["lease"] == value["lease"]:
            self.binding = {
                "mac": state["mac"],
                "ip": value["offered"],
                "port": 1,
                "lease": value["lease"],
                "expires": now + value["lease"],
            }
            self.last_lease = value["lease"]
            self.pending = None
            self.counts["ack_learned"] += 1
        else:
            return self.drop("dhcp_sequence_drop")
        return self.forward()

    def process(self, side, frame, now):
        if side not in (1, 2):
            raise ValueError("Only the fixed untrusted/trusted data ports are supported")
        self.expire(now)
        try:
            _, _, kind, _ = wire.ethernet(frame)
            if kind == 0x0806:
                value = wire.arp(frame)
                if side == 2:
                    return self.forward()
                bound = self.binding
                if bound is not None and (value["src_mac"], value["sender"]) == (
                    bound["mac"],
                    bound["ip"],
                ):
                    return self.forward()
                if (
                    self.pending is not None
                    and value["sender"] == "0.0.0.0"
                    and value["target"] == wire.LEASED
                    and value["src_mac"] == self.pending["mac"]
                ):
                    return self.forward()
                return self.drop("arp_binding_drop")
            if kind != 0x0800:
                return self.drop("unsupported_drop")
            value = wire.ipv4(frame)
            payload = value["payload"]
            if (
                value["protocol"] == 17
                and len(payload) >= 8
                and struct.unpack("!HH", payload[:4]) in ((68, 67), (67, 68))
            ):
                return self.dhcp(side, wire.dhcp(frame), now)
            if side == 2:
                return self.forward()
            bound = self.binding
            if bound is not None and (value["src_mac"], value["src"]) == (
                bound["mac"],
                bound["ip"],
            ):
                return self.forward()
            return self.drop("ip_binding_drop")
        except (ValueError, struct.error):
            return self.drop("malformed_drop")

    def snapshot(self, now):
        self.expire(now)
        binding = None
        if self.binding is not None:
            binding = {
                **self.binding,
                "mac": self.binding["mac"].hex(":"),
                "remaining": max(0.0, self.binding["expires"] - now),
            }
        return {
            "binding": binding,
            "last_lease": self.last_lease,
            "pending_stage": None if self.pending is None else self.pending["stage"],
            "counts": dict(self.counts),
        }
