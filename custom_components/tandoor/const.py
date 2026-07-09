"""Constants for the Tandoor integration."""

from datetime import timedelta

DOMAIN = "tandoor"

FRONTEND_VERSION = "0.3.2"
FRONTEND_URL = f"/{DOMAIN}-frontend/tandoor-mealplan-card.js"

SHOPPING_UPDATE_INTERVAL = timedelta(seconds=60)
MEALPLAN_UPDATE_INTERVAL = timedelta(minutes=5)
MEALPLAN_DAYS = 7
