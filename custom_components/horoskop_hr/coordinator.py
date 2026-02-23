"""Coordinators for Horoskop HR."""
from __future__ import annotations

import asyncio
import html as html_lib
import json
import logging
import re
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ATTRIBUTION,
    ATTR_SOURCE_URLS,
    BASE_URL,
    DEFAULT_SCHEDULED_TIMES,
    DEFAULT_TRANSLATION_ENABLED,
    DEFAULT_TRANSLATION_LANGUAGE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_USE_SCHEDULED_REFRESH,
    DOMAIN,
    SIGNS,
)

_LOGGER = logging.getLogger(__name__)


def _try_demojibake(text: str) -> str:
    """Best-effort recovery when UTF-8 was decoded with a legacy codepage."""
    candidates = [text]
    for src in ("latin-1", "cp1252", "cp1250"):
        try:
            candidates.append(text.encode(src).decode("utf-8"))
        except Exception:  # noqa: BLE001
            continue

    def _score(value: str) -> int:
        good = sum(value.count(ch) for ch in "čćžšđČĆŽŠĐ")
        bad = value.count("Ã") + value.count("Ä") + value.count("Å") + value.count("Ĺ") + value.count("�")
        return (good * 3) - (bad * 4)

    return max(candidates, key=_score)


def _normalize_match_text(text: str) -> str:
    """Normalize text for tolerant section-title matching."""
    value = _try_demojibake(_strip_tags(text)).lower()
    value = value.replace("č", "c").replace("ć", "c").replace("ž", "z").replace("š", "s").replace("đ", "d")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _strip_tags(text: str) -> str:
    """Convert HTML to plain text with stable spacing."""
    value = re.sub(r"(?i)<br\s*/?>", "\n", text)
    value = re.sub(r"<[^>]+>", "", value)
    value = html_lib.unescape(value)
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    cleaned = "\n".join([line for line in lines if line]).strip()
    repaired = _try_demojibake(cleaned)
    # Drop residual C1 controls that sometimes appear in mojibake payloads.
    repaired = re.sub(r"[\u0080-\u009f]", "", repaired)
    return repaired


def _extract_section(html: str, keyword: str) -> tuple[str | None, str]:
    """Extract date and text payload for one section."""
    wanted = _normalize_match_text(keyword)

    def _title_matches(title_norm: str) -> bool:
        if "mjesec" in wanted or "mjesec" in wanted or "mjese" in wanted:
            return ("horoskop" in title_norm) and (
                "mjesec" in title_norm or "mjesec" in title_norm or "mjese" in title_norm
            )
        if "tjedn" in wanted:
            return ("horoskop" in title_norm) and ("tjedn" in title_norm)
        if "dnevn" in wanted:
            return ("horoskop" in title_norm) and ("dnevn" in title_norm)
        return wanted in title_norm

    h3_match = None
    for match in re.finditer(r"<h3[^>]*>(.*?)</h3>", html, re.IGNORECASE | re.DOTALL):
        title_norm = _normalize_match_text(match.group(1))
        if _title_matches(title_norm):
            h3_match = match
            break

    if h3_match is None:
        return None, ""
    start = h3_match.end()
    next_h3 = re.search(r"<h3[^>]*>", html[start:], re.IGNORECASE)
    chunk = html[start : start + next_h3.start()] if next_h3 else html[start:]

    date_match = re.search(r'<div[^>]*class="[^"]*datum[^"]*"[^>]*>\s*(.*?)\s*</div>', chunk, re.IGNORECASE | re.DOTALL)
    raw_date = _strip_tags(date_match.group(1)) if date_match else None

    text_match = re.search(r"<p[^>]*>(.*?)</p>", chunk, re.IGNORECASE | re.DOTALL)
    raw_text = _strip_tags(text_match.group(1)) if text_match else ""
    return raw_date, raw_text


def _normalize_category(label: str) -> str | None:
    normalized = _strip_tags(label).upper().replace("&", "").replace(" ", "")
    if "LJUBAV" in normalized:
        return "ljubav"
    if "KARIJERA" in normalized or "POSAO" in normalized:
        return "posao"
    if "ZDRAVLJE" in normalized:
        return "zdravlje"
    return None


def _extract_weekly_scores(chunk: str) -> dict[str, int]:
    """Extract weekly star scores from image URLs."""
    scores: dict[str, int] = {}
    pattern = re.compile(
        r'<div[^>]*class="[^"]*zvijezda-text[^"]*"[^>]*>\s*([^:]+):\s*</div>\s*'
        r'<img[^>]+src="[^"]*zvijezde-(\d+)-5\.png"',
        re.IGNORECASE | re.DOTALL,
    )
    for label, score_str in pattern.findall(chunk):
        key = _normalize_category(label)
        if not key:
            continue
        try:
            scores[key] = max(1, min(5, int(score_str)))
        except ValueError:
            continue
    return scores


