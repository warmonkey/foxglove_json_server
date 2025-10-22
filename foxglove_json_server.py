import asyncio, json, time
from datetime import datetime

from mcap.writer import Writer

from foxglove_websocket import run_cancellable
from foxglove_websocket.server import FoxgloveServer, FoxgloveServerListener
from foxglove_websocket.types import ChannelId, ClientChannelId, ServiceId

# ---------- Config parameters ---------
fname = datetime.now().strftime("%Y%m%d_%H%M%S") + '.mcap'
udp_listen = ("0.0.0.0", 9999)
foxglove_listen = ("0.0.0.0", 8765)
channel_name = "tlm"    # Channel name

# ---------- Create schema ---------
tlm_schema = (
    "Telemetry",     # Channel type (schema name)
    json.dumps({
        "type": "object",
        "additionalProperties": True,
    })
)

# ---------- UDP protocol ----------
class UdpJsonProtocol(asyncio.DatagramProtocol):
    def __init__(self, loop, foxglove_server=None, foxglove_chan=None, mcap_writer=None, mcap_chan=None):
        self.loop = loop
        self.foxglove_server = foxglove_server
        self.foxglove_chan = foxglove_chan
        self.mcap_writer = mcap_writer
        self.mcap_chan = mcap_chan

    def datagram_received(self, data: bytes, addr):
        ts = time.time_ns()

        # send to foxglove
        if self.foxglove_server:
            self.loop.create_task(self.foxglove_server.send_message(
                self.foxglove_chan, ts, data
            ))
        
        # write to mcap file
        if self.mcap_writer:
            self.mcap_writer.add_message(
                channel_id=self.mcap_chan,
                log_time=ts,
                publish_time=ts,
                data=data,
            )

    def error_received(self, exc):
        print(f"[UDP] Error: {exc}")

# ---------- Server setup ----------
async def main():
    server = FoxgloveServer(
        *foxglove_listen,
        "Telemetry server",
        supported_encodings=["json"],
    )
    server.start()

    mcap_file = open(fname, "wb")
    mcap_writer = Writer(mcap_file)
    mcap_writer.start()

    # Channel: UDP JSON payloads
    foxglove_chan: ChannelId = await server.add_channel({
        "topic": channel_name,
        "encoding": "json",
        "schemaName": tlm_schema[0],
        "schema": tlm_schema[1],
        "schemaEncoding": "jsonschema"
    })

    mcap_chan = mcap_writer.register_channel(
        topic=channel_name,
        message_encoding="json",
        schema_id=mcap_writer.register_schema(
            name=tlm_schema[0],
            encoding="jsonschema",
            data=tlm_schema[1].encode("utf-8"),
        ),
    )

    loop = asyncio.get_running_loop()
    transport, _protocol = await loop.create_datagram_endpoint(
        lambda: UdpJsonProtocol(loop, server, foxglove_chan, mcap_writer, mcap_chan),
        local_addr=udp_listen,
    )
    
    print("UDP JSON listener: %s:%d" % udp_listen)
    print("Foxglove WebSocket: ws://%s:%d" % foxglove_listen)
    print("MCAP recoder: %s" % mcap_file.name)
    print("")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        transport.close()
        server.close()
        mcap_writer.finish()
        mcap_file.close()

if __name__ == "__main__":
    run_cancellable(main())
