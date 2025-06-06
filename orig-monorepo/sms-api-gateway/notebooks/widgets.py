import dataclasses as dc
import json
import pprint
import threading
import time
import uuid
import warnings
from collections.abc import Iterable
from typing import Any, Callable

import ipywidgets as iwidgets
import numpy as np
import requests
from data_model.api import WCMIntervalData, WCMIntervalResponse
from IPython.display import display as idisplay
from requests import Session
from sseclient import SSEClient
from tqdm.notebook import tqdm


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
        for item in self.results["bulk"]:
            item_data = BulkResult(**item)
            bulk_data.append(item_data)
        self.results["bulk"] = bulk_data


class AuthenticationError(Exception):
    pass


class ApiKeyValue:
    def __init__(self, v):
        self.value = v

    def show(self):
        from common.encryption.safe_data import from_binary

        return from_binary(self.value)

    def __repr__(self):
        import hashlib

        return hashlib.sha256(self.value.encode("utf-8")).hexdigest()


class Dashboard:
    _data = {}
    _url_root: str = "http://0.0.0.0:8080"

    def __init__(self, url_root: str | None = None, session: Session | None = None, *args, **kwargs):
        self.url_root = url_root or self._url_root
        self.session = session or Session()

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, v):
        self._data = v

    def __setitem__(self, k, v):
        import copy

        d = copy.deepcopy(self.data)
        d.update({k: v})
        self.data = d

    def set(self, dataname: str, dataval: Any):
        return self.__setitem__(dataname, dataval)

    def _increment_counts(self, output_packet: WCMIntervalResponse):
        names = []
        counts = []
        for result in output_packet.data.bulk:
            names.append(result.id)
            counts.append(result.count)
        counts_i = dict(zip(names, counts))
        for name, count in self.data.items():
            if name in counts_i:
                current = self.data[name]
                current += count
                self.set("name", current)
            else:
                self.set("name", count)

    def _plot_interval(self, output_packet: WCMIntervalResponse):
        # TODO: implement some nice plotting here: a dashboard with bigraph-viz, seaborn/plotly, etc
        # with output_area:
        #     plt.figure(figsize=(6, 4))
        #     sns.barplot(data=counts_i)
        #     plt.tight_layout()
        #     plt.show()
        pass

    def _render_data(self, output_packet: WCMIntervalResponse):
        # TODO: create a more general "interval dashboard": escher x bulk submasses x bulk counts
        # TODO: render escher from fluxes listeners
        self._increment_counts(output_packet)
        self._plot_interval(output_packet)

        print(f">> Interval ID: {output_packet.interval_id}")
        pprint.pp(output_packet.experiment_id)
        print()
        print(">> I promise that a dashboard will go here!\n")

    @classmethod
    def display_progress_bar(cls, t: Iterable[float], interval_generator: Callable, buffer: float) -> None:
        print(f"Running simulation for duration: {len(t)}...\n")
        for i in tqdm(t, desc="Fetching Results...", unit="step"):
            gen_i = iter(interval_generator(i))
            result_i = next(gen_i)
            print(f"IntervalID {i}:\n{result_i}\n")
            time.sleep(buffer)
        print("Done")

    def authenticate(
        self,
        username: str,
        key: str,
        auth_url: str = "http://0.0.0.0:8080/login",  # TODO: change this for prod
        verbose: bool = False,
    ) -> requests.Response:
        response = self.session.post(
            auth_url,
            data={"username": username, "password": key},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if verbose:
            print("Status Code:", response.status_code)
            print("Response JSON:", response.json())
            print("Cookies:", response.cookies.get_dict())
        if response.status_code != 200:
            warnings.warn(
                f"There was an issue with authentication as I just got a status code of: {response.status_code}"
            )
        return response

    def _start(
        self,
        experiment_name: str | None = None,
        duration: float = 11.0,
        time_step: float = 1.0,
        start_time: float = 0.01111,
        framesize: float = 1.0,
    ):
        exp_name = experiment_name or f"experiment-{uuid.uuid4()!s}"
        # -- ui elements -- #
        self.run_button = iwidgets.Button(description="Run")
        self.cancel_button = iwidgets.Button(description="Cancel", disabled=True)
        self.output_area = iwidgets.Output()
        self.metadata_area = iwidgets.Output()
        self.password_input = iwidgets.Password(
            continuous_update=False, description="Please enter password:", placeholder="Make it long!"
        )

        idisplay(self.run_button, self.cancel_button, self.output_area, self.metadata_area, self.password_input)

        # -- threading config -- #
        stop_event = threading.Event()
        stream_thread = None

        def stream_sse(url, output_widget, metadata_widget):
            stop_event.clear()
            output_widget.clear_output()
            try:
                query_params = {
                    "experiment_id": exp_name,
                    "total_time": duration,
                    "time_step": time_step,
                    "start_time": start_time,
                    "framesize": framesize,
                }
                t = np.arange(start_time, duration, time_step)
                with self.session.get(url, params=query_params, stream=True) as response:
                    client = SSEClient(response)
                    with output_widget:
                        print(f"Running simulation for duration: {len(t)}...\n")

                        stream_stopped = False
                        for idx, ti in enumerate(tqdm(t, desc="Processing Simulation...")):
                            if stream_stopped:
                                break
                            for event in client.events():
                                # get event status: break loop if cancelled
                                if stop_event.is_set():
                                    print("Stream cancelled.")
                                    stream_stopped = True
                                    break

                                raw_packet = json.loads(event.data)
                                raw_results = raw_packet.pop("results")
                                if raw_results is None:
                                    raise Exception("No results could be extracted")
                                results_n = WCMIntervalData(**raw_results)
                                kwargs = {**raw_packet, "data": results_n}
                                packet_n = WCMIntervalResponse(**kwargs)

                                # store data after datamodel validation-fit
                                for k, v in packet_n.data.dict().items():
                                    self.set(k, v)

                                # NOTE: here is where we actually render the response packet data
                                self._render_data(packet_n)
            except Exception as e:
                with output_widget:
                    print(f"Error: {e}")

        def on_run_clicked(b):
            global stream_thread
            self.run_button.disabled = True
            self.cancel_button.disabled = False

            stream_url = "http://0.0.0.0:8080/api/v1/core/run-simulation"
            stream_thread = threading.Thread(target=stream_sse, args=(stream_url, self.output_area, self.metadata_area))
            stream_thread.start()

        def on_cancel_clicked(b):
            stop_event.set()
            self.run_button.disabled = False
            self.cancel_button.disabled = True
            if stream_thread is not None:
                stream_thread.join()

        self.run_button.on_click(on_run_clicked)
        self.cancel_button.on_click(on_cancel_clicked)

    def up(self, username: str, duration: float = 11.0, time_step: float = 1.0):
        # key = collect_key()
        auth_resp = self.authenticate(username=username, key=self.password_input.value)  # key=key.show())
        if auth_resp.status_code != 200:
            raise AuthenticationError(f"User {username} could not be authenticated.")
        else:
            print(f"User: {username} has been successfully authenticated!")
        return self._start(duration, time_step)

    @staticmethod
    def collect_key():
        import getpass

        from common.encryption.safe_data import to_binary

        api_key = getpass.getpass("Enter your API key: ")
        return ApiKeyValue(to_binary(api_key))


dashboard = Dashboard()
