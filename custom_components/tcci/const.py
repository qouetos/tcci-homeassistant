"""Constantes TCCI."""
from datetime import timedelta

DOMAIN = "tcci"
CONF_URL = "url"
CONF_TOKEN = "token"
SCAN_INTERVAL = timedelta(seconds=20)
EVENT_TCCI = "tcci_event"   # declenche a chaque nouvel appui (boitier, telephone ou HA)
HISTORY_DAYS = 60          # nuits exposees dans l'attribut "nuits" du capteur Historique
HISTORY_INTERVAL = 300     # s entre deux relectures de /api/nights
