import dataclasses
import json
import os
import asyncio
import websockets
from typing import Dict, List, Optional

import dotenv
from fastapi import WebSocket

from api.data_model.connection import DynamicPacket


dotenv.load_dotenv()

CONNECTIONS = {}
PORT = eval(os.getenv('SERVER_PORT', '8001'))


# -- conn funcs -- #

async def open_websocket(uri: str):
    return await websockets.connect(uri)


async def listen_to_websocket(ws):
    async for message in ws:
        try:
            data = json.loads(message)
            print("Received:", data)
            # TODO: here take in the request and process, possibly also listening for deltas and stopping if so
        except json.JSONDecodeError:
            print("Invalid JSON:", message)


async def send_packet(ws, data: DynamicPacket):
    await ws.send(json.dumps(data.to_dict()))


async def receive_packet(ws, state: list):
    msg = await ws.recv()
    payload = json.loads(msg)
    state.append(payload)
