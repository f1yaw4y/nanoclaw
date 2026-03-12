from __future__ import annotations

from collections import defaultdict

import aiohttp
from homeassistant.components.conversation import ConversationEntity, ConversationInput, ConversationResult, MATCH_ALL
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_API_KEY,
    CONF_MODEL,
    CONF_SYSTEM_PROMPT,
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    VENICE_API_URL,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([VeniceAiAgent(entry)], True)


class VeniceAiAgent(ConversationEntity):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._api_key = entry.data[CONF_API_KEY]
        self._model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        self._system_prompt = entry.data.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = None
        # Per-conversation history: conversation_id → list of messages
        self._history: dict[str, list[dict]] = defaultdict(list)

    @property
    def name(self) -> str:
        return "Venice AI"

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

        conv_id = user_input.conversation_id or user_input.device_id or "default"
        history = self._history[conv_id]
        history.append({"role": "user", "content": user_input.text})

        messages = [{"role": "system", "content": self._system_prompt}] + history

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    VENICE_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": self._model, "messages": messages},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = (
                            data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "No response received.")
                        )
                        history.append({"role": "assistant", "content": text})
                        # Keep history bounded to last 20 turns (40 messages)
                        if len(history) > 40:
                            self._history[conv_id] = history[-40:]
                    elif resp.status == 401:
                        text = "Authentication failed. Check your Venice AI API key."
                    else:
                        body = await resp.text()
                        text = f"Venice AI returned an error (status {resp.status}): {body[:200]}"
        except aiohttp.ClientConnectorError:
            text = "Cannot connect to Venice AI. Check your internet connection."
        except TimeoutError:
            text = "Venice AI took too long to respond."
        except Exception as err:  # noqa: BLE001
            text = f"Error: {err}"

        response.async_set_speech(text)
        return ConversationResult(
            response=response,
            conversation_id=conv_id,
        )
