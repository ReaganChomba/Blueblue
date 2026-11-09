#!/usr/bin/env python3
"""Python 3 replacement for Blueblue's legacy raw SSH-over-HTTP upgrade bridge.

This preserves payload-client tunnelling (an HTTP upgrade followed by raw SSH),
not RFC6455 framing. Targets are fixed by the operator, never chosen by headers.
"""
import asyncio
import contextlib
import os
import signal

HOST = os.environ.get('BLUEBLUE_BRIDGE_HOST', '127.0.0.1')
PORT = int(os.environ.get('BLUEBLUE_BRIDGE_PORT', '700'))
TARGET_PORT = int(os.environ.get('BLUEBLUE_SSH_PORT', '109'))
LIMIT = int(os.environ.get('BLUEBLUE_BRIDGE_CONNECTIONS', '512'))
active = 0


async def pipe(reader, writer):
    while True:
        block = await asyncio.wait_for(reader.read(65536), timeout=300)
        if not block:
            return
        writer.write(block)
        await writer.drain()


async def handle(reader, writer):
    global active
    if active >= LIMIT:
        writer.close()
        return
    active += 1
    upstream = None
    try:
        header = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 15)
        if len(header) > 16384 or not header.startswith((b'GET ', b'CONNECT ')):
            writer.write(b'HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n')
            await writer.drain()
            return
        remote, upstream = await asyncio.wait_for(asyncio.open_connection('127.0.0.1', TARGET_PORT), 10)
        writer.write(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n')
        await writer.drain()
        tasks = [asyncio.create_task(pipe(reader, upstream)), asyncio.create_task(pipe(remote, writer))]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
        pass
    finally:
        active -= 1
        for stream in (writer, upstream):
            if stream:
                stream.close()
                with contextlib.suppress(OSError):
                    await stream.wait_closed()


async def main():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    server = await asyncio.start_server(handle, HOST, PORT, limit=16384)
    async with server:
        await stop.wait()


if __name__ == '__main__':
    asyncio.run(main())
