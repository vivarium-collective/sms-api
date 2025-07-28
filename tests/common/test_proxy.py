import os
import socket
import tempfile
import time
from textwrap import dedent

import requests
from testcontainers.core.container import DockerContainer  # type: ignore [import-untyped]

from sms_api.common.proxy.models import KernelInfo
from sms_api.common.proxy.utils import set_nginx_kernel_paths


def test_simple_proxy(simple_inline_nginx_conf_path: str) -> None:
    """
    Test a simple NGINX proxy configuration.
    This test uses an inline NGINX configuration provided by the fixture.
    """
    # Start the NGINX container with the inline configuration
    with (
        DockerContainer("nginx:1.25")
        .with_exposed_ports(8080)
        .with_volume_mapping(simple_inline_nginx_conf_path, "/etc/nginx/nginx.conf") as nginx
    ):
        host = nginx.get_container_host_ip()
        port = int(nginx.get_exposed_port(8080))
        # Wait for NGINX to start
        time.sleep(2)
        resp = requests.get(f"http://{host}:{port}/", timeout=5)
        print(nginx.get_logs())
        print(resp.status_code, resp.text)
        assert resp.status_code == 200
        assert resp.text == "hello world"


def test_path1_proxy(simple_path1_nginx: tuple[int, str, str]) -> None:
    port, host, expected_response_text = simple_path1_nginx
    resp = requests.get(f"http://{host}:{port}/", timeout=5)
    print(resp.status_code, resp.text)
    assert resp.status_code == 200
    assert resp.text == expected_response_text


def test_direct_path_proxy(simple_path1_nginx: tuple[int, str, str], simple_path2_nginx: tuple[int, str, str]) -> None:
    """
    this tests the proxy where each path is defined separately in the NGINX config (no regex or maps).
    """
    port1, host1, response1 = simple_path1_nginx
    port2, host2, response2 = simple_path2_nginx

    # the target machines are in different containers, so we need to use the host IP
    host_ip = get_local_ip()

    # test direct connection to path1
    resp = requests.get(f"http://{host1}:{port1}/", timeout=5)
    print(resp.status_code, resp.text)
    assert resp.status_code == 200
    assert resp.text == response1

    # test direct connection to path2
    resp = requests.get(f"http://{host2}:{port2}/", timeout=5)
    print(resp.status_code, resp.text)
    assert resp.status_code == 200
    assert resp.text == response2

    proxy_config = dedent(f"""
        worker_processes  1;
        events {{ worker_connections  1024; }}
        error_log  /var/log/nginx/error.log debug;

        http {{
            server {{
                listen 8080 default_server;

                location = /path1 {{
                    proxy_pass http://{host_ip}:{port1}/;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                }}

                location = /path2 {{
                    proxy_pass http://{host_ip}:{port2}/;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                }}

                location / {{
                    return 404;
                }}
            }}
        }}
    """)

    # Start the two target NGINX containers for job1234 and job5678
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create temporary files for the NGINX configurations
        proxy_config_path = os.path.join(tmpdir, "nginx.conf")
        with open(proxy_config_path, "w") as f:
            f.write(proxy_config)

        with (
            DockerContainer("nginx:1.25")
            .with_exposed_ports(8080)
            .with_volume_mapping(proxy_config_path, "/etc/nginx/nginx.conf") as nginx
        ):
            print(nginx.get_logs())
            # Wait for the proxy NGINX container to start
            proxy_port = int(nginx.get_exposed_port(8080))
            proxy_host = nginx.get_container_host_ip()
            # first test that the basic response is not available (root path)
            resp1 = requests.get(f"http://{proxy_host}:{proxy_port}/", timeout=5)
            assert resp1.status_code == 404

            # test that path1 is correctly proxied
            resp1 = requests.get(f"http://{proxy_host}:{proxy_port}/path1", timeout=5)
            assert resp1.status_code == 200
            assert resp1.text == response1

            # test that path2 is correctly proxied
            resp1 = requests.get(f"http://{proxy_host}:{proxy_port}/path2", timeout=5)
            assert resp1.status_code == 200
            assert resp1.text == response2


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't have to be reachable
        s.connect(("8.8.8.8", 80))
        ip = str(s.getsockname()[0])
    finally:
        s.close()
    return ip


