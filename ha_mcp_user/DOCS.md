# HA-MCP (användartoken)

Samma Home Assistant MCP Server som den officiella appen (`homeassistant-ai/ha-mcp`,
version i `build.yaml`), men den pratar med Home Assistant med en **långlivad token
från ett riktigt admin-konto** i stället för Supervisor-token.

Varför: Supervisor-token och HA-MCP-integrationens egen token tillhör systemanvändare
som inte kan logga in. Sådant som gäller per användare, till exempel Marketplace-varningen
i HA 2026.11, kan då aldrig godkännas. Med din egen token agerar servern som du.

## Inställning

1. Profil → Säkerhet → Långlivade åtkomsttokens → Skapa token (t.ex. "Claude MCP").
2. Klistra in den i `ha_token` här och starta appen.
3. Loggen visar MCP-adressen: `http://<ha-ip>:9583/private_...`.
   Exponera port 9583 via Cloudflare-tunneln och lägg till
   `https://<din-mcp-host>/private_...` som anpassad koppling i Claude.

`ha_url` kan lämnas tomt (standard `http://127.0.0.1:8123`, appen kör på host-nätverket).
Lämnas `ha_token` tomt faller appen tillbaka på Supervisor-token som originalet.

Alla övriga inställningar är originalappens, se
https://github.com/homeassistant-ai/ha-mcp/blob/master/homeassistant-addon/DOCS.md
