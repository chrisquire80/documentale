"""
Configurazione centralizzata del rate limiter (slowapi).

Il limiter è definito qui per evitare import circolari tra main.py
e i singoli router (auth, documents, ecc.).

Limiti applicati:
  - POST /auth/login    → 10 tentativi/minuto per IP  (anti brute-force)
  - POST /auth/logout   →  30/minuto per IP
  - POST /documents/upload  → 20 upload/minuto per IP
  - GET  /documents/search  → 120 ricerche/minuto per IP
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
