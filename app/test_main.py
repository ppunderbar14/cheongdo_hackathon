import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import (
    add_rating_summaries,
    app,
    distance_meters,
    filtered_catalog,
    load_catalog,
    monthly_awards,
    openai_provider_config,
)
from copilot import ModelCapabilitiesOverride, ModelSupportsOverride


class ShippedCatalogTests(unittest.TestCase):
    def test_published_restaurants_and_menus_have_a_source_and_no_invented_ratings(self):
        catalog = load_catalog()
        restaurants = {restaurant["id"]: restaurant for restaurant in catalog["restaurants"]}

        self.assertEqual(len(restaurants), 3)
        self.assertEqual(len(catalog["menus"]), 9)
        self.assertTrue(all(restaurant["source_url"] for restaurant in restaurants.values()))
        self.assertTrue(
            all(menu["restaurant_id"] in restaurants for menu in catalog["menus"])
        )
        self.assertEqual(catalog["reviews"], [])
        self.assertTrue(all("rating" not in menu for menu in catalog["menus"]))

    def test_published_catalog_supports_area_and_menu_search(self):
        catalog = load_catalog()
        result = filtered_catalog(catalog, "매운수제비", "화양읍", None, None)

        self.assertEqual([row["name"] for row in result["restaurants"]], ["청도매운수제비집"])
        self.assertIn(
            "매운수제비",
            [menu["name"] for menu in result["restaurants"][0]["menus"]],
        )


class AIConfigurationTests(unittest.TestCase):
    def test_reasoning_effort_is_disabled_for_openai_models_that_reject_it(self):
        capabilities = ModelCapabilitiesOverride(
            supports=ModelSupportsOverride(reasoning_effort=False)
        )
        self.assertFalse(capabilities.supports.reasoning_effort)

    def test_openai_provider_uses_responses_api(self):
        self.assertEqual(
            openai_provider_config("test-key"),
            {
                "type": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-key",
                "wire_api": "responses",
            },
        )

    def test_missing_openai_key_fails_before_creating_a_copilot_session(self):
        catalog = load_catalog()
        menu_id = catalog["menus"][0]["id"]
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            response = TestClient(app).post(
                "/api/taste-guide",
                json={
                    "reviews": [
                        {"menu_id": menu_id, "score": 4.5, "tags": ["담백함"]}
                    ]
                },
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "AI 연결 설정이 없어요.")


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {
            "restaurants": [
                {
                    "id": "restaurant-1",
                    "name": "산책 식당",
                    "area": "청도읍",
                    "latitude": 35.65,
                    "longitude": 128.73,
                    "status": "active",
                },
                {
                    "id": "restaurant-2",
                    "name": "숨은 식당",
                    "area": "화양읍",
                    "latitude": 35.7,
                    "longitude": 128.8,
                    "status": "active",
                },
            ],
            "menus": [
                {"id": "menu-1", "restaurant_id": "restaurant-1", "name": "대표 메뉴"},
                {"id": "menu-2", "restaurant_id": "restaurant-2", "name": "들깨 메뉴"},
            ],
            "reviews": [
                {
                    "restaurant_id": "restaurant-1",
                    "menu_id": "menu-1",
                    "reviewer_id": f"user-{index}",
                    "score": score,
                    "status": "public",
                    "created_at": "2026-11-02T10:00:00Z",
                }
                for index, score in enumerate((5, 4, 4), start=1)
            ]
            + [
                {
                    "restaurant_id": "restaurant-2",
                    "menu_id": "menu-2",
                    "reviewer_id": f"user-{index}",
                    "score": 5,
                    "status": "private",
                    "created_at": "2026-11-02T10:00:00Z",
                }
                for index in range(4, 8)
            ],
        }

    def test_distance_is_zero_for_same_coordinates(self):
        self.assertAlmostEqual(distance_meters(35.65, 128.73, 35.65, 128.73), 0)

    def test_nearby_filter_uses_verified_coordinates_and_query(self):
        result = filtered_catalog(self.catalog, "대표", None, 35.65, 128.73)
        self.assertEqual([row["id"] for row in result["restaurants"]], ["restaurant-1"])
        self.assertEqual(result["restaurants"][0]["distance_meters"], 0)

    def test_private_reviews_do_not_create_public_awards(self):
        awards = monthly_awards(self.catalog, "2026-11")
        self.assertEqual([(award["kind"], award["id"]) for award in awards], [
            ("menu", "menu-1"),
            ("restaurant", "restaurant-1"),
        ])

    def test_rating_uses_one_average_per_reviewer_and_hides_small_samples(self):
        result = add_rating_summaries(self.catalog)
        menu = next(menu for menu in result["menus"] if menu["id"] == "menu-1")
        private_menu = next(menu for menu in result["menus"] if menu["id"] == "menu-2")
        self.assertEqual(menu["rating"], 4.33)
        self.assertEqual(menu["unique_reviewers"], 3)
        self.assertIsNone(private_menu["rating"])


if __name__ == "__main__":
    unittest.main()
