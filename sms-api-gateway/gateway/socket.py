# client.py
import asyncio
import websockets

async def hello():
    async with websockets.connect("ws://localhost:8765") as websocket:
        msg = input("Enter a message to send to the server: ")
        await websocket.send(msg)
        response = await websocket.recv()
        print(f"Received from server: {response}")

asyncio.get_event_loop().run_until_complete(hello())