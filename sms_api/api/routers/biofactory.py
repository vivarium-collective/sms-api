import logging

from fastapi import APIRouter

from sms_api.common.gateway.models import RouterConfig

logger = logging.getLogger(__name__)

config = RouterConfig(router=APIRouter(), prefix="/biofactory", dependencies=[])
