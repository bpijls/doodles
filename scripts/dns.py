"""Manage the doodles.feib.nl CNAME at TransIP, reusing pagelink's TransIP client and credentials.

Run from the pagelink checkout so its venv and `app` package are used (no secrets live in this repo):

    cd ~/projects/hva/pagelink
    PYTHONPATH=. .venv/bin/python ~/projects/doodles/scripts/dns.py list|add
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

from app.config import _decode_key
from app.transip import TransIP

ENV_FILE = os.environ.get("PAGELINK_ENV", str(Path.cwd() / ".env"))
DOMAIN, NAME, TARGET = "feib.nl", "doodles", "bpijls.github.io."


async def main(cmd: str) -> None:
    env = dotenv_values(ENV_FILE)
    key = _decode_key(env["TRANSIP_PRIVATE_KEY_B64"])
    global_key = env.get("TRANSIP_GLOBAL_KEY", "true").lower() == "true"
    async with httpx.AsyncClient(timeout=30) as client:
        t = TransIP(client, env["TRANSIP_LOGIN"], key, global_key=global_key)
        mine = [e for e in await t.list_dns(DOMAIN) if e["name"] == NAME]
        if cmd == "add" and not mine:
            await t.add_dns(DOMAIN, NAME, "CNAME", TARGET)
            mine = [e for e in await t.list_dns(DOMAIN) if e["name"] == NAME]
        print(f"{NAME}.{DOMAIN}:", mine or "no records")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("list", "add"):
        sys.exit(__doc__)
    asyncio.run(main(sys.argv[1]))
