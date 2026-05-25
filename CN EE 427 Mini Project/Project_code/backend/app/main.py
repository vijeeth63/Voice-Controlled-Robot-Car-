import logging
import os
from pathlib import Path
from typing import Literal

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

_esp_session = requests.Session()
_esp_session.headers.update({"Connection": "keep-alive"})

CMD_TO_PATH: dict[str, str] = {
    "forward": "F",
    "backward": "B",
    "left": "L",
    "right": "R",
    "stop": "S",
}

SPEED_TO_PATH: dict[str, str] = {
    "LOW": "SPD/LOW",
    "MED": "SPD/MED",
    "HIGH": "SPD/HIGH",
}


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v is not None and v != "" else default


def _cors_origins() -> list[str]:
    raw = _env("CORS_ORIGINS", "http://localhost:5173") or "http://localhost:5173"
    return [o.strip() for o in raw.split(",") if o.strip()]


def _esp_base() -> str:
    return (_env("ESP32_BASE_URL", "http://192.168.1.192") or "http://192.168.1.192").rstrip("/")


def _esp_http_timeouts() -> tuple[float, float]:
    """Connect and read timeouts (seconds). ESP32 handlers often block on motors."""
    try:
        c = float(_env("ESP32_HTTP_CONNECT_TIMEOUT", "2") or "2")
    except ValueError:
        c = 2.0
    try:
        r = float(_env("ESP32_HTTP_READ_TIMEOUT", "12") or "12")
    except ValueError:
        r = 12.0
    return (c, r)


def _check_api_key(x_api_key: str | None) -> None:
    expected = _env("BRIDGE_API_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="Server misconfigured: BRIDGE_API_KEY not set")
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _esp_get(path: str) -> tuple[requests.Response | None, bool]:
    """
    GET path on the ESP32 (path is e.g. F, B, SPD/LOW).

    Returns (response, read_timed_out). If read_timed_out is True, the TCP request
    was sent but the body did not arrive in time — many firmwares still execute the command.
    """
    url = f"{_esp_base()}/{path.lstrip('/')}"
    timeouts = _esp_http_timeouts()
    try:
        r = _esp_session.get(url, timeout=timeouts)
        return (r, False)
    except requests.exceptions.ReadTimeout:
        logger.warning(
            "ESP HTTP read timeout for %s (timeouts=%s; command may still have run)",
            url,
            timeouts,
        )
        return (None, True)
    except requests.exceptions.RequestException as e:
        logger.exception("ESP request failed for %s", url)
        raise HTTPException(status_code=502, detail=f"Could not reach ESP32: {e!s}") from e


class CommandBody(BaseModel):
    cmd: Literal["forward", "backward", "left", "right", "stop"] = Field(
        description="Motion command"
    )


class SpeedBody(BaseModel):
    speed: Literal["LOW", "MED", "HIGH"] = Field(description="Speed level")


app = FastAPI(title="Robot Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/command")
def api_command(
    body: CommandBody,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict:
    _check_api_key(x_api_key)
    r, slow = _esp_get(CMD_TO_PATH[body.cmd])
    if slow:
        return {"ok": True, "cmd": body.cmd, "esp_warning": "read_timeout"}
    assert r is not None
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"ESP32 returned HTTP {r.status_code}")
    return {"ok": True, "cmd": body.cmd, "esp_body": r.text}


@app.post("/api/speed")
def api_speed(
    body: SpeedBody,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict:
    _check_api_key(x_api_key)
    r, slow = _esp_get(SPEED_TO_PATH[body.speed])
    if slow:
        return {"ok": True, "speed": body.speed, "esp_warning": "read_timeout"}
    assert r is not None
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"ESP32 returned HTTP {r.status_code}")
    return {"ok": True, "speed": body.speed, "esp_body": r.text}
