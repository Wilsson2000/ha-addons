# Miele lokal

Lägen (`mode`):

- `probe`: läser bara. Testar vilka lokala adresser maskinen på `host` svarar på. Ändrar ingenting.
- `commission`: skickar en egen nyckel till maskinen (kräver att Miele@home är återställd och att maskinen är på hemmanätet). Nyckeln sparas i appens /data.
- `run`: läser status var `poll_seconds` sekund och publicerar via MQTT discovery. Knappar för Väck och Starta.
