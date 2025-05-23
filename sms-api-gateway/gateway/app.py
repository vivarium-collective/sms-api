from dataclasses import asdict, dataclass
import json
import os
import pickle
import shutil
import tempfile

from fastapi import FastAPI, Query, WebSocket
from fastapi.responses import HTMLResponse
import numpy as np
from fastapi.middleware.cors import CORSMiddleware

from gateway.dispatch import compile_simulation, dispatch_simulation


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = """
<!DOCTYPE html>
<html>
    <head>
        <title>SMS</title>
    </head>
    <body>
        <h1>Results</h1>
        <ul id='messages'></ul>
        <script>
            function submit(dur=11.11, step=2.22) {
                const socket = new WebSocket(`ws://0.0.0.0:8080/ws`);

                socket.onopen = () => {
                    console.log("WebSocket connection opened.");
                    const requestPayload = `${dur},${step}`;
                    socket.send(requestPayload);
                    console.log("Sent: 11.11,2.22");
                };

                socket.onmessage = (event) => {
                    console.log("Received:", event.data);
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode(event.data)
                    message.appendChild(content)
                    messages.appendChild(message)
                };

                socket.onerror = (error) => {
                    console.error("WebSocket error:", error);
                };

                socket.onclose = () => {
                    console.log("WebSocket connection closed.");
                };
            }
            submit();
        </script>
    </body>
</html>
"""

@dataclass
class BulkMolecule:
    id: str 
    count: int 
    submasses: list[float]

    def dict(self):
        return asdict(self)


@app.get("/")
async def get():
    return HTMLResponse(client)


def extract_request_params(payload: str):
    """Expects positional string of <duration>,<timestep>"""
    return [json.loads(p) for p in payload.split(',')]


async def simulate(input_state, ws: WebSocket):
    dur = input_state['total_time']
    dt = input_state['time_step']
    exp_id = input_state['experiment_id']
    response_template = {"experiment_id": exp_id}
    t = np.arange(1, dur, dt)
    datadir = tempfile.mkdtemp()
    sim = compile_simulation(experiment_id=exp_id, duration=dur, time_step=dt, datadir=datadir, build=False)
    for t_i in t:
        sim.total_time = dur
        sim.save_times = [t_i]
        sim.build_ecoli()
        sim.run()
        filepath = os.path.join(datadir, f"vivecoli_t{t_i}.json")
        with open(filepath, 'r') as f:
            result_i = json.load(f)["agents"]["0"]
        
        bulk_mols_i = []
        for mol in result_i["bulk"]:
            mol_id = mol.pop(0)
            mol_count = mol.pop(0)
            bulk_mol = BulkMolecule(id=mol_id, count=mol_count, submasses=mol)
            bulk_mols_i.append(bulk_mol.dict())
        # {"bulk": result_i["bulk"]}
        resp_i = json.dumps({**response_template, "interval_id": str(t_i), "results": {"bulk": bulk_mols_i}})
        await ws.send_text(resp_i)
    shutil.rmtree(datadir)
        

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        payload = await websocket.receive_text()
        dur, time_step = extract_request_params(payload)
        state = {
            "total_time": dur,
            "time_step": time_step,
            "experiment_id": "test"
        }
        await simulate(state, websocket)
        # msg = json.dumps({'results': f"Message text was: {duration}"})
        # await websocket.send_text(msg)