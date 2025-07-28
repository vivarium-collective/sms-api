from pydantic import BaseModel


class KernelInfo(BaseModel):
    job_id: str
    host: str
    port: int
    kernel_token: str
