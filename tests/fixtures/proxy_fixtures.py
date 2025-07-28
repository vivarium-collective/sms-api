import os
import tempfile
import time
from collections.abc import Generator
from textwrap import dedent

import pytest
from testcontainers.core.container import DockerContainer  # type: ignore [import-untyped]

parent_dir = os.path.dirname(__file__)


@pytest.fixture(scope="session")
def nginx_conf_path() -> str:
    conf_path = os.path.join(parent_dir, "data", "nginx.conf")
    if not os.path.exists(conf_path):
        raise FileNotFoundError(f"NGINX configuration file not found: {conf_path}")
    return conf_path


@pytest.fixture(scope="session")
def simple_inline_nginx_conf_path() -> str:
    conf_path = os.path.join(parent_dir, "data", "nginx_simple.conf")
    if not os.path.exists(conf_path):
        raise FileNotFoundError(f"NGINX configuration file not found: {conf_path}")
    return conf_path


@pytest.fixture(scope="session")
def simple_path1_nginx() -> Generator[tuple[int, str, str], None, None]:
    response_text = "path1 response"
    config_contents = dedent(f"""
        worker_processes  1;
        events {{
            worker_connections  1024;
        }}
        http {{
            server {{
                listen       8080;
                location / {{
                    return 200 '{response_text}';
                    add_header Content-Type text/plain;
                }}
            }}
        }}
    """)

    config_contents = config_contents.replace("RESPONSE_TEXT", response_text)
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "nginx.conf")
        with open(config_path, "w") as f:
            f.write(config_contents)

        with (
            DockerContainer("nginx:1.25")
            .with_exposed_ports(8080)
            .with_volume_mapping(config_path, "/etc/nginx/nginx.conf") as nginx
        ):
            host = nginx.get_container_host_ip()
            port = int(nginx.get_exposed_port(8080))
            time.sleep(2)
            yield port, host, response_text


@pytest.fixture(scope="session")
def simple_path2_nginx() -> Generator[tuple[int, str, str], None, None]:
    response_text = "path2 response"
    config_contents = dedent(f"""
        worker_processes  1;
        events {{
            worker_connections  1024;
        }}
        http {{
            server {{
                listen       8080;
                location / {{
                    return 200 '{response_text}';
                    add_header Content-Type text/plain;
                }}
            }}
        }}
    """)

    config_contents = config_contents.replace("RESPONSE_TEXT", response_text)
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "nginx.conf")
        with open(config_path, "w") as f:
            f.write(config_contents)

        with (
            DockerContainer("nginx:1.25")
            .with_exposed_ports(8080)
            .with_volume_mapping(config_path, "/etc/nginx/nginx.conf") as nginx
        ):
            host = nginx.get_container_host_ip()
            port = int(nginx.get_exposed_port(8080))
            time.sleep(2)
            yield port, host, response_text