def _extract_weekly_split(text: str) -> dict[str, str]:
    """Split weekly text into category paragraphs."""
    sections: dict[str, str] = {}
    pattern = re.compile(
        r"(LJUBAV|KARIJERA|ZDRAVLJE(?:&SAVJET)?):\s*(.*?)(?=(?:LJUBAV|KARIJERA|ZDRAVLJE(?:&SAVJET)?):|$)",
        re.IGNORECASE | re.DOTALL,
    )
    for label, payload in pattern.findall(text):
        key = _normalize_category(label)
        if key:
            sections[key] = re.sub(r"\s+", " ", payload).strip()
    return sections


def _format_daily(sign_name: str, payload: dict[str, Any]) -> str:
    return f"{sign_name} ({payload.get('datum', '-')})\n{payload.get('tekst', '')}".strip()


def _format_weekly(sign_name: str, payload: dict[str, Any]) -> str:
    categories = payload.get("kategorija", {})
    parts = [f"{sign_name} ({payload.get('datum_od_do', '-')})"]
    for key in ("ljubav", "posao", "zdravlje"):
        entry = categories.get(key, {})
        score = entry.get("score")
        text = entry.get("tekst", "")
        parts.append(f"{key.upper()} [{score if score is not None else '-'} / 5]: {text}")
    return "\n".join(parts).strip()


def _format_monthly(sign_name: str, payload: dict[str, Any]) -> str:
    return f"{sign_name} ({payload.get('mjesec', '-')})\n{payload.get('tekst', '')}".strip()


def _decode_html(raw: bytes, declared_charset: str | None) -> str:
    """Decode HTML with robust fallback for Balkan encodings."""
    # Some pages are served with misleading charset headers.
    candidates = ["utf-8"]
    if declared_charset and declared_charset.lower() != "utf-8":
        candidates.append(declared_charset)
    candidates.extend(["cp1250", "iso-8859-2", "latin-1"])

    decoded: list[str] = []
    for charset in candidates:
        try:
            decoded.append(raw.decode(charset))
        except (LookupError, UnicodeDecodeError):
            continue

    if decoded:
        def _score(text: str) -> int:
            # Prefer strings with valid HR diacritics; penalize mojibake artifacts.
            good = sum(text.count(ch) for ch in "čćžšđČĆŽŠĐ")
            c1 = sum(1 for ch in text if 0x80 <= ord(ch) <= 0x9F)
            bad = text.count("Ã") + text.count("Ä") + text.count("Å") + text.count("Ĺ") + text.count("�") + c1
            return (good * 3) - (bad * 4)

        return max(decoded, key=_score)

    return raw.decode("utf-8", errors="replace")


def _parse_scheduled_times(raw: str) -> list[tuple[int, int]]:
    """Parse 'HH:MM,HH:MM' into a list of (hour, minute)."""
    out: list[tuple[int, int]] = []
    for token in (raw or "").split(","):
        part = token.strip()
        if not part:
            continue
        try:
            hour_s, minute_s = part.split(":", 1)
            hour = int(hour_s)
            minute = int(minute_s)
        except (ValueError, TypeError):
            continue
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            out.append((hour, minute))
    return sorted(set(out))