def test_static_map_proxy(simple_path1_nginx: tuple[int, str, str], simple_path2_nginx: tuple[int, str, str]) -> None:
    """
    this tests the proxy where each path is hard-coded to a specific NGINX container.
    """
    port1, host1, response1 = simple_path1_nginx
    port2, host2, response2 = simple_path2_nginx

    # the target machines are in different containers, so we need to use the host IP
    host_ip = get_local_ip()

    # test direct connection to path1
    resp = requests.get(f"http://{host1}:{port1}/", timeout=5)
    print(resp.status_code, resp.text)
    assert resp.status_code == 200
    assert resp.text == response1

    # test direct connection to path2
    resp = requests.get(f"http://{host2}:{port2}/", timeout=5)
    print(resp.status_code, resp.text)
    assert resp.status_code == 200
    assert resp.text == response2

    proxy_config = dedent(f"""
        worker_processes  1;
        events {{ worker_connections  1024; }}
        error_log  /var/log/nginx/error.log debug;


        http {{
            map $jobid $upstream {{
                default 0;
                job1234 {host_ip}:{port1};
                job5678 {host_ip}:{port2};
            }}

            server {{
                listen 8080 default_server;

                location ~ ^/kernel/(?<jobid>[^/]+)/ {{
                    proxy_pass http://$upstream/;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                }}

                location / {{
                    return 404;
                }}
            }}
        }}
    """)

    # Start the two target NGINX containers for job1234 and job5678
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create temporary files for the NGINX configurations
        proxy_config_path = os.path.join(tmpdir, "nginx.conf")
        with open(proxy_config_path, "w") as f:
            f.write(proxy_config)

        with (
            DockerContainer("nginx:1.25")
            .with_exposed_ports(8080)
            .with_volume_mapping(proxy_config_path, "/etc/nginx/nginx.conf") as nginx
        ):
            print(nginx.get_logs())
            # Wait for the proxy NGINX container to start
            proxy_port = int(nginx.get_exposed_port(8080))
            proxy_host = nginx.get_container_host_ip()
            # first test that the basic response is not available (root path)
            resp1 = requests.get(f"http://{proxy_host}:{proxy_port}/", timeout=5)
            assert resp1.status_code == 404

            # test that path1 is correctly proxied
            resp1 = requests.get(f"http://{proxy_host}:{proxy_port}/kernel/job1234/", timeout=5)
            assert resp1.status_code == 200
            assert resp1.text == response1

            # test that path2 is correctly proxied
            resp1 = requests.get(f"http://{proxy_host}:{proxy_port}/kernel/job5678/", timeout=5)
            assert resp1.status_code == 200
            assert resp1.text == response2


