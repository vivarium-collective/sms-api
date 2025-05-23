# Requires: `starlette`, `uvicorn`, `jinja2`
# Run with `uv run uvicorn gateway.broadcasting:app`
import datetime
import json
import anyio
from dataclasses import dataclass, asdict

from broadcaster import Broadcast
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.templating import Jinja2Templates

from gateway.dispatch import compile_simulation, dispatch_simulation


CLIENT_TEMPLATES_DIR = "resources/client_templates"
broadcast = Broadcast("memory://localhost:6379")
templates = Jinja2Templates(CLIENT_TEMPLATES_DIR)


def timestamp():
    return str(datetime.datetime.now())


async def homepage(request):
    template = "index.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context)


async def chatroom_ws(websocket):
    await websocket.accept()
    print(f'Socket accepted!')
    async with anyio.create_task_group() as task_group:
        # run until first is complete
        async def run_chatroom_ws_receiver() -> None:
            await ws_receiver(websocket=websocket)
            task_group.cancel_scope.cancel()

        task_group.start_soon(run_chatroom_ws_receiver)
        await ws_sender(websocket)


@dataclass
class SocketResponseMessage:
    action: str 
    user: str 
    payload: dict 

    @property 
    def message(self):
        return json.dumps(self.payload)
    
    def export(self):
        return json.dumps({"action": self.action, "user": self.user, "message": self.message})
    

queue = {}


def hydrate_message(message: str):
    return json.loads(message)


def extract_request(payload: dict):
    return eval(payload['message'])


def process_request(request):
    return {'experiment_id': request['experiment_id'], 'results': {}}


async def ws_receiver(websocket):
    """Recieve and process payloads"""
    async for message in websocket.iter_text():
        print(f'Reciever got raw message', message)
        payload = hydrate_message(message)
        action = payload['action']
        user = payload['user']
        request = extract_request(payload)
        sim = compile_simulation()
        t = sim.save_times
        output_data = process_request(request)
        response = SocketResponseMessage(action=action, user=user, payload=output_data)
        await broadcast.publish(channel="chatroom", message=response.export())


async def ws_sender(websocket):
    """Send to the message board UI element for rendering"""
    async with broadcast.subscribe(channel="chatroom") as subscriber:
        async for event in subscriber:
            print(f'Sender detetcted an event and is sending the message: {event.message}')
            await websocket.send_text(event.message)


routes = [
    Route("/", homepage),
    WebSocketRoute("/", chatroom_ws, name='chatroom_ws'),
]


app = Starlette(
    routes=routes, on_startup=[broadcast.connect], on_shutdown=[broadcast.disconnect],
)


test_request = {'experiment_id': 'A', 'state': {'x': 11.11, 'y': 2.22}}