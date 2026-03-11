import voluptuous as vol
from homeassistant import config_entries

from .const import CONF_API_KEY, CONF_URL, DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, description={"suggested_value": "http://192.168.8.182:3002"}): str,
        vol.Required(CONF_API_KEY): str,
    }
)


class NanoClawConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            url = user_input[CONF_URL].rstrip("/")
            return self.async_create_entry(
                title="NanoClaw",
                data={CONF_URL: url, CONF_API_KEY: user_input[CONF_API_KEY]},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )
