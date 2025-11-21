"""NATS implementation of the messaging service."""

import logging
from typing import Any

import nats
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg

from sms_api.common.messaging.messaging_service import MessageHandler, MessagingService

logger = logging.getLogger(__name__)


class MessagingServiceNATS(MessagingService):
    """NATS implementation of the messaging service."""

    def __init__(self) -> None:
        """Initialize the NATS messaging service."""
        self._client: NATSClient | None = None

    async def connect(self, url: str, **kwargs: Any) -> None:
        """Connect to the NATS server.

        Args:
            url: NATS server URL (e.g., "nats://localhost:4222")
            **kwargs: Additional NATS connection parameters
        """
        if self._client is not None and self._client.is_connected:
            logger.warning("NATS client is already connected")
            return

        logger.info(f"Connecting to NATS server at {url}")
        self._client = await nats.connect(url, **kwargs)
        logger.info("Successfully connected to NATS server")

    async def disconnect(self) -> None:
        """Disconnect from the NATS server."""
        if self._client is not None and self._client.is_connected:
            logger.info("Disconnecting from NATS server")
            await self._client.close()
            logger.info("Disconnected from NATS server")

    async def publish(self, subject: str, data: bytes) -> None:
        """Publish a message to a NATS subject.

        Args:
            subject: The NATS subject to publish to
            data: The message data as bytes

        Raises:
            RuntimeError: If not connected to NATS
        """
        if self._client is None or not self._client.is_connected:
            raise RuntimeError("Not connected to NATS server")

        await self._client.publish(subject, data)
        logger.debug(f"Published message to subject '{subject}'")

    async def subscribe(self, subject: str, callback: MessageHandler) -> None:
        """Subscribe to a NATS subject with a callback handler.

        Args:
            subject: The NATS subject to subscribe to
            callback: Async function to handle received messages

        Raises:
            RuntimeError: If not connected to NATS
        """
        if self._client is None or not self._client.is_connected:
            raise RuntimeError("Not connected to NATS server")

        async def nats_message_handler(msg: Msg) -> None:
            """Wrapper to convert NATS Msg to bytes for the callback."""
            await callback(msg.data)

        await self._client.subscribe(subject, cb=nats_message_handler)
        logger.info(f"Subscribed to NATS subject '{subject}'")

    def is_connected(self) -> bool:
        """Check if connected to NATS server.

        Returns:
            True if connected, False otherwise
        """
        return self._client is not None and self._client.is_connected