def test_dynamic_map_proxy(simple_path1_nginx: tuple[int, str, str], simple_path2_nginx: tuple[int, str, str]) -> None:
    """
    this tests the proxy where each path is dynamically added to the NGINX config.
    """
    port1, host1, response1 = simple_path1_nginx
    port2, host2, response2 = simple_path2_nginx
    job_id_1 = "job1234"
    job_id_2 = "job5678"

    # the target machines are in different containers, so we need to use the host IP
    host_ip = get_local_ip()

    # test direct connection to path1
    resp = requests.get(f"http://{host1}:{port1}/", timeout=5)
    print(resp.status_code, resp.text)
    assert resp.status_code == 200
    assert resp.text == response1

    # test direct connection to path2
    resp = requests.get(f"http://{host2}:{port2}/", timeout=5)
    print(resp.status_code, resp.text)
    assert resp.status_code == 200
    assert resp.text == response2

    proxy_config = dedent("""
        worker_processes  1;
        events { worker_connections  1024; }
        error_log  /var/log/nginx/error.log debug;

        http {
            map $jobid $upstream {
                default 0;
                #INSERT_MAP_ENTRIES_HERE
            }

            server {
                listen 8080 default_server;

                location ~ ^/kernel/(?<jobid>[^/]+)/ {
                    proxy_pass http://$upstream/;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                }

                location / {
                    return 404;
                }
            }
        }
    """)

    # Start the two target NGINX containers for job1234 and job5678
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create temporary files for the NGINX configurations
        proxy_config_path = os.path.join(tmpdir, "nginx.conf")
        with open(proxy_config_path, "w") as f:
            f.write(proxy_config)

        with (
            DockerContainer("nginx:1.25")
            .with_exposed_ports(8080)
            .with_volume_mapping(proxy_config_path, "/etc/nginx/nginx.conf") as nginx
        ):
            print(nginx.get_logs())
            # Wait for the proxy NGINX container to start
            proxy_port = int(nginx.get_exposed_port(8080))
            proxy_host = nginx.get_container_host_ip()

            # first test that the basic response is not available (root path)
            resp1 = requests.get(f"http://{proxy_host}:{proxy_port}/", timeout=5)
            assert resp1.status_code == 404

            # BEFORE ADDING ROUTES - the paths should give 502 (Bad Gateway) since they are not defined yet
            assert requests.get(f"http://{proxy_host}:{proxy_port}/kernel/{job_id_1}/", timeout=5).status_code == 502
            assert requests.get(f"http://{proxy_host}:{proxy_port}/kernel/{job_id_2}/", timeout=5).status_code == 502

            kernel_1 = KernelInfo(job_id=job_id_1, host=host_ip, port=port1, kernel_token="<fake-token1>")  # noqa: S106
            kernel_2 = KernelInfo(job_id=job_id_2, host=host_ip, port=port2, kernel_token="<fake-token2>")  # noqa: S106

            #
            # TEST THAT PATH1 IS PROXIED CORRECTLY
            #

            # rewrite the NGINX config with the new mapping and reload nginx in the proxy container
            new_config = set_nginx_kernel_paths(
                config_template=proxy_config, placeholder="#INSERT_MAP_ENTRIES_HERE", kernels=[kernel_1]
            )
            with open(proxy_config_path, "w") as f:
                f.write(new_config)
            exec_response: tuple[int, bytes] = nginx.exec("nginx -s reload")
            assert exec_response[0] == 0
            time.sleep(2)

            # test that path1 is correctly proxied
            resp = requests.get(f"http://{proxy_host}:{proxy_port}/kernel/{job_id_1}/", timeout=5)
            assert resp.status_code == 200
            assert resp.text == response1

            # test that path2 is still not available
            assert requests.get(f"http://{proxy_host}:{proxy_port}/kernel/{job_id_2}/", timeout=5).status_code == 502

            #
            # TEST THAT PATH1 AND PATH2 IS PROXIED CORRECTLY
            #

            # rewrite the NGINX config with the new mapping and reload nginx in the proxy container
            new_config = set_nginx_kernel_paths(
                config_template=proxy_config, placeholder="#INSERT_MAP_ENTRIES_HERE", kernels=[kernel_1, kernel_2]
            )
            with open(proxy_config_path, "w") as f:
                f.write(new_config)
            exec_response = nginx.exec("nginx -s reload")
            assert exec_response[0] == 0
            time.sleep(2)

            # test that path1 is correctly proxied
            resp = requests.get(f"http://{proxy_host}:{proxy_port}/kernel/{job_id_1}/", timeout=5)
            assert resp.status_code == 200
            assert resp.text == response1

            # test that path2 is correctly proxied
            resp = requests.get(f"http://{proxy_host}:{proxy_port}/kernel/{job_id_2}/", timeout=5)
            assert resp.status_code == 200
            assert resp.text == response2
