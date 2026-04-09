"""Comprehensive tests for the nutrigenomics dietary recommendation engine."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from teloscopy.nutrition.diet_advisor import (
    FOOD_DATABASE,
    GEOGRAPHIC_FOOD_DB,
    DietAdvisor,
    DietaryRecommendation,
    FoodItem,
    MealPlan,
    NutrientNeed,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def advisor():
    """Shared DietAdvisor instance (expensive init, reuse across tests)."""
    return DietAdvisor()


@pytest.fixture(scope="module")
def basic_recommendations(advisor):
    """Recommendations for a north-Indian male, age 30, T2D risk."""
    return advisor.generate_recommendations(
        genetic_risks=["Type 2 diabetes"],
        variants={"rs1801133": "CT"},
        region="south_asia_north",
        age=30,
        sex="male",
    )


@pytest.fixture(scope="module")
def seven_day_plan(advisor, basic_recommendations):
    """A 7-day meal plan for south_asia_north at 2000 kcal."""
    return advisor.create_meal_plan(
        basic_recommendations,
        region="south_asia_north",
        calories=2000,
        days=7,
    )


# ---------------------------------------------------------------------------
# Test DietAdvisor initialization
# ---------------------------------------------------------------------------


class TestDietAdvisorInit:
    def test_instantiation(self):
        advisor = DietAdvisor()
        assert advisor is not None

    def test_food_database_size(self):
        assert len(FOOD_DATABASE) >= 450, (
            f"FOOD_DATABASE has only {len(FOOD_DATABASE)} items, expected >= 450"
        )

    def test_geographic_profiles_count(self):
        assert len(GEOGRAPHIC_FOOD_DB) >= 20

    def test_region_index_built(self, advisor):
        # The advisor should have a populated internal region index.
        assert len(advisor._region_index) > 0

    def test_group_index_built(self, advisor):
        assert len(advisor._group_index) > 0

    def test_custom_food_db(self):
        custom_food = FoodItem(
            name="test_food",
            calories_per_100g=100,
            protein=10,
            carbs=20,
            fat=5,
            fiber=3,
            key_micronutrients={"iron": 2.0},
            food_group="grain",
            regions=["test_region"],
        )
        custom_advisor = DietAdvisor(food_db=[custom_food])
        assert len(custom_advisor._food_db) == 1


# ---------------------------------------------------------------------------
# Test generate_recommendations
# ---------------------------------------------------------------------------


class TestGenerateRecommendations:
    def test_basic_call_returns_list(self, advisor):
        recs = advisor.generate_recommendations(
            genetic_risks=[],
            variants={"rs1801133": "CT"},
            region="south_asia_north",
            age=30,
            sex="male",
        )
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_recommendation_type(self, basic_recommendations):
        for rec in basic_recommendations:
            assert isinstance(rec, DietaryRecommendation)

    def test_recommendation_has_required_fields(self, basic_recommendations):
        for rec in basic_recommendations:
            assert isinstance(rec.nutrient, str) and len(rec.nutrient) > 0
            assert isinstance(rec.recommendation, str) and len(rec.recommendation) > 0
            assert rec.priority in ("critical", "high", "moderate", "low")
            assert isinstance(rec.target_foods, list)
            assert isinstance(rec.avoid_foods, list)
            assert isinstance(rec.genetic_basis, str)
            assert isinstance(rec.daily_target, str)
            assert 0.0 <= rec.confidence <= 1.0

    def test_with_genetic_risks(self, advisor):
        recs = advisor.generate_recommendations(
            genetic_risks=["Type 2 diabetes", "Coronary artery disease"],
            variants={"rs1801133": "CT"},
            region="south_asia_north",
            age=45,
            sex="male",
        )
        nutrients = {r.nutrient for r in recs}
        # T2D should drive glycemic_control, CAD should drive omega_3
        assert "glycemic_control" in nutrients
        assert "omega_3" in nutrients

    def test_with_multiple_risks(self, advisor):
        recs = advisor.generate_recommendations(
            genetic_risks=[
                "Type 2 diabetes",
                "Coronary artery disease",
                "Osteoporosis",
            ],
            variants={"rs1801133": "CT"},
            region="south_asia_north",
            age=60,
            sex="female",
        )
        nutrients = {r.nutrient for r in recs}
        assert "calcium" in nutrients

    def test_sorted_by_priority(self, advisor):
        recs = advisor.generate_recommendations(
            genetic_risks=["Type 2 diabetes", "Coronary artery disease"],
            variants={"rs1801133": "CT"},
            region="south_asia_north",
            age=45,
            sex="male",
        )
        priority_order = {"critical": 4, "high": 3, "moderate": 2, "low": 1}
        for i in range(len(recs) - 1):
            assert priority_order.get(recs[i].priority, 0) >= priority_order.get(
                recs[i + 1].priority, 0
            )

    def test_vegetarian_restriction(self, advisor):
        recs = advisor.generate_recommendations(
            genetic_risks=["Coronary artery disease"],
            variants={"rs1801133": "CT"},
            region="south_asia_north",
            age=35,
            sex="female",
            dietary_restrictions=["vegetarian"],
        )
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_vegan_restriction(self, advisor):
        recs = advisor.generate_recommendations(
            genetic_risks=[],
            variants={"rs1801133": "CT"},
            region="mediterranean",
            age=25,
            sex="male",
            dietary_restrictions=["vegan"],
        )
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_gluten_free_restriction(self, advisor):
        recs = advisor.generate_recommendations(
            genetic_risks=[],
            variants={"rs1801133": "CT"},
            region="northern_europe",
            age=40,
            sex="female",
            dietary_restrictions=["gluten_free"],
        )
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_empty_dietary_restrictions(self, advisor):
        recs = advisor.generate_recommendations(
            genetic_risks=[],
            variants={"rs1801133": "CT"},
            region="south_asia_north",
            age=30,
            sex="male",
            dietary_restrictions=[],
        )
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_no_variants_but_risks(self, advisor):
        """With no matching variants, risk-driven recs should still appear."""
        recs = advisor.generate_recommendations(
            genetic_risks=["Coronary artery disease"],
            variants={},
            region="south_asia_north",
            age=50,
            sex="male",
        )
        assert len(recs) > 0
        nutrients = {r.nutrient for r in recs}
        assert "omega_3" in nutrients

    def test_different_regions_produce_results(self, advisor):
        for region in [
            "south_asia_north",
            "east_asia",
            "mediterranean",
            "north_america",
            "latin_america",
        ]:
            recs = advisor.generate_recommendations(
                genetic_risks=["Type 2 diabetes"],
                variants={"rs1801133": "CT"},
                region=region,
                age=30,
                sex="male",
            )
            assert len(recs) > 0, f"No recommendations for region {region}"


# ---------------------------------------------------------------------------
# Test create_meal_plan
# ---------------------------------------------------------------------------


class TestCreateMealPlan:
    def test_returns_list_of_meal_plans(self, seven_day_plan):
        assert isinstance(seven_day_plan, list)
        for plan in seven_day_plan:
            assert isinstance(plan, MealPlan)

    def test_three_day_plan(self, advisor, basic_recommendations):
        plans = advisor.create_meal_plan(basic_recommendations, region="south_asia_north", days=3)
        assert len(plans) == 3

    def test_seven_day_plan(self, seven_day_plan):
        assert len(seven_day_plan) == 7

    def test_fourteen_day_plan(self, advisor, basic_recommendations):
        plans = advisor.create_meal_plan(basic_recommendations, region="south_asia_north", days=14)
        assert len(plans) == 14

    def test_thirty_day_plan(self, advisor, basic_recommendations):
        plans = advisor.create_meal_plan(basic_recommendations, region="south_asia_north", days=30)
        assert len(plans) == 30

    def test_day_numbers_sequential(self, seven_day_plan):
        for i, plan in enumerate(seven_day_plan, start=1):
            assert plan.day == i

    def test_each_day_has_all_meals(self, seven_day_plan):
        for plan in seven_day_plan:
            assert isinstance(plan.breakfast, list) and len(plan.breakfast) > 0
            assert isinstance(plan.lunch, list) and len(plan.lunch) > 0
            assert isinstance(plan.dinner, list) and len(plan.dinner) > 0
            assert isinstance(plan.snacks, list) and len(plan.snacks) > 0

    def test_meal_items_are_food_tuples(self, seven_day_plan):
        for plan in seven_day_plan:
            for meal in (plan.breakfast, plan.lunch, plan.dinner, plan.snacks):
                for item in meal:
                    assert isinstance(item, tuple) and len(item) == 2
                    food, grams = item
                    assert isinstance(food, FoodItem)
                    assert isinstance(grams, (int, float)) and grams > 0

    def test_calorie_target_approximately_met(self, seven_day_plan):
        """Each day should be within ~30% of the 2000 kcal target."""
        for plan in seven_day_plan:
            assert plan.total_calories > 0
            # Allow a generous range: 1200–2800 for a 2000 target
            assert 1200 <= plan.total_calories <= 2800, (
                f"Day {plan.day}: {plan.total_calories} kcal outside acceptable range"
            )

    def test_total_macros_present(self, seven_day_plan):
        for plan in seven_day_plan:
            assert "protein" in plan.total_macros
            assert "carbs" in plan.total_macros
            assert "fat" in plan.total_macros
            assert "fiber" in plan.total_macros
            assert plan.total_macros["protein"] > 0
            assert plan.total_macros["carbs"] > 0
            assert plan.total_macros["fat"] > 0

    def test_low_calorie_plan(self, advisor, basic_recommendations):
        plans = advisor.create_meal_plan(
            basic_recommendations, region="south_asia_north", calories=1200, days=3
        )
        assert len(plans) == 3
        for plan in plans:
            assert plan.total_calories > 0
            # Should be lower than a 2000 kcal plan
            assert plan.total_calories < 2000

    def test_high_calorie_plan(self, advisor, basic_recommendations):
        plans = advisor.create_meal_plan(
            basic_recommendations, region="south_asia_north", calories=3500, days=3
        )
        assert len(plans) == 3
        for plan in plans:
            assert plan.total_calories > 0
            # Should generally be higher than 2000
            assert plan.total_calories > 2000

    def test_unknown_region_defaults_gracefully(self, advisor, basic_recommendations):
        """An unrecognised region should not crash; falls back to global DB."""
        plans = advisor.create_meal_plan(
            basic_recommendations, region="nonexistent_region", calories=2000, days=3
        )
        assert len(plans) == 3
        for plan in plans:
            assert plan.total_calories > 0
            assert len(plan.breakfast) > 0

    def test_meal_plan_summary_dataframe(self, seven_day_plan):
        """The MealPlan.summary() helper should return a valid DataFrame."""
        df = seven_day_plan[0].summary()
        assert len(df) > 0
        assert "meal" in df.columns
        assert "food" in df.columns
        assert "calories" in df.columns

    def test_different_regions_produce_plans(self, advisor):
        for region in [
            "south_asia_north",
            "east_asia",
            "mediterranean",
            "north_america",
            "latin_america",
            "middle_east",
        ]:
            recs = advisor.generate_recommendations(
                genetic_risks=["Type 2 diabetes"],
                variants={"rs1801133": "CT"},
                region=region,
                age=30,
                sex="male",
            )
            plans = advisor.create_meal_plan(recs, region=region, calories=2000, days=3)
            assert len(plans) == 3, f"Failed for region {region}"
            for plan in plans:
                assert plan.total_calories > 0


# ---------------------------------------------------------------------------
# Test variety in meal plans
# ---------------------------------------------------------------------------


class TestMealPlanVariety:
    @pytest.fixture(scope="class")
    def thirty_day_plan(self):
        advisor = DietAdvisor()
        recs = advisor.generate_recommendations(
            genetic_risks=["Type 2 diabetes"],
            variants={"rs1801133": "CT"},
            region="south_asia_north",
            age=30,
            sex="male",
        )
        return advisor.create_meal_plan(recs, region="south_asia_north", calories=2000, days=30)

    def test_unique_breakfast_items(self, thirty_day_plan):
        """A 30-day plan should have good breakfast variety (>15 unique)."""
        breakfast_names = set()
        for plan in thirty_day_plan:
            for food, _ in plan.breakfast:
                breakfast_names.add(food.name)
        assert len(breakfast_names) > 15, (
            f"Only {len(breakfast_names)} unique breakfast items in 30-day plan"
        )

    def test_unique_dinner_items(self, thirty_day_plan):
        """A 30-day plan should have good dinner variety (>15 unique)."""
        dinner_names = set()
        for plan in thirty_day_plan:
            for food, _ in plan.dinner:
                dinner_names.add(food.name)
        assert len(dinner_names) > 15, (
            f"Only {len(dinner_names)} unique dinner items in 30-day plan"
        )

    def test_no_excessive_consecutive_repeats(self, thirty_day_plan):
        """No more than 2 consecutive days with the same main dish at dinner."""
        main_dishes = []
        for plan in thirty_day_plan:
            if plan.dinner:
                # Use the first dinner item as the "main dish"
                main_dishes.append(plan.dinner[0][0].name)
            else:
                main_dishes.append(None)

        consecutive = 1
        for i in range(1, len(main_dishes)):
            if main_dishes[i] == main_dishes[i - 1] and main_dishes[i] is not None:
                consecutive += 1
                assert consecutive <= 2, (
                    f"Same main dish '{main_dishes[i]}' on {consecutive} "
                    f"consecutive days (days {i}, {i + 1})"
                )
            else:
                consecutive = 1

    def test_unique_lunch_items(self, thirty_day_plan):
        lunch_names = set()
        for plan in thirty_day_plan:
            for food, _ in plan.lunch:
                lunch_names.add(food.name)
        assert len(lunch_names) > 10


# ---------------------------------------------------------------------------
# Test edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_very_low_calories(self, advisor, basic_recommendations):
        plans = advisor.create_meal_plan(
            basic_recommendations, region="south_asia_north", calories=1200, days=7
        )
        assert len(plans) == 7
        for plan in plans:
            assert plan.total_calories > 0

    def test_very_high_calories(self, advisor, basic_recommendations):
        plans = advisor.create_meal_plan(
            basic_recommendations, region="south_asia_north", calories=3500, days=7
        )
        assert len(plans) == 7
        for plan in plans:
            assert plan.total_calories > 0

    def test_unknown_region_recommendations(self, advisor):
        """Unknown region should still produce valid recommendations."""
        recs = advisor.generate_recommendations(
            genetic_risks=["Type 2 diabetes"],
            variants={"rs1801133": "CT"},
            region="atlantis",
            age=30,
            sex="male",
        )
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_empty_genetic_risks(self, advisor):
        recs = advisor.generate_recommendations(
            genetic_risks=[],
            variants={"rs1801133": "CT"},
            region="south_asia_north",
            age=30,
            sex="male",
        )
        assert isinstance(recs, list)

    def test_empty_variants(self, advisor):
        recs = advisor.generate_recommendations(
            genetic_risks=["Type 2 diabetes"],
            variants={},
            region="south_asia_north",
            age=30,
            sex="male",
        )
        assert isinstance(recs, list)
        assert len(recs) > 0  # Risk-driven recs should still appear

    def test_single_day_plan(self, advisor, basic_recommendations):
        plans = advisor.create_meal_plan(
            basic_recommendations, region="south_asia_north", calories=2000, days=1
        )
        assert len(plans) == 1
        assert plans[0].day == 1
        assert plans[0].total_calories > 0


# ---------------------------------------------------------------------------
# Test region coverage
# ---------------------------------------------------------------------------


class TestRegionCoverage:
    """Ensure at least 5 different regions produce valid meal plans."""

    REGIONS = [
        "south_asia_north",
        "south_asia_south",
        "east_asia",
        "mediterranean",
        "north_america",
        "middle_east",
        "latin_america",
        "northern_europe",
        "southeast_asia",
        "sub_saharan_africa",
    ]

    @pytest.fixture(scope="class")
    def advisor_instance(self):
        return DietAdvisor()

    @pytest.mark.parametrize("region", REGIONS)
    def test_region_produces_valid_plan(self, advisor_instance, region):
        recs = advisor_instance.generate_recommendations(
            genetic_risks=["Type 2 diabetes"],
            variants={"rs1801133": "CT"},
            region=region,
            age=30,
            sex="male",
        )
        assert len(recs) > 0, f"No recommendations for {region}"

        plans = advisor_instance.create_meal_plan(recs, region=region, calories=2000, days=3)
        assert len(plans) == 3, f"Wrong number of days for {region}"
        for plan in plans:
            assert plan.total_calories > 0, f"Zero-calorie plan for {region}"
            assert len(plan.breakfast) > 0, f"Empty breakfast for {region}"
            assert len(plan.lunch) > 0, f"Empty lunch for {region}"
            assert len(plan.dinner) > 0, f"Empty dinner for {region}"
            assert len(plan.snacks) > 0, f"Empty snacks for {region}"


# ---------------------------------------------------------------------------
# Test calculate_nutrient_needs
# ---------------------------------------------------------------------------


class TestCalculateNutrientNeeds:
    def test_returns_nutrient_needs(self, advisor):
        needs = advisor.calculate_nutrient_needs(
            variants={"rs1801133": "CT"},
            age=40,
            sex="female",
        )
        assert isinstance(needs, list)
        for need in needs:
            assert isinstance(need, NutrientNeed)

    def test_nutrient_need_fields(self, advisor):
        needs = advisor.calculate_nutrient_needs(
            variants={"rs1801133": "CT"},
            age=40,
            sex="female",
        )
        if needs:
            need = needs[0]
            assert isinstance(need.nutrient, str)
            assert need.daily_target_mg > 0
            assert need.priority in ("critical", "high", "moderate", "low")
            assert isinstance(need.source_gene, str)
            assert isinstance(need.source_variant, str)
            assert isinstance(need.rationale, str)

    def test_homozygous_vs_heterozygous(self, advisor):
        """Homozygous carriers should get higher targets than heterozygous."""
        het_needs = advisor.calculate_nutrient_needs(
            variants={"rs1801133": "CT"}, age=40, sex="male"
        )
        hom_needs = advisor.calculate_nutrient_needs(
            variants={"rs1801133": "TT"}, age=40, sex="male"
        )
        # Same nutrient, but homozygous dosage should yield >=  heterozygous target
        het_map = {n.nutrient: n.daily_target_mg for n in het_needs}
        hom_map = {n.nutrient: n.daily_target_mg for n in hom_needs}
        common = set(het_map) & set(hom_map)
        for nutrient in common:
            assert hom_map[nutrient] >= het_map[nutrient], (
                f"{nutrient}: homozygous ({hom_map[nutrient]}) < heterozygous ({het_map[nutrient]})"
            )

    def test_empty_variants(self, advisor):
        needs = advisor.calculate_nutrient_needs(variants={}, age=30, sex="male")
        assert needs == []


# ---------------------------------------------------------------------------
# Test additional DietAdvisor methods
# ---------------------------------------------------------------------------


class TestAdditionalMethods:
    def test_get_region_specific_foods(self, advisor):
        foods = advisor.get_region_specific_foods("south_asia_north", "iron")
        assert isinstance(foods, list)
        for food in foods:
            assert isinstance(food, FoodItem)

    def test_get_telomere_protective_diet(self, advisor):
        recs = advisor.get_telomere_protective_diet(
            telomere_data={"mean_length_bp": 5000.0, "age": 50, "sex": "male"},
            region="south_asia_north",
        )
        assert isinstance(recs, list)
        assert len(recs) > 0
        for rec in recs:
            assert isinstance(rec, DietaryRecommendation)

    def test_adapt_to_restrictions(self, advisor, basic_recommendations):
        plans = advisor.create_meal_plan(
            basic_recommendations, region="south_asia_north", calories=2000, days=3
        )
        adapted = advisor.adapt_to_restrictions(plans, restrictions=["vegetarian"])
        assert len(adapted) == len(plans)
        for plan in adapted:
            assert isinstance(plan, MealPlan)
            assert "Adapted for: vegetarian" in plan.notes
