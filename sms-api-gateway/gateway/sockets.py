import anyio
from broadcaster import Broadcast
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.templating import Jinja2Templates

from data_model.messages import Packet


BROADCAST_PORT = "8080"

broadcast = Broadcast(f"memory://localhost:{BROADCAST_PORT}")
templates = Jinja2Templates("resources/client_templates")


async def homepage(request):
    template = "index.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context)


async def chatroom_ws(websocket):
    await websocket.accept()

    async with anyio.create_task_group() as task_group:
        # run until first is complete
        async def run_chatroom_ws_receiver() -> None:
            await chatroom_ws_receiver(websocket=websocket)
            task_group.cancel_scope.cancel()

        task_group.start_soon(run_chatroom_ws_receiver)
        await chatroom_ws_sender(websocket)


async def chatroom_ws_receiver(websocket):
    async for message in websocket.iter_text():
        await broadcast.publish(channel="chatroom", message=message)
        print(f'Got user input:\n{message}')


async def chatroom_ws_sender(websocket):
    print(f'Got websocket: {dir(websocket)}, {websocket.url}')
    async with broadcast.subscribe(channel="chatroom") as subscriber:
        async for event in subscriber:
            await websocket.send_text(event.message)


routes = [
    Route("/run", homepage),
    WebSocketRoute("/run", chatroom_ws, name='chatroom_ws'),
]
