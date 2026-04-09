"""Focused variety tests for the DietAdvisor meal-plan generator.

Validates that multi-day meal plans exhibit sufficient food diversity,
avoid excessive repetition, and include regionally appropriate items.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from teloscopy.nutrition.diet_advisor import DietAdvisor

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def advisor():
    return DietAdvisor()


@pytest.fixture(scope="module")
def recs_north_india(advisor):
    return advisor.generate_recommendations(
        genetic_risks=["Type 2 diabetes"],
        variants={"rs1801133": "CT"},
        region="south_asia_north",
        age=30,
        sex="male",
    )


@pytest.fixture(scope="module")
def thirty_day_north_india(advisor, recs_north_india):
    return advisor.create_meal_plan(
        recs_north_india, region="south_asia_north", calories=2000, days=30
    )


@pytest.fixture(scope="module")
def recs_south_india(advisor):
    return advisor.generate_recommendations(
        genetic_risks=["Type 2 diabetes"],
        variants={"rs1801133": "CT"},
        region="south_asia_south",
        age=30,
        sex="male",
    )


@pytest.fixture(scope="module")
def thirty_day_south_india(advisor, recs_south_india):
    return advisor.create_meal_plan(
        recs_south_india, region="south_asia_south", calories=2000, days=30
    )


# ---------------------------------------------------------------------------
# Unique food count tests
# ---------------------------------------------------------------------------


class TestUniqueFoodCounts:
    """A 30-day plan should draw from a wide variety of foods."""

    def test_unique_breakfast_count(self, thirty_day_north_india):
        names = set()
        for plan in thirty_day_north_india:
            for food, _ in plan.breakfast:
                names.add(food.name)
        assert len(names) > 15, f"Only {len(names)} unique breakfast items"

    def test_unique_lunch_count(self, thirty_day_north_india):
        names = set()
        for plan in thirty_day_north_india:
            for food, _ in plan.lunch:
                names.add(food.name)
        assert len(names) > 10, f"Only {len(names)} unique lunch items"

    def test_unique_dinner_count(self, thirty_day_north_india):
        names = set()
        for plan in thirty_day_north_india:
            for food, _ in plan.dinner:
                names.add(food.name)
        assert len(names) > 15, f"Only {len(names)} unique dinner items"

    def test_unique_snack_count(self, thirty_day_north_india):
        names = set()
        for plan in thirty_day_north_india:
            for food, _ in plan.snacks:
                names.add(food.name)
        assert len(names) > 5, f"Only {len(names)} unique snack items"

    def test_total_unique_foods(self, thirty_day_north_india):
        """Across all meals, there should be broad variety."""
        names = set()
        for plan in thirty_day_north_india:
            for meal in (plan.breakfast, plan.lunch, plan.dinner, plan.snacks):
                for food, _ in meal:
                    names.add(food.name)
        assert len(names) > 30, f"Only {len(names)} unique foods across 30-day plan"


# ---------------------------------------------------------------------------
# Consecutive day repetition tests
# ---------------------------------------------------------------------------


class TestConsecutiveDayDifferences:
    """Adjacent days should not repeat the same main items too often."""

    def _get_main_item_per_day(self, plans, meal_attr):
        """Extract the first food name from a meal for each day."""
        items = []
        for plan in plans:
            meal = getattr(plan, meal_attr)
            if meal:
                items.append(meal[0][0].name)
            else:
                items.append(None)
        return items

    def _max_consecutive_same(self, items):
        """Return the maximum streak of identical consecutive items."""
        if not items:
            return 0
        max_streak = 1
        streak = 1
        for i in range(1, len(items)):
            if items[i] == items[i - 1] and items[i] is not None:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 1
        return max_streak

    def test_dinner_no_long_repeats(self, thirty_day_north_india):
        mains = self._get_main_item_per_day(thirty_day_north_india, "dinner")
        assert self._max_consecutive_same(mains) <= 2, (
            "Dinner main dish repeated >2 consecutive days"
        )

    def test_breakfast_no_long_repeats(self, thirty_day_north_india):
        mains = self._get_main_item_per_day(thirty_day_north_india, "breakfast")
        assert self._max_consecutive_same(mains) <= 2, (
            "Breakfast main item repeated >2 consecutive days"
        )

    def test_lunch_no_long_repeats(self, thirty_day_north_india):
        mains = self._get_main_item_per_day(thirty_day_north_india, "lunch")
        assert self._max_consecutive_same(mains) <= 2, (
            "Lunch main item repeated >2 consecutive days"
        )

    def test_adjacent_days_differ_in_at_least_one_meal(self, thirty_day_north_india):
        """Each pair of adjacent days should differ in at least one meal."""
        for i in range(len(thirty_day_north_india) - 1):
            day_a = thirty_day_north_india[i]
            day_b = thirty_day_north_india[i + 1]
            a_foods = {
                f.name for meal in (day_a.breakfast, day_a.lunch, day_a.dinner) for f, _ in meal
            }
            b_foods = {
                f.name for meal in (day_b.breakfast, day_b.lunch, day_b.dinner) for f, _ in meal
            }
            # They should not be identical
            assert a_foods != b_foods, f"Days {day_a.day} and {day_b.day} are identical"


# ---------------------------------------------------------------------------
# Regional food appropriateness
# ---------------------------------------------------------------------------


class TestRegionalFoodAppropriateness:
    """Foods in region-specific plans should reflect that cuisine."""

    def _all_food_names(self, plans):
        names = set()
        for plan in plans:
            for meal in (plan.breakfast, plan.lunch, plan.dinner, plan.snacks):
                for food, _ in meal:
                    names.add(food.name.lower())
        return names

    def test_south_india_has_indian_foods(self, thirty_day_south_india):
        """South Indian plan should contain recognisable South Indian foods."""
        names = self._all_food_names(thirty_day_south_india)
        # At least some of these should appear
        south_indian_markers = {
            "idli",
            "dosa",
            "sambar",
            "coconut chutney",
            "rasam",
            "rice",
            "ragi",
            "brown rice",
            "white rice",
            "tamarind",
            "coconut",
            "banana",
            "drumstick",
            "curry leaves",
            "urad dal",
        }
        found = names & south_indian_markers
        assert len(found) >= 1, (
            f"South India plan lacks regional foods. Found: {names & south_indian_markers}"
        )

    def test_north_india_has_indian_foods(self, thirty_day_north_india):
        names = self._all_food_names(thirty_day_north_india)
        north_indian_markers = {
            "roti",
            "whole wheat roti",
            "dal",
            "paneer",
            "ghee",
            "basmati rice",
            "brown rice",
            "white rice",
            "chickpeas",
            "spinach",
            "potato",
            "lentils",
            "moong dal",
            "rajma",
            "turmeric",
        }
        found = names & north_indian_markers
        assert len(found) >= 1, (
            f"North India plan lacks regional foods. Names: {sorted(names)[:20]}"
        )

    def test_mediterranean_has_relevant_foods(self, advisor):
        recs = advisor.generate_recommendations(
            genetic_risks=["Coronary artery disease"],
            variants={"rs1801133": "CT"},
            region="mediterranean",
            age=40,
            sex="male",
        )
        plans = advisor.create_meal_plan(recs, region="mediterranean", calories=2000, days=30)
        names = self._all_food_names(plans)
        med_markers = {
            "olive oil",
            "feta",
            "pasta",
            "tomato",
            "lentils",
            "chickpeas",
            "sardine",
            "salmon",
            "brown rice",
            "greek yoghurt",
            "hummus",
            "tabbouleh",
            "grilled fish",
        }
        found = names & med_markers
        assert len(found) >= 1, (
            f"Mediterranean plan lacks regional foods. Names: {sorted(names)[:20]}"
        )

    def test_east_asian_has_relevant_foods(self, advisor):
        recs = advisor.generate_recommendations(
            genetic_risks=[],
            variants={"rs1801133": "CT"},
            region="east_asia",
            age=35,
            sex="female",
        )
        plans = advisor.create_meal_plan(recs, region="east_asia", calories=2000, days=30)
        names = self._all_food_names(plans)
        ea_markers = {
            "tofu",
            "rice",
            "brown rice",
            "white rice",
            "soy sauce",
            "miso",
            "edamame",
            "bok choy",
            "noodles",
            "tempeh",
            "seaweed",
            "shiitake",
            "green tea",
        }
        found = names & ea_markers
        assert len(found) >= 1, f"East Asian plan lacks regional foods. Names: {sorted(names)[:20]}"

    def test_different_regions_produce_different_plans(self, advisor):
        """Plans for two very different regions should not be identical."""
        recs_a = advisor.generate_recommendations(
            genetic_risks=["Type 2 diabetes"],
            variants={"rs1801133": "CT"},
            region="south_asia_south",
            age=30,
            sex="male",
        )
        recs_b = advisor.generate_recommendations(
            genetic_risks=["Type 2 diabetes"],
            variants={"rs1801133": "CT"},
            region="northern_europe",
            age=30,
            sex="male",
        )
        plans_a = advisor.create_meal_plan(recs_a, region="south_asia_south", calories=2000, days=7)
        plans_b = advisor.create_meal_plan(recs_b, region="northern_europe", calories=2000, days=7)

        names_a = set()
        names_b = set()
        for plan in plans_a:
            for meal in (plan.breakfast, plan.lunch, plan.dinner, plan.snacks):
                for food, _ in meal:
                    names_a.add(food.name)
        for plan in plans_b:
            for meal in (plan.breakfast, plan.lunch, plan.dinner, plan.snacks):
                for food, _ in meal:
                    names_b.add(food.name)

        # They should differ meaningfully (at least some items unique to each)
        only_a = names_a - names_b
        only_b = names_b - names_a
        assert len(only_a) > 0 or len(only_b) > 0, (
            "South India and Northern Europe plans contain identical food sets"
        )
