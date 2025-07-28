from sms_api.common.proxy.models import KernelInfo


def set_nginx_kernel_paths(config_template: str, placeholder: str, kernels: list[KernelInfo]) -> str:
    map_contents = ""
    for kernelInfo in kernels:
        map_contents += f'        {kernelInfo.job_id} {kernelInfo.host}:{str(kernelInfo.port)};\n'

    return config_template.replace(placeholder, map_contents)
