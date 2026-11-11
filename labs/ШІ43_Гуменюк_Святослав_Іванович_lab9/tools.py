import hashlib
import logging
import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timezone
from functools import cache
from typing import Callable
from zoneinfo import ZoneInfo

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
UPCOMING_HOLIDAYS_COUNT = 3

SYNODIC_MONTH_DAYS = 29.530588853
KNOWN_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)

MOON_PHASES = [
    "новий місяць",
    "молодий місяць",
    "перша чверть",
    "зростаючий місяць",
    "повня",
    "спадаючий місяць",
    "остання чверть",
    "старий місяць",
]

ZODIAC_SIGNS = [
    "Овен", "Телець", "Близнюки", "Рак", "Лев", "Діва",
    "Терези", "Скорпіон", "Стрілець", "Козеріг", "Водолій", "Риби",
]

HOROSCOPE_OPENINGS = [
    "Зірки сьогодні на вашому боці",
    "Меркурій дивиться на вас з підозрою",
    "Венера натякає на несподівані можливості",
    "Марс радить не поспішати",
    "Сатурн мовчить, і це тривожно",
    "Юпітер щедрий на обіцянки",
]
HOROSCOPE_ADVICE = [
    "тож довіряйте інтуїції, але перевіряйте факти",
    "тож краще відкласти важливі розмови на вечір",
    "тож сміливо рухайтеся вперед",
    "тож уникайте поспішних покупок",
    "тож зробіть паузу і випийте чаю",
    "тож час діяти рішуче",
]

WEEKDAYS = ["понеділок", "вівторок", "середа", "четвер", "пʼятниця", "субота", "неділя"]

WEATHER_CODES = {
    0: "ясно",
    1: "переважно ясно",
    2: "мінлива хмарність",
    3: "похмуро",
    45: "туман",
    48: "паморозь",
    51: "легка мряка",
    53: "мряка",
    55: "сильна мряка",
    56: "легка паморозна мряка",
    57: "сильна паморозна мряка",
    61: "легкий дощ",
    63: "дощ",
    65: "сильний дощ",
    66: "легкий крижаний дощ",
    67: "сильний крижаний дощ",
    71: "легкий сніг",
    73: "сніг",
    75: "сильний сніг",
    77: "снігова крупа",
    80: "легка злива",
    81: "злива",
    82: "сильна злива",
    85: "легкий снігопад",
    86: "сильний снігопад",
    95: "гроза",
    96: "гроза з градом",
    99: "гроза з сильним градом",
}


def get_json(url: str, params: dict | None = None):
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    return response.json()


@cache
def find_city(city: str) -> dict | None:
    results = get_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {"name": city, "count": 1, "language": "uk"},
    ).get("results")

    return results[0] if results else None


def part_of_day(hour: int) -> str:
    if hour < 6:
        return "ніч"

    if hour < 12:
        return "ранок"

    if hour < 18:
        return "день"

    return "вечір"


def get_weather(city: str) -> dict:
    place = find_city(city)

    if not place:
        return {"error": f"місто '{city}' не знайдено"}

    current = get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,wind_speed_10m,precipitation,weather_code",
        },
    )["current"]

    return {
        "city": place["name"],
        "temperature_c": current["temperature_2m"],
        "wind_speed_kmh": current["wind_speed_10m"],
        "precipitation_mm": current["precipitation"],
        "conditions": WEATHER_CODES[current["weather_code"]],
    }


def get_crypto_price(coin_id: str) -> dict:
    coin_id = coin_id.lower()
    prices = get_json(
        "https://api.coingecko.com/api/v3/simple/price",
        {"ids": coin_id, "vs_currencies": "usd,uah", "include_24hr_change": "true"},
    )

    if coin_id not in prices:
        return {"error": f"криптовалюту '{coin_id}' не знайдено"}

    quote = prices[coin_id]

    return {
        "coin": coin_id,
        "price_usd": quote["usd"],
        "price_uah": quote["uah"],
        "change_24h_percent": round(quote["usd_24h_change"], 2),
    }


def get_uah_rate(currency: str) -> dict:
    rates = get_json(
        "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange",
        {"valcode": currency.upper(), "json": ""},
    )

    if not rates:
        return {"error": f"валюту '{currency}' не знайдено"}

    rate = rates[0]

    return {"currency": rate["cc"], "uah_per_unit": rate["rate"], "date": rate["exchangedate"]}


def get_fear_greed_index() -> dict:
    index = get_json("https://api.alternative.me/fng/")["data"][0]

    return {"value": int(index["value"]), "classification": index["value_classification"]}


def get_space_weather() -> dict:
    latest_reading = get_json("https://services.swpc.noaa.gov/json/planetary_k_index_1m.json")[-1]

    return {"kp_index": latest_reading["kp_index"], "time_utc": latest_reading["time_tag"]}


def get_iss_position() -> dict:
    position = get_json("https://api.wheretheiss.at/v1/satellites/25544")

    return {
        "latitude": round(position["latitude"], 2),
        "longitude": round(position["longitude"], 2),
        "altitude_km": round(position["altitude"]),
        "velocity_kmh": round(position["velocity"]),
    }


