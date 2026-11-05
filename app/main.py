from __future__ import annotations

import json
import math
import os
from datetime import date
from pathlib import Path
from typing import Annotated, Any

from agent_framework import workflow
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "data" / "catalog.json"
EARTH_RADIUS_METERS = 6_371_000
MIN_AWARD_REVIEWERS = 3

app = FastAPI(title="청도 한입", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")


class TasteReview(BaseModel):
    menu_id: str = Field(min_length=1, max_length=80)
    score: float = Field(ge=0, le=5)
    tags: list[Annotated[str, Field(min_length=1, max_length=32)]] = Field(
        default_factory=list, max_length=8
    )


class TasteRequest(BaseModel):
    reviews: list[TasteReview] = Field(min_length=1, max_length=100)


def load_catalog() -> dict[str, Any]:
    with DATA_FILE.open(encoding="utf-8") as catalog_file:
        return json.load(catalog_file)


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(min(1, haversine)))


def monthly_awards(
    catalog: dict[str, Any], month: str, minimum_reviewers: int = MIN_AWARD_REVIEWERS
) -> list[dict[str, Any]]:
    try:
        year, month_number = (int(part) for part in month.split("-", maxsplit=1))
        date(year, month_number, 1)
    except (ValueError, TypeError):
        raise ValueError("month must be YYYY-MM") from None

    menus = {menu["id"]: menu for menu in catalog.get("menus", [])}
    restaurants = {restaurant["id"]: restaurant for restaurant in catalog.get("restaurants", [])}
    groups: dict[tuple[str, str], dict[str, list[float]]] = {}
    for review in catalog.get("reviews", []):
        if review.get("status", "public") != "public":
            continue
        created_at = str(review.get("created_at", ""))
        if created_at[:7] != month:
            continue
        reviewer = review.get("reviewer_id")
        menu = menus.get(review.get("menu_id"))
        restaurant = restaurants.get(review.get("restaurant_id"))
        if not reviewer or not menu or not restaurant or menu.get("restaurant_id") != restaurant["id"]:
            continue
        score = review.get("score")
        if not isinstance(score, (int, float)) or not 0 <= score <= 5:
            continue
        for kind, target_id in (("restaurant", restaurant["id"]), ("menu", menu["id"])):
            groups.setdefault((kind, target_id), {}).setdefault(str(reviewer), []).append(float(score))

    awards: list[dict[str, Any]] = []
    for (kind, target_id), by_reviewer in groups.items():
        if len(by_reviewer) < minimum_reviewers:
            continue
        per_reviewer = [sum(scores) / len(scores) for scores in by_reviewer.values()]
        target = restaurants[target_id] if kind == "restaurant" else menus[target_id]
        awards.append(
            {
                "kind": kind,
                "id": target_id,
                "name": target["name"],
                "month": month,
                "rating": round(sum(per_reviewer) / len(per_reviewer), 2),
                "unique_reviewers": len(by_reviewer),
            }
        )
    return sorted(
        awards,
        key=lambda award: (
            award["kind"],
            -award["rating"],
            -award["unique_reviewers"],
            award["id"],
        ),
    )


def add_rating_summaries(catalog: dict[str, Any]) -> dict[str, Any]:
    menus = {menu["id"]: dict(menu) for menu in catalog.get("menus", [])}
    restaurants = {
        restaurant["id"]: dict(restaurant)
        for restaurant in catalog.get("restaurants", [])
    }
    grouped: dict[tuple[str, str], dict[str, list[float]]] = {}
    counts: dict[tuple[str, str], int] = {}
    for review in catalog.get("reviews", []):
        if review.get("status", "public") != "public":
            continue
        reviewer = review.get("reviewer_id")
        menu = menus.get(review.get("menu_id"))
        restaurant = restaurants.get(review.get("restaurant_id"))
        score = review.get("score")
        if (
            not reviewer
            or not menu
            or not restaurant
            or menu.get("restaurant_id") != restaurant["id"]
            or not isinstance(score, (int, float))
            or not 0 <= score <= 5
        ):
            continue
        for kind, target_id in (("menu", menu["id"]), ("restaurant", restaurant["id"])):
            grouped.setdefault((kind, target_id), {}).setdefault(str(reviewer), []).append(float(score))
            counts[(kind, target_id)] = counts.get((kind, target_id), 0) + 1

    for (kind, target_id), by_reviewer in grouped.items():
        target = menus[target_id] if kind == "menu" else restaurants[target_id]
        target["review_count"] = counts[(kind, target_id)]
        target["unique_reviewers"] = len(by_reviewer)
        target["rating"] = (
            round(
                sum(sum(scores) / len(scores) for scores in by_reviewer.values())
                / len(by_reviewer),
                2,
            )
            if len(by_reviewer) >= MIN_AWARD_REVIEWERS
            else None
        )
    for menu in menus.values():
        menu.setdefault("review_count", 0)
        menu.setdefault("unique_reviewers", 0)
        menu.setdefault("rating", None)
    for restaurant in restaurants.values():
        restaurant.setdefault("review_count", 0)
        restaurant.setdefault("unique_reviewers", 0)
        restaurant.setdefault("rating", None)
    return {
        **catalog,
        "restaurants": list(restaurants.values()),
        "menus": list(menus.values()),
    }


