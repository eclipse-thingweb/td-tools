"""LoRaWAN Web of Things (WoT) binding tools.

This package converts W3C WoT Thing Descriptions (TDs) that carry a LoRaWAN
payload binding into the MultiTech / LoRa Alliance Payload Schema language,
generates TDs back from those schemas, and decodes device uplinks by driving the
MultiTech reference interpreter.
"""

from lorawan_wot.converter import ConversionError, td_to_payload_schema
from lorawan_wot.schema_to_td import (
    SkipReason,
    UnsupportedSchemaError,
    payload_schema_to_td,
)

__all__ = [
    "ConversionError",
    "SkipReason",
    "UnsupportedSchemaError",
    "payload_schema_to_td",
    "td_to_payload_schema",
]
