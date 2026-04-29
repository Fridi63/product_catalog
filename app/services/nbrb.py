from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import httpx


class NbrbError(Exception):
    pass

USD_NUMERIC_CODE = 840
NBRB_RATES = "https://api.nbrb.by/exrates/rates/{code}"

@dataclass
class NbrbRate:
    cur_id: int
    cur_scale: int
    cur_official_rate: Decimal
    cur_abbreviation: str
    rate_date: str

def _parse_rate(data: object) -> NbrbRate:
    if not isinstance(data, dict):
        raise NbrbError("Некорректный ответ API")
    try:
        return NbrbRate(
            cur_id=int(data["Cur_ID"]),
            cur_scale=int(data["Cur_Scale"]),
            cur_official_rate=Decimal(str(data["Cur_OfficialRate"])),
            cur_abbreviation=str(data.get("Cur_Abbreviation", "")),
            rate_date=str(data.get("Date", "")),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise NbrbError("Не удалось разобрать курс") from e

async def _fetch_one(client: httpx.AsyncClient, code: int, on_date: date) -> NbrbRate:
    url = f"{NBRB_RATES.format(code=code)}?parammode=1&ondate={on_date.isoformat()}"
    try:
        r = await client.get(url, timeout=20.0)
    except httpx.RequestError as e:
        raise NbrbError("Сеть: не удалось обратиться к API") from e
    if r.status_code != 200:
        raise NbrbError(f"API: HTTP {r.status_code}")
    data = r.json()
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        raise NbrbError("Пустой ответ курса")
    return _parse_rate(data)

async def convert_byn_to_usd(amount_byn: Decimal, on_date: date) -> dict:

    if amount_byn < 0:
        raise ValueError("amount")
    async with httpx.AsyncClient() as client:
        usd = await _fetch_one(client, USD_NUMERIC_CODE, on_date)
    if usd.cur_scale <= 0:
        raise NbrbError("Некорректный объём курса")
    byn_per_usd = usd.cur_official_rate / Decimal(usd.cur_scale)
    if byn_per_usd == 0:
        raise NbrbError("Курс USD к BYN 0")
    usd_amount = (amount_byn / byn_per_usd).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    return {
        "amount_byn": str(amount_byn),
        "amount_usd": str(usd_amount),
        "on_date": on_date.isoformat(),
        "scale_usd": usd.cur_scale,
        "rate_usd_byn": str(usd.cur_official_rate),
        "nbrb_usd_abbrev": usd.cur_abbreviation,
        "nbrb_byn_abbrev": "BYN",
    }
