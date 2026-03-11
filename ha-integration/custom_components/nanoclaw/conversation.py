from __future__ import annotations

import aiohttp
from homeassistant.components.conversation import ConversationEntity, ConversationInput, ConversationResult, MATCH_ALL
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_API_KEY, CONF_URL, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([NanoClawAgent(entry)], True)


class NanoClawAgent(ConversationEntity):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._url = entry.data[CONF_URL]
        self._api_key = entry.data[CONF_API_KEY]
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = None

    @property
    def name(self) -> str:
        return "NanoClaw"

    @property
    def state(self) -> str:
        return "idle"

    @property
    def supported_languages(self) -> str:
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_write_ha_state()

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        response = intent.IntentResponse(language=user_input.language)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._url}/chat",
                    json={"text": user_input.text, "api_key": self._api_key},
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data.get("response", "No response received.")
                    elif resp.status == 401:
                        text = "Authentication failed. Check your NanoClaw API key."
                    else:
                        text = f"NanoClaw returned an error (status {resp.status})."
        except aiohttp.ClientConnectorError:
            text = "Cannot connect to NanoClaw. Is the server running?"
        except TimeoutError:
            text = "NanoClaw took too long to respond."
        except Exception as err:  # noqa: BLE001
            text = f"Error: {err}"

        response.async_set_speech(text)
        return ConversationResult(
            response=response,
            conversation_id=user_input.conversation_id,
        )
