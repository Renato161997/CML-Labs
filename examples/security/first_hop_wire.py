"""Bounded Ethernet/IPv4/ARP/DHCPv4 teaching profile, not a general DHCP stack.

Wire layout and option numbers follow RFC2131/RFC2132. Relays, overload,
concatenated options, IP options/fragments, tagged frames and DHCPv6 are outside
this closed one-client profile and are rejected rather than partially parsed.
"""

import ipaddress
import struct

SERVER = "198.18.10.20"
LEASED = "198.18.10.10"
CLIENT_MAC = bytes.fromhex("020000000010")
BROADCAST = b"\xff" * 6
COOKIE = bytes.fromhex("63825363")
BOOT = struct.Struct("!BBBBIHHIIII16s64s128s")


def checksum(raw):
    data = raw + b"\0" * (len(raw) % 2)
    value = sum(struct.unpack("!" + "H" * (len(data) // 2), data))
    while value >> 16:
        value = (value & 0xFFFF) + (value >> 16)
    return (~value) & 0xFFFF


def ip_bytes(value):
    return ipaddress.IPv4Address(value).packed


def ethernet(frame):
    if not 14 <= len(frame) <= 4096:
        raise ValueError("Ethernet frame size outside profile")
    return frame[:6], frame[6:12], struct.unpack("!H", frame[12:14])[0], frame[14:]


def ipv4(frame):
    dst_mac, src_mac, kind, raw = ethernet(frame)
    if kind != 0x0800 or len(raw) < 20 or raw[0] != 0x45:
        raise ValueError("Only untagged IPv4 without options is supported")
    total, fragment = struct.unpack("!HH", raw[2:4] + raw[6:8])
    if not 20 <= total <= len(raw) or fragment & 0xBFFF or checksum(raw[:20]) != 0:
        raise ValueError("Invalid IPv4 length, checksum or fragmentation")
    return {
        "src_mac": src_mac,
        "dst_mac": dst_mac,
        "src": str(ipaddress.IPv4Address(raw[12:16])),
        "dst": str(ipaddress.IPv4Address(raw[16:20])),
        "protocol": raw[9],
        "payload": raw[20:total],
    }


def arp(frame):
    dst_mac, src_mac, kind, raw = ethernet(frame)
    if kind != 0x0806 or len(raw) < 28:
        raise ValueError("Not a complete untagged ARP message")
    hardware, protocol, hlen, plen, opcode = struct.unpack("!HHBBH", raw[:8])
    if (hardware, protocol, hlen, plen) != (1, 0x0800, 6, 4) or opcode not in (1, 2):
        raise ValueError("Unsupported ARP profile")
    if raw[8:14] != src_mac:
        raise ValueError("ARP sender MAC disagrees with Ethernet source")
    return {
        "src_mac": src_mac,
        "dst_mac": dst_mac,
        "opcode": opcode,
        "sender": str(ipaddress.IPv4Address(raw[14:18])),
        "target": str(ipaddress.IPv4Address(raw[24:28])),
    }


def options(raw):
    result = {}
    offset = 0
    while offset < len(raw):
        tag = raw[offset]
        offset += 1
        if tag == 0:
            continue
        if tag == 255:
            if any(raw[offset:]):
                raise ValueError("Non-padding data after DHCP end option")
            return result
        if offset >= len(raw):
            raise ValueError("Truncated DHCP option length")
        size = raw[offset]
        offset += 1
        if not size or offset + size > len(raw) or tag in result or tag == 52:
            raise ValueError("Duplicate, truncated, empty or overloaded DHCP option")
        result[tag] = raw[offset : offset + size]
        offset += size
    raise ValueError("DHCP end option missing")


def dhcp(frame):
    packet = ipv4(frame)
    if packet["dst"] != "255.255.255.255" or packet["dst_mac"] != BROADCAST:
        raise ValueError("Only the fixed selecting broadcast profile is supported")
    udp = packet["payload"]
    if packet["protocol"] != 17 or len(udp) < 8:
        raise ValueError("Not UDP")
    source, destination, size, check = struct.unpack("!HHHH", udp[:8])
    if (source, destination) not in ((68, 67), (67, 68)) or size != len(udp):
        raise ValueError("Invalid DHCP port or UDP length")
    pseudo = ip_bytes(packet["src"]) + ip_bytes(packet["dst"]) + struct.pack("!BBH", 0, 17, size)
    if check and checksum(pseudo + udp) != 0:
        raise ValueError("Invalid optional IPv4 UDP checksum")
    data = udp[8:]
    if len(data) < BOOT.size + 4 or data[BOOT.size : BOOT.size + 4] != COOKIE:
        raise ValueError("Missing BOOTP body or DHCP cookie")
    (
        op,
        hardware,
        hlen,
        hops,
        xid,
        _secs,
        flags,
        ciaddr,
        yiaddr,
        siaddr,
        giaddr,
        chaddr,
        sname,
        file,
    ) = BOOT.unpack(data[: BOOT.size])
    if (hardware, hlen, hops, ciaddr, siaddr, giaddr) != (
        1,
        6,
        0,
        0,
        0,
        0,
    ) or flags != 0x8000:
        raise ValueError("Only the closed direct broadcast selecting profile is supported")
    if any(chaddr[6:]) or any(sname) or any(file):
        raise ValueError("Unexpected BOOTP extension fields")
    if (
        not any(chaddr[:6])
        or chaddr[0] & 1
        or not any(packet["src_mac"])
        or packet["src_mac"][0] & 1
    ):
        raise ValueError("DHCP source/client hardware address must be nonzero unicast")
    opts = options(data[BOOT.size + 4 :])
    kind = opts.get(53)
    if kind not in (b"\x01", b"\x02", b"\x03", b"\x05"):
        raise ValueError("Only actual DORA message types are supported")
    message = kind[0]
    request = message in (1, 3)
    if (op, source, destination) != ((1, 68, 67) if request else (2, 67, 68)):
        raise ValueError("BOOTP operation/UDP roles disagree with message type")
    if request and (yiaddr != 0 or packet["src"] != "0.0.0.0"):
        raise ValueError("Unexpected selecting-client IP state")
    if message != 1 and opts.get(54) != ip_bytes(SERVER):
        raise ValueError("Wrong fixed server identifier")
    if message == 3 and opts.get(50) != ip_bytes(LEASED):
        raise ValueError("Wrong requested fixture address")
    lease = None
    if not request:
        if packet["src"] != SERVER or yiaddr != int(ipaddress.IPv4Address(LEASED)):
            raise ValueError("Wrong server source or offered fixture address")
        if len(opts.get(51, b"")) != 4 or opts.get(1) != ip_bytes("255.255.255.0"):
            raise ValueError("Missing lease or subnet options")
        lease = struct.unpack("!I", opts[51])[0]
        if not 1 <= lease <= 3600:
            raise ValueError("Lease time outside the finite fixture range")
    return {
        **packet,
        "message": message,
        "xid": xid,
        "client_mac": chaddr[:6],
        "offered": str(ipaddress.IPv4Address(yiaddr)),
        "lease": lease,
    }


def make_dhcp(message, xid, source_mac, client_mac=CLIENT_MAC, lease=600):
    if message not in (1, 2, 3, 5) or type(xid) is not int or not 0 <= xid < 2**32:
        raise ValueError("Invalid fixed DORA constructor parameters")
    if (
        type(source_mac) is not bytes
        or type(client_mac) is not bytes
        or len(source_mac) != 6
        or len(client_mac) != 6
        or type(lease) is not int
        or not 1 <= lease <= 3600
    ):
        raise ValueError("Invalid MAC length or lease")
    if not any(source_mac) or not any(client_mac) or source_mac[0] & 1 or client_mac[0] & 1:
        raise ValueError("Source/client MAC must be nonzero unicast")
    request = message in (1, 3)
    opts = bytes((53, 1, message))
    if message != 1:
        opts += bytes((54, 4)) + ip_bytes(SERVER)
    if message == 3:
        opts += bytes((50, 4)) + ip_bytes(LEASED)
    if not request:
        opts += (
            bytes((51, 4)) + struct.pack("!I", lease) + bytes((1, 4)) + ip_bytes("255.255.255.0")
        )
    opts += b"\xff"
    boot = BOOT.pack(
        1 if request else 2,
        1,
        6,
        0,
        xid,
        0,
        0x8000,
        0,
        0 if request else int(ipaddress.IPv4Address(LEASED)),
        0,
        0,
        client_mac,
        b"",
        b"",
    )
    data = (boot + COOKIE + opts).ljust(300, b"\0")
    udp = (
        struct.pack("!HHHH", 68 if request else 67, 67 if request else 68, len(data) + 8, 0) + data
    )
    source = ip_bytes("0.0.0.0" if request else SERVER)
    header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        20 + len(udp),
        xid & 0xFFFF,
        0,
        64,
        17,
        0,
        source,
        ip_bytes("255.255.255.255"),
    )
    header = header[:10] + struct.pack("!H", checksum(header)) + header[12:]
    return BROADCAST + source_mac + b"\x08\x00" + header + udp


def pcap(frames):
    result = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
    for index, frame in enumerate(frames, 1):
        result += struct.pack("<IIII", index, 0, len(frame), len(frame)) + frame
    return result
