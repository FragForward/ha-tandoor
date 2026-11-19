"""Config flow for the Tandoor integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_TOKEN, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TandoorAuthenticationError, TandoorClient, TandoorConnectionError
from .const import (
    CONF_BRING_ENTITY,
    CONF_ESSENSPLAN_URL,
    CONF_SHOPPING_AMOUNT_IN_DESCRIPTION,
    DEFAULT_ESSENSPLAN_URL,
    DOMAIN,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_API_TOKEN): str,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
)


class TandoorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tandoor."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> TandoorOptionsFlow:
        """Create the options flow."""
        return TandoorOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            url = user_input[CONF_URL].rstrip("/")
            user_input[CONF_URL] = url
            client = TandoorClient(
                base_url=url,
                api_token=user_input[CONF_API_TOKEN],
                session=async_get_clientsession(
                    self.hass, verify_ssl=user_input[CONF_VERIFY_SSL]
                ),
            )
            try:
                space = await client.get_space()
            except TandoorAuthenticationError:
                errors["base"] = "invalid_auth"
            except TandoorConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(url.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=space.name or "Tandoor", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )


class TandoorOptionsFlow(OptionsFlow):
    """Options flow: Kochliste URL, Bring entity and shopping list format."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            user_input[CONF_ESSENSPLAN_URL] = (
                user_input.get(CONF_ESSENSPLAN_URL) or ""
            ).strip().rstrip("/")
            # EntitySelector omits the key when cleared — store "" explicitly
            user_input[CONF_BRING_ENTITY] = (
                user_input.get(CONF_BRING_ENTITY) or ""
            ).strip()
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_ESSENSPLAN_URL, DEFAULT_ESSENSPLAN_URL
        )
        current_bring = self.config_entry.options.get(CONF_BRING_ENTITY, "")
        current_desc = bool(
            self.config_entry.options.get(CONF_SHOPPING_AMOUNT_IN_DESCRIPTION, False)
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ESSENSPLAN_URL,
                        default="",
                        description={"suggested_value": current},
                    ): str,
                    vol.Optional(
                        CONF_BRING_ENTITY,
                        description={"suggested_value": current_bring or None},
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="todo")
                    ),
                    vol.Optional(
                        CONF_SHOPPING_AMOUNT_IN_DESCRIPTION, default=current_desc
                    ): bool,
                }
            ),
        )
