"""Constants for the Tandoor integration."""

from datetime import timedelta

DOMAIN = "tandoor"

SHOPPING_UPDATE_INTERVAL = timedelta(seconds=60)
MEALPLAN_UPDATE_INTERVAL = timedelta(minutes=5)
MEALPLAN_DAYS = 7
