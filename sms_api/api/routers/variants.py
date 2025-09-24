import logging

from sms_api.common.gateway.utils import router_config

logger = logging.getLogger(__name__)

config = router_config(prefix="variants")
