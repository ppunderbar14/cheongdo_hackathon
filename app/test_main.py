import unittest

from main import add_rating_summaries, distance_meters, filtered_catalog, monthly_awards


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
