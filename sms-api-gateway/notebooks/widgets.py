import json
import pprint
import threading
import dataclasses as dc 
from matplotlib import pyplot as plt
import pandas as pd
import seaborn as sns 
import requests
from sseclient import SSEClient
import ipywidgets as widgets
from IPython.display import display as idisplay, clear_output


@dc.dataclass
class BulkResult:
    id: str 
    count: int 
    submasses: list[float]


@dc.dataclass
class IntervalResponse:
    experiment_id: str 
    duration: int 
    interval_id: str 
    results: dict[str, list[BulkResult | dict]]

    def __post_init__(self):
        bulk_data = []
        for item in self.results['bulk']:
            item_data = BulkResult(**item)
            bulk_data.append(item_data)
        self.results['bulk'] = bulk_data


class Viewer:
    data = {}

    @classmethod
    def render_data(cls, event, output_area):
        # TODO: create a more general "interval dashboard": escher x bulk submasses x bulk counts
        # TODO: render escher from fluxes listeners
        output_packet = IntervalResponse(**json.loads(event.data))
        names = []
        counts = []
        for result in output_packet.results['bulk']:
            names.append(result.id)
            counts.append(result.count)
        counts_i = dict(zip(names, counts))
        for name, count in cls.data.items():
            if name in counts_i:
                cls.data[name] += count
            else:
                cls.data[name] = count

        # with output_area:
        #     plt.figure(figsize=(6, 4))
        #     sns.barplot(data=counts_i)
        #     plt.tight_layout()
        #     plt.show()

        print(f"Interval ID: {output_packet.interval_id}")
        pprint.pp(output_packet)
        print()

    @classmethod
    def start(cls):
        # -- ui elements -- #
        run_button = widgets.Button(description="Run")
        cancel_button = widgets.Button(description="Cancel", disabled=True)
        output_area = widgets.Output()
        metadata_area = widgets.Output()
        idisplay(run_button, cancel_button, output_area, metadata_area)

        # -- threading config -- #
        stop_event = threading.Event()
        stream_thread = None

        def stream_sse(url, output_widget, metadata_widget):
            stop_event.clear()
            output_widget.clear_output()
            
            try:
                experiment_id = None
                with requests.get(url, stream=True) as response:
                    client = SSEClient(response)
                    with output_widget:
                        for event in client.events():
                            if stop_event.is_set():
                                print("Stream cancelled.")
                                break
                            
                            # NOTE: here is where we actually render the data
                            # display metadata
                            if experiment_id is None:
                                # case: is first iteration
                                data0 = json.loads(event.data)
                                experiment_id = data0['experiment_id']
                                with metadata_widget:
                                    print(f'Running experiment: {experiment_id}')

                            # render/display interval data
                            cls.render_data(event, output_widget)
            except Exception as e:
                with output_widget:
                    print(f"Error: {e}")

        def on_run_clicked(b):
            global stream_thread
            run_button.disabled = True
            cancel_button.disabled = False

            stream_url = "http://0.0.0.0:8080/api/v1/core/run-simulation"
            stream_thread = threading.Thread(target=stream_sse, args=(stream_url, output_area, metadata_area))
            stream_thread.start()

        def on_cancel_clicked(b):
            stop_event.set()
            run_button.disabled = False
            cancel_button.disabled = True
            if stream_thread is not None:
                stream_thread.join()

        run_button.on_click(on_run_clicked)
        cancel_button.on_click(on_cancel_clicked)


def start():
    return Viewer.start()