def get_earthquakes() -> dict:
    earthquakes = get_json(
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
    )["features"]

    if not earthquakes:
        return {"count_24h": 0}

    strongest = max(earthquakes, key=lambda earthquake: earthquake["properties"]["mag"] or 0)

    return {
        "count_24h": len(earthquakes),
        "strongest_magnitude": strongest["properties"]["mag"],
        "strongest_place": strongest["properties"]["place"],
    }


def get_holidays(country_code: str) -> dict:
    today = date.today()
    holidays = get_json(
        f"https://date.nager.at/api/v3/PublicHolidays/{today.year}/{country_code.upper()}"
    )
    upcoming = [holiday for holiday in holidays if holiday["date"] >= today.isoformat()]

    return {
        "is_holiday_today": any(holiday["date"] == today.isoformat() for holiday in holidays),
        "next_holidays": [
            {"date": holiday["date"], "name": holiday["name"]}
            for holiday in upcoming[:UPCOMING_HOLIDAYS_COUNT]
        ],
    }


def get_moon_phase() -> dict:
    days_since_new_moon = (datetime.now(timezone.utc) - KNOWN_NEW_MOON).total_seconds() / 86400
    cycle_position = (days_since_new_moon % SYNODIC_MONTH_DAYS) / SYNODIC_MONTH_DAYS
    illuminated_fraction = (1 - math.cos(2 * math.pi * cycle_position)) / 2
    phase_index = round(cycle_position * len(MOON_PHASES)) % len(MOON_PHASES)

    return {
        "phase": MOON_PHASES[phase_index],
        "illumination_percent": round(illuminated_fraction * 100),
    }


def get_horoscope(sign: str) -> dict:
    normalized_sign = sign.strip().capitalize()

    if normalized_sign not in ZODIAC_SIGNS:
        return {"error": f"невідомий знак '{sign}'", "valid_signs": ZODIAC_SIGNS}

    seed = hashlib.sha256(f"{normalized_sign}{date.today()}".encode()).digest()
    generator = random.Random(seed)

    return {
        "sign": normalized_sign,
        "prediction": f"{generator.choice(HOROSCOPE_OPENINGS)}, {generator.choice(HOROSCOPE_ADVICE)}.",
        "lucky_number": generator.randint(1, 99),
    }


def get_current_datetime(city: str) -> dict:
    place = find_city(city)

    if not place:
        return {"error": f"місто '{city}' не знайдено"}

    now = datetime.now(ZoneInfo(place["timezone"]))

    return {
        "city": place["name"],
        "timezone": place["timezone"],
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M"),
        "weekday": WEEKDAYS[now.weekday()],
        "part_of_day": part_of_day(now.hour),
    }


@dataclass(frozen=True)
class Tool:
    function: Callable[..., dict]
    description: str
    parameters: dict[str, str]

    @property
    def name(self) -> str:
        return self.function.__name__

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        name: {"type": "string", "description": description}
                        for name, description in self.parameters.items()
                    },
                    "required": list(self.parameters),
                },
            },
        }


TOOLS = {
    tool.name: tool
    for tool in [
        Tool(get_weather, "Поточна погода в місті (температура, вітер, опади).",
             {"city": "Назва міста"}),
        Tool(get_crypto_price, "Курс криптовалюти в USD та UAH і зміна за 24 години.",
             {"coin_id": "Ідентифікатор CoinGecko, наприклад bitcoin або ethereum"}),
        Tool(get_uah_rate, "Офіційний курс гривні до валюти за даними НБУ.",
             {"currency": "Код валюти ISO, наприклад USD, EUR"}),
        Tool(get_fear_greed_index, "Індекс страху й жадібності крипторинку (0 — страх, 100 — жадібність).", {}),
        Tool(get_space_weather, "Поточний Kp-індекс геомагнітної активності (магнітні бурі).", {}),
        Tool(get_iss_position, "Поточне положення Міжнародної космічної станції.", {}),
        Tool(get_earthquakes, "Кількість і найсильніший землетрус у світі за останню добу.", {}),
        Tool(get_holidays, "Чи сьогодні державне свято та найближчі свята країни.",
             {"country_code": "Двобуквений код країни ISO, наприклад UA"}),
        Tool(get_moon_phase, "Поточна фаза місяця та освітленість.", {}),
        Tool(get_horoscope, "Жартівливе передбачення для знака зодіаку на сьогодні.",
             {"sign": "Знак зодіаку українською, наприклад Овен"}),
        Tool(get_current_datetime, "Поточні дата, день тижня та час доби в місті (за його часовим поясом).",
             {"city": "Назва міста"}),
    ]
}

TOOL_SCHEMAS = [tool.schema() for tool in TOOLS.values()]


def run_tool(name: str, arguments: dict) -> dict:
    try:
        tool = TOOLS[name]
        known_arguments = {key: value for key, value in arguments.items() if key in tool.parameters}

        return tool.function(**known_arguments)
    except Exception as error:
        logger.exception("Tool %s failed", name)

        return {"error": f"{type(error).__name__}: {error}"}