class HoroskopDataCoordinator(DataUpdateCoordinator):
    """Fetch and parse horoscope data from ehoroskop.net."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.translation_coordinator: HoroskopTranslationCoordinator | None = None
        self._unsub_schedule: list[Any] = []
        use_schedule = bool(entry.options.get("use_scheduled_refresh", DEFAULT_USE_SCHEDULED_REFRESH))
        interval = int(entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None if use_schedule else timedelta(seconds=interval),
        )

    async def async_setup_schedule(self) -> None:
        """Register exact-time refresh callbacks."""
        self.async_unload_schedule()
        use_schedule = bool(self.entry.options.get("use_scheduled_refresh", DEFAULT_USE_SCHEDULED_REFRESH))
        if not use_schedule:
            return

        raw_times = str(self.entry.options.get("scheduled_times", DEFAULT_SCHEDULED_TIMES))
        parsed = _parse_scheduled_times(raw_times)
        if not parsed:
            parsed = _parse_scheduled_times(DEFAULT_SCHEDULED_TIMES)

        for hour, minute in parsed:
            unsub = async_track_time_change(self.hass, self._handle_scheduled_refresh, hour=hour, minute=minute, second=0)
            self._unsub_schedule.append(unsub)
        _LOGGER.info("Horoskop HR scheduled refresh enabled at: %s", ", ".join(f"{h:02d}:{m:02d}" for h, m in parsed))

    def async_unload_schedule(self) -> None:
        """Remove schedule callbacks."""
        for unsub in self._unsub_schedule:
            try:
                unsub()
            except Exception:
                pass
        self._unsub_schedule.clear()

    async def _handle_scheduled_refresh(self, _now) -> None:
        """Refresh when scheduled time hits."""
        await self.async_request_refresh()

    async def _fetch_sign(self, slug: str, sign_name: str) -> dict[str, Any]:
        url = f"{BASE_URL}/{slug}/"
        session = async_get_clientsession(self.hass)
        async with session.get(url, timeout=30) as response:
            response.raise_for_status()
            raw = await response.read()
            html = _decode_html(raw, response.charset)

        daily_date, daily_text = _extract_section(html, "Dnevni horoskop")
        weekly_date, weekly_text = _extract_section(html, "Tjedni horoskop")
        monthly_date, monthly_text = _extract_section(html, "Mjesečni horoskop")
        if not monthly_text:
            # Fallback for occasional unaccented heading variants.
            monthly_date, monthly_text = _extract_section(html, "Mjesecni horoskop")

        weekly_h3 = re.search(r"<h3[^>]*>.*?-\s*Tjedni horoskop\s*</h3>", html, re.IGNORECASE | re.DOTALL)
        weekly_chunk = ""
        if weekly_h3:
            next_h3 = re.search(r"<h3[^>]*>", html[weekly_h3.end() :], re.IGNORECASE)
            weekly_chunk = (
                html[weekly_h3.end() : weekly_h3.end() + next_h3.start()]
                if next_h3
                else html[weekly_h3.end() :]
            )

        scores = _extract_weekly_scores(weekly_chunk)
        weekly_split = _extract_weekly_split(weekly_text)
        categories = {
            "ljubav": {"score": scores.get("ljubav"), "tekst": weekly_split.get("ljubav", "")},
            "posao": {"score": scores.get("posao"), "tekst": weekly_split.get("posao", "")},
            "zdravlje": {"score": scores.get("zdravlje"), "tekst": weekly_split.get("zdravlje", "")},
        }

        return {
            "slug": slug,
            "znak": sign_name,
            "url": url,
            "dnevni": {"datum": daily_date, "tekst": daily_text},
            "tjedni": {"datum_od_do": weekly_date, "kategorija": categories},
            "mjesecni": {"mjesec": monthly_date, "tekst": monthly_text},
        }

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            tasks = [self._fetch_sign(slug, sign_name) for slug, sign_name in SIGNS.items()]
            results = await asyncio.gather(*tasks)

            dnevni_raw: dict[str, Any] = {}
            tjedni_raw: dict[str, Any] = {}
            mjesecni_raw: dict[str, Any] = {}

            dnevni_formatted: dict[str, str] = {}
            tjedni_formatted: dict[str, str] = {}
            mjesecni_formatted: dict[str, str] = {}
            source_urls: dict[str, str] = {}

            for item in results:
                slug = item["slug"]
                sign_name = item["znak"]
                source_urls[slug] = item["url"]
                dnevni_raw[slug] = {"znak": sign_name, "url": item["url"], **item["dnevni"]}
                tjedni_raw[slug] = {"znak": sign_name, "url": item["url"], **item["tjedni"]}
                mjesecni_raw[slug] = {"znak": sign_name, "url": item["url"], **item["mjesecni"]}

                dnevni_formatted[slug] = _format_daily(sign_name, dnevni_raw[slug])
                tjedni_formatted[slug] = _format_weekly(sign_name, tjedni_raw[slug])
                mjesecni_formatted[slug] = _format_monthly(sign_name, mjesecni_raw[slug])

            data = {
                "generated_at": dt_util.now().isoformat(),
                ATTR_ATTRIBUTION: "Data by ehoroskop.net",
                ATTR_SOURCE_URLS: source_urls,
                "dnevni_raw": dnevni_raw,
                "tjedni_raw": tjedni_raw,
                "mjesecni_raw": mjesecni_raw,
                "dnevni_formatted": dnevni_formatted,
                "tjedni_formatted": tjedni_formatted,
                "mjesecni_formatted": mjesecni_formatted,
                "dnevni_translated": None,
                "tjedni_translated": None,
                "mjesecni_translated": None,
            }

            if self.entry.options.get("translation_enabled", DEFAULT_TRANSLATION_ENABLED) and self.translation_coordinator:
                self.hass.async_create_task(self.translation_coordinator.async_translate(data))

            return data
        except Exception as err:
            raise UpdateFailed(f"Failed to fetch horoskop data: {err}") from err


class HoroskopTranslationCoordinator(DataUpdateCoordinator):
    """Translation state and execution coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, data_coordinator: HoroskopDataCoordinator) -> None:
        self.entry = entry
        self.data_coordinator = data_coordinator
        self._state = {
            "status": "idle",
            "last_attempt": None,
            "last_success": None,
            "error_message": None,
            "language": None,
        }
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}_translation", update_interval=None)

    async def async_initialize(self) -> None:
        self.async_set_updated_data(dict(self._state))

    async def _async_update_data(self) -> dict[str, Any]:
        return dict(self._state)

    async def async_translate(self, source_data: dict[str, Any] | None = None) -> None:
        language = str(self.entry.options.get("translation_language", DEFAULT_TRANSLATION_LANGUAGE))
        ai_task_entity = self.entry.options.get("translation_ai_task_entity")

        self._state.update(
            {
                "status": "translating",
                "last_attempt": dt_util.now().isoformat(),
                "error_message": None,
                "language": language,
            }
        )
        self.async_set_updated_data(dict(self._state))

        try:
            source = source_data or dict(self.data_coordinator.data or {})
            if not source:
                raise RuntimeError("No source data available for translation.")

            translated = await self._translate_payload(source, language, ai_task_entity)
            merged = dict(source)
            merged["dnevni_translated"] = translated.get("dnevni", {})
            merged["tjedni_translated"] = translated.get("tjedni", {})
            merged["mjesecni_translated"] = translated.get("mjesecni", {})

            self.data_coordinator.async_set_updated_data(merged)
            self._state.update(
                {
                    "status": "done",
                    "last_success": dt_util.now().isoformat(),
                    "error_message": None,
                }
            )
        except Exception as err:
            _LOGGER.error("Horoskop translation failed: %s", err)
            self._state.update({"status": "error", "error_message": str(err)})
        finally:
            self.async_set_updated_data(dict(self._state))

    async def _translate_payload(self, source: dict[str, Any], language: str, ai_task_entity: str | None) -> dict[str, Any]:
        has_generate_data = self.hass.services.has_service("ai_task", "generate_data")
        has_generate_text = self.hass.services.has_service("ai_task", "generate_text")
        if not has_generate_data and not has_generate_text:
            raise RuntimeError("No ai_task service available.")

        ai_service = "generate_data" if has_generate_data else "generate_text"
        compact_source = {
            "dnevni": source.get("dnevni_formatted", {}),
            "tjedni": source.get("tjedni_formatted", {}),
            "mjesecni": source.get("mjesecni_formatted", {}),
        }

        prompt = (
            f"Translate the following horoscope texts to language code '{language}'.\n"
            "Return strictly valid JSON only. Keep original keys and structure exactly:\n"
            "{'dnevni': {'slug': 'text'}, 'tjedni': {'slug': 'text'}, 'mjesecni': {'slug': 'text'}}.\n"
            "Do not add markdown, comments, or extra keys.\n\n"
            f"INPUT_JSON:\n{json.dumps(compact_source, ensure_ascii=False)}"
        )

        service_data: dict[str, Any] = {"task_name": f"{DOMAIN}_translate", "instructions": prompt}
        if ai_task_entity:
            service_data["entity_id"] = ai_task_entity

        resp = await self.hass.services.async_call(
            "ai_task",
            ai_service,
            service_data,
            blocking=True,
            return_response=True,
        )
        raw = self._extract_text(resp)
        if not raw:
            raise RuntimeError(f"Empty translation response: {resp!r}")
        parsed = self._parse_json(raw)

        return {
            "dnevni": parsed.get("dnevni", {}),
            "tjedni": parsed.get("tjedni", {}),
            "mjesecni": parsed.get("mjesecni", {}),
        }

    @staticmethod
    def _extract_text(resp: Any) -> str:
        if isinstance(resp, str):
            return resp.strip()
        if isinstance(resp, dict):
            for key in ("text", "response", "result", "content", "output", "generated_text", "answer"):
                value = resp.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            data = resp.get("data")
            if isinstance(data, str) and data.strip():
                return data.strip()
            if isinstance(data, dict):
                for key in ("text", "response", "result", "content"):
                    value = data.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        return ""

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        stripped = text.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise RuntimeError("Translation output is not JSON.")
            return json.loads(stripped[start : end + 1])
