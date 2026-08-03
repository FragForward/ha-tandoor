"""Constants for the Tandoor integration."""

from datetime import timedelta

DOMAIN = "tandoor"

FRONTEND_VERSION = "0.5.13"
FRONTEND_URL = f"/{DOMAIN}-frontend/tandoor-mealplan-card.js"

SHOPPING_UPDATE_INTERVAL = timedelta(seconds=60)
MEALPLAN_UPDATE_INTERVAL = timedelta(minutes=5)
MEALPLAN_DAYS = 7

# Kochliste (Essensplan website companion API, not part of Tandoor itself)
CONF_ESSENSPLAN_URL = "essensplan_url"
DEFAULT_ESSENSPLAN_URL = "http://192.168.1.4:8091"
CONF_BRING_ENTITY = "bring_entity"
KOCHLISTE_UPDATE_INTERVAL = timedelta(seconds=60)