def filtered_catalog(
    catalog: dict[str, Any],
    query: str | None,
    area: str | None,
    latitude: float | None,
    longitude: float | None,
) -> dict[str, Any]:
    catalog = add_rating_summaries(catalog)
    menus_by_restaurant: dict[str, list[dict[str, Any]]] = {}
    for menu in catalog.get("menus", []):
        menus_by_restaurant.setdefault(menu["restaurant_id"], []).append(menu)

    normalized_query = (query or "").strip().casefold()
    rows = []
    for restaurant in catalog.get("restaurants", []):
        if restaurant.get("status", "active") == "inactive":
            continue
        if area and restaurant.get("area") != area:
            continue
        menus = menus_by_restaurant.get(restaurant["id"], [])
        if normalized_query and normalized_query not in " ".join(
            [restaurant.get("name", ""), *(menu.get("name", "") for menu in menus)]
        ).casefold():
            continue

        row = dict(restaurant)
        if latitude is not None and longitude is not None:
            restaurant_lat = restaurant.get("latitude")
            restaurant_lon = restaurant.get("longitude")
            if not isinstance(restaurant_lat, (int, float)) or not isinstance(restaurant_lon, (int, float)):
                continue
            row["distance_meters"] = round(
                distance_meters(latitude, longitude, restaurant_lat, restaurant_lon)
            )
        row["menus"] = menus
        rows.append(row)

    if latitude is not None and longitude is not None:
        rows.sort(key=lambda restaurant: (restaurant["distance_meters"], restaurant["id"]))
    else:
        rows.sort(key=lambda restaurant: restaurant["name"])
    return {
        "restaurants": rows,
        "menus": catalog.get("menus", []),
        "awards": monthly_awards(catalog, date.today().strftime("%Y-%m")),
        "data_notice": catalog.get("data_notice", ""),
    }


@workflow(name="taste-profile", description="Summarize food preferences from evidence-backed ratings")
async def taste_profile_workflow(payload: dict[str, Any]) -> str:
    catalog = load_catalog()
    menus = {menu["id"]: menu for menu in catalog.get("menus", [])}
    evidence = []
    for review in payload["reviews"]:
        menu = menus.get(review.menu_id)
        if menu:
            evidence.append(
                {
                    "menu": menu["name"],
                    "restaurant": menu.get("restaurant_name", ""),
                    "score": review.score,
                    "tags": review.tags,
                }
            )
    if not evidence:
        raise ValueError("평가 기록과 연결되는 메뉴를 찾지 못했어요.")

    endpoint = os.getenv("COPILOT_AZURE_ENDPOINT")
    api_key = os.getenv("COPILOT_AZURE_API_KEY")
    model = os.getenv("COPILOT_MODEL")
    if not endpoint or not api_key or not model:
        raise RuntimeError("AI 연결 설정이 없어요.")

    prompt = (
        "사용자의 실제 메뉴 평가에 근거해 한국어로 취향을 2~3문장으로 요약하세요. "
        "관찰된 경향과 추측을 구분하고, 기록이 부족하면 그 한계를 밝히세요. "
        "새 식당, 메뉴, 맛 속성을 만들어내지 말고 점수나 순위를 산정하지 마세요. "
        "아래 JSON에 있는 이름과 태그만 근거로 사용하세요.\n"
        + json.dumps(evidence, ensure_ascii=False)
    )

    try:
        from copilot import CopilotClient
        from copilot.session_events import AssistantMessageData

        async with CopilotClient() as client:
            async with await client.create_session(
                model=model,
                provider={
                    "type": "azure",
                    "base_url": endpoint,
                    "api_key": api_key,
                },
                available_tools=[],
            ) as session:
                reply = await session.send_and_wait(prompt)
        if reply and isinstance(reply.data, AssistantMessageData):
            summary = reply.data.content.strip()
            if summary:
                return summary[:1200]
        raise RuntimeError("AI가 취향 요약을 반환하지 않았어요.")
    except RuntimeError:
        raise
    except Exception as error:
        raise RuntimeError("AI 취향 요약에 실패했어요.") from error


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(APP_DIR / "index.html")


@app.get("/api/catalog")
async def get_catalog(
    q: str | None = Query(default=None, max_length=80),
    area: str | None = Query(default=None, max_length=30),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
) -> dict[str, Any]:
    if (lat is None) != (lon is None):
        raise HTTPException(status_code=422, detail="위치 좌표를 함께 전달해 주세요.")
    try:
        catalog = load_catalog()
        return filtered_catalog(catalog, q, area, lat, lon)
    except ValueError as error:
        raise HTTPException(status_code=500, detail="카탈로그 설정을 확인해 주세요.") from error


@app.post("/api/taste-guide")
async def get_taste_guide(request: TasteRequest) -> dict[str, str]:
    catalog = load_catalog()
    known_menu_ids = {menu["id"] for menu in catalog.get("menus", [])}
    if any(review.menu_id not in known_menu_ids for review in request.reviews):
        raise HTTPException(status_code=422, detail="기록에 연결되지 않은 메뉴가 있어요.")
    try:
        result = await taste_profile_workflow.build().run(
            {"reviews": request.reviews}
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="AI 취향 분석을 완료하지 못했어요.") from error
    if not result.text:
        raise HTTPException(status_code=502, detail="AI 취향 분석 결과가 비어 있어요.")
    return {"summary": result.text}
