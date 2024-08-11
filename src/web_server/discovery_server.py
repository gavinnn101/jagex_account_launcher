import socket
import threading
import time

from loguru import logger


class DiscoveryServer:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port

    def broadcast_server_address(self, multicast_address="224.1.1.1", multicast_port=6000):
        logger.debug("Starting broadcast server")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)

        message = f"SERVER_IP:{self.server_ip}:{self.server_port}".encode("utf-8")

        while True:
            sock.sendto(message, (multicast_address, multicast_port))
            logger.debug(
                f"Sent message: {message} to multicast address: {multicast_address}:{multicast_port}"
            )
            time.sleep(5)

    def run_broadcast_thread(self):
        broadcast_thread = threading.Thread(
            target=self.broadcast_server_address, daemon=True
        )
        broadcast_thread.start()