
import socket, argparse, urlparse, os, ctypes, struct
import sys
ihost = ""
iport = 0
ihost = ""
iport = 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, help='input interface to listen incoming flows (<host>:<port>)')
    parser.add_argument('--output', type=str, help='list of outputs in <host>:<port> format', nargs='+')
    parser.add_argument('--tunnel_start', action='store_true', help='Relays the raw packet inside another udp packet for transport across spoof blockers.')
    parser.add_argument('--tunnel_end', action='store_true', help='Run on the receiving end of the tunnel_start option.')

    args = parser.parse_args()

    try:
        global ihost, iport
        ihost, iport = parse_url(args.input)
    except Exception, e:
        print "Input interface is not valid: %s" % (str(e))
        return

    outs = []
    for out in args.output:
        try:
            global ohost, oport
            ohost, oport = parse_url(out)
        except Exception, e:
            print "DEBUG Output interface %s is not valid: %s" % (out, str(e))
            return

        try:
            host = onaddr(ohost)
        except IPError, e:
            print "host address should be in IP4 format: %s " % (str(e))
            return

        outs.append((ohost, host, oport))

    if os.geteuid() != 0:
        print "Only root can relay raw packets"
        return

    # Use the custom relay for receiving.  Assumes traffic is being sent
    # with the --tunnel_start option.
    if args.tunnel_end:
        tunnel_end_relay()
        sys.exit(1)

    ##########################################################################
    # Normal relay routine...
    #
    print "Listening on %s:%d" % (ihost, iport)
    print "Sending to:"
    for host, dst, port in outs:
        print "  %s:%d" % (host, port)

    listen = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
    listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    listen.bind((ihost, iport))

    if args.tunnel_start:
        # This option will send the raw pack inside another packet. DGRAM optiont takes
        # care of this for us.
        relay = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    try:
        while True:
            msg, addr = listen.recvfrom(2048)
            #print addr
            ba = bytearray(msg)

            head = PackHead.from_buffer(ba)
            head.uchecksum = 0
            for host, dst, port in outs:
                head.dest = dst
                head.dstport = port

                if args.tunnel_start:
                    size = relay.sendto(str(ba), (host, port))
                    #print size
                else:
                    # Send the raw packet forward, with spoofed destination.
                    size = listen.sendto(str(ba), (host, port))
                    #print size

    except KeyboardInterrupt:
        try:
            print "\nExiting..."
        except:
            pass


def tunnel_end_relay():
    # Datagram (udp) socket
    global ihost, iport
    try:
        listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print 'Socket created'
    except socket.error, msg:
        print 'Failed to create socket. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()

    # Bind socket to local host and port
    try:
        listen.bind((ihost, iport))
    except socket.error, msg:
        print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()

    print 'Socket bind complete...'
    relay = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
    relay.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

    try:
        while True:
            # receive data from client (data, addr)
            msg, addr = listen.recvfrom(2048)
            ba = bytearray(msg)
            #print len(msg)
            #print addr

            # When resending a raw packet we must spoof the destination.
            # Note on sendto routine that is not bound. The ip header determines
            # the port destination, not the arguments to the function.
            head = PackHead.from_buffer(ba)
            head.uchecksum = 0
            head.checksum = 0
            head.dstport = oport

            relay.sendto(str(ba), (ohost, oport))
    except KeyboardInterrupt:
        try:
            print "\nExiting..."
            relay.close()
            listen.close()
        except:
            pass


def ip2int(addr):
    return struct.unpack("!I", socket.inet_aton(addr))[0]


def int2ip(addr):
    return socket.inet_ntoa(struct.pack("!I", addr))


class PackHead(ctypes.BigEndianStructure):
    """UDP Header."""

    _pack_ = 1
    _fields_ = [('prefix', ctypes.c_byte),
                ('DSF', ctypes.c_byte),
                ('length', ctypes.c_uint16),
                ('id', ctypes.c_uint16),
                ('frags', ctypes.c_uint16),
                ('TTL', ctypes.c_byte),
                ('protocol', ctypes.c_byte),
                ('checksum', ctypes.c_uint16),
                ('source', ctypes.c_uint32),
                ('dest', ctypes.c_uint32),
                ('srcport', ctypes.c_uint16),
                ('dstport', ctypes.c_uint16),
                ('ulength', ctypes.c_uint16),
                ('uchecksum', ctypes.c_uint16)]


class IPError(Exception):
    """Custom."""

    pass


def onaddr(ip):
    val = 0
    parts = ip.split('.')
    if len(parts) != 4 : raise IPError("Invalid IP format: '%s'" % (ip))
    for num in parts:
        val <<= 8
        try:
            val += int(num)
        except:
            raise IPError("Invalid IP format: '%s'" % (ip))
    return val


def toip(ip):
    nm = ''
    for _ in range(4):
        nm = ('%d.' % (ip & 0xFF)) + nm
        ip >>= 8
    return nm[:-1]


def parse_url(url):
    orig = url
    if url.find('://') <= 0:
        url = 'udp://' + url.strip()  # just to make urlparse happy
    p = urlparse.urlsplit(url.strip())
    if not p.port:
        raise Exception("Port is not provided. Got '%s'" % (orig))

    if p.scheme != 'udp':
        raise Exception('only udp is supported now')

    return p.hostname, p.port

if __name__ == '__main__':
    main()
