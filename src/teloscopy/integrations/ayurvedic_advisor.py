"""
Ayurvedic remedy advisor for health checkup integration.

Provides personalised Ayurvedic recommendations (from Charaka Samhita and
Sushruta Samhita) based on detected health conditions and abdomen scan findings.

The knowledge base is loaded from ``ayurvedic_remedies.json`` which contains
condition-specific remedies, lifestyle guidance, yoga/pranayama prescriptions,
dietary principles, and contraindications.

Usage::

    from teloscopy.integrations.ayurvedic_advisor import AyurvedicAdvisor

    advisor = AyurvedicAdvisor()
    analysis = advisor.get_remedies(
        conditions=["diabetes", "dyslipidemia"],
        abdomen_findings=[{"finding": "Grade 1 fatty liver", "severity": "mild"}],
    )
    print(analysis.dosha_assessment)
    for remedy in analysis.remedies:
        print(f"{remedy.name}: {remedy.dosage}")
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data directory — relative to this file's location
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "json"
_REMEDIES_FILE = "ayurvedic_remedies.json"

_DEFAULT_DISCLAIMER = (
    "Ayurvedic remedies are based on traditional knowledge from Charaka Samhita and "
    "Sushruta Samhita. These are for informational purposes only and should not replace "
    "professional medical advice. Consult a qualified Ayurvedic practitioner (BAMS) "
    "before starting any herbal regimen, especially if you are on allopathic medication."
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AyurvedicRemedy:
    """A single Ayurvedic remedy recommendation.

    Attributes
    ----------
    name : str
        Classical name of the formulation.
    ingredients : list[str]
        Key ingredients / herbs in the formulation.
    preparation : str
        How the remedy is traditionally prepared.
    dosage : str
        Recommended dosage and administration instructions.
    source : str
        Charaka/Sushruta Samhita or other classical text reference.
    mechanism : str
        Pharmacological or Ayurvedic rationale for efficacy.
    for_conditions : list[str]
        Which detected conditions this remedy addresses.
    """

    name: str
    ingredients: list[str] = field(default_factory=list)
    preparation: str = ""
    dosage: str = ""
    source: str = ""
    mechanism: str = ""
    for_conditions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "ingredients": self.ingredients,
            "preparation": self.preparation,
            "dosage": self.dosage,
            "source": self.source,
            "mechanism": self.mechanism,
            "for_conditions": self.for_conditions,
        }


@dataclass
class AyurvedicAnalysis:
    """Complete Ayurvedic analysis based on Charaka & Sushruta Samhita.

    Attributes
    ----------
    dosha_assessment : str
        Overall dosha involvement summary derived from all conditions.
    remedies : list[AyurvedicRemedy]
        Top 5–8 prioritised remedies (deduplicated, multi-condition first).
    lifestyle_recommendations : list[str]
        Merged and deduplicated lifestyle advice.
    yoga_asanas : list[str]
        Deduplicated yoga pose recommendations.
    pranayama : list[str]
        Deduplicated breathing exercise recommendations.
    dietary_principles : list[str]
        Ayurvedic dietary advice aggregated from all conditions.
    contraindications : list[str]
        Safety warnings and contraindications.
    general_disclaimer : str
        Legal/medical disclaimer text.
    """

    dosha_assessment: str = ""
    remedies: list[AyurvedicRemedy] = field(default_factory=list)
    lifestyle_recommendations: list[str] = field(default_factory=list)
    yoga_asanas: list[str] = field(default_factory=list)
    pranayama: list[str] = field(default_factory=list)
    dietary_principles: list[str] = field(default_factory=list)
    contraindications: list[str] = field(default_factory=list)
    general_disclaimer: str = _DEFAULT_DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        """Serialise the full analysis to a JSON-compatible dictionary."""
        return {
            "dosha_assessment": self.dosha_assessment,
            "remedies": [r.to_dict() for r in self.remedies],
            "lifestyle_recommendations": self.lifestyle_recommendations,
            "yoga_asanas": self.yoga_asanas,
            "pranayama": self.pranayama,
            "dietary_principles": self.dietary_principles,
            "contraindications": self.contraindications,
            "general_disclaimer": self.general_disclaimer,
        }


# ---------------------------------------------------------------------------
# Helper: load JSON with graceful fallback
# ---------------------------------------------------------------------------


def _load_remedies_json() -> dict[str, Any]:
    """Load the Ayurvedic remedies knowledge base from disk.

    Returns an empty dict (with a warning) if the file is missing or malformed,
    so the advisor can still be instantiated without crashing.
    """
    path = _DATA_DIR / _REMEDIES_FILE
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        logger.info("Loaded Ayurvedic remedies from %s (%d conditions)", path, len(data.get("conditions", {})))
        return data
    except FileNotFoundError:
        logger.warning("Ayurvedic remedies file not found at %s — advisor will return empty results", path)
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to parse Ayurvedic remedies JSON (%s): %s", path, exc)
        return {}


# ---------------------------------------------------------------------------
# Main advisor class
# ---------------------------------------------------------------------------


class AyurvedicAdvisor:
    """Provides Ayurvedic remedy recommendations based on detected health conditions.

    The advisor loads its knowledge base from ``ayurvedic_remedies.json`` at
    initialisation.  If the file is absent or corrupt the advisor degrades
    gracefully, returning empty :class:`AyurvedicAnalysis` objects instead of
    raising exceptions.

    Parameters
    ----------
    data : dict | None
        Pre-loaded JSON data.  When *None* (the default) the advisor loads
        from the standard data directory.

    Example
    -------
    >>> advisor = AyurvedicAdvisor()
    >>> result = advisor.get_remedies(
    ...     conditions=["diabetes", "dyslipidemia"],
    ...     abdomen_findings=[{"finding": "Grade 1 fatty liver"}],
    ... )
    >>> result.dosha_assessment
    'Kapha-Pitta-Vata (Prameha/Madhumeha), Kapha-Medas (Medoroga), ...'
    """

    # Maximum number of remedies returned in the final analysis
    _MAX_REMEDIES = 8

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = data if data is not None else _load_remedies_json()
        self._conditions: dict[str, Any] = self._data.get("conditions", {})
        self._abdomen_mappings: dict[str, str] = self._data.get("abdomen_finding_mappings", {})

    # -- public API ----------------------------------------------------------

    def get_remedies(
        self,
        conditions: list[str],
        abdomen_findings: list[dict[str, Any]] | None = None,
    ) -> AyurvedicAnalysis:
        """Return comprehensive Ayurvedic recommendations for the given conditions.

        Parameters
        ----------
        conditions : list[str]
            Detected condition keys (e.g. ``"diabetes"``, ``"dyslipidemia"``).
        abdomen_findings : list[dict] | None
            Abdomen scan findings — each dict should contain at least a
            ``"finding"`` key (e.g. ``"Grade 1 fatty liver"``).

        Returns
        -------
        AyurvedicAnalysis
            A fully populated analysis object with prioritised remedies,
            lifestyle advice, yoga/pranayama, dietary principles, and
            contraindications.
        """
        if abdomen_findings is None:
            abdomen_findings = []

        # 1. Collect all condition keys (direct + mapped from abdomen findings)
        all_keys = self._collect_condition_keys(conditions, abdomen_findings)
        if not all_keys:
            logger.info("No mappable conditions found — returning empty Ayurvedic analysis")
            return AyurvedicAnalysis()

        logger.info("Ayurvedic analysis for %d condition(s): %s", len(all_keys), ", ".join(all_keys))

        # 2. Gather raw data from each matched condition
        all_remedies: list[dict[str, Any]] = []  # (remedy_dict, condition_key)
        all_doshas: list[str] = []
        all_lifestyle: list[str] = []
        all_yoga: list[str] = []
        all_pranayama: list[str] = []
        all_dietary: list[str] = []
        all_contraindications: list[str] = []
        condition_descriptions: list[str] = []

        for key in all_keys:
            entry = self._conditions.get(key)
            if entry is None:
                logger.debug("Condition key %r not found in Ayurvedic knowledge base", key)
                continue

            dosha = entry.get("dosha", "")
            description = entry.get("description", "")
            if dosha:
                all_doshas.append(f"{dosha} ({description})" if description else dosha)
            if description:
                condition_descriptions.append(description)

            # Collect remedies and tag them with the condition key
            for remedy in entry.get("remedies", []):
                all_remedies.append({"remedy": remedy, "condition_key": key})

            all_lifestyle.extend(entry.get("lifestyle", []))
            all_yoga.extend(entry.get("yoga_asanas", []))
            all_pranayama.extend(entry.get("pranayama", []))
            all_dietary.extend(entry.get("dietary_principles", []))
            all_contraindications.extend(entry.get("contraindications", []))

        # 3. Build dosha assessment summary
        dosha_assessment = self._build_dosha_assessment(all_doshas)

        # 4. Deduplicate and prioritise remedies
        prioritised = self._prioritize_remedies(all_remedies)

        # 5. Deduplicate list-type recommendations (preserve order)
        lifestyle = _deduplicate_preserve_order(all_lifestyle)
        yoga = _deduplicate_preserve_order(all_yoga)
        pranayama = _deduplicate_preserve_order(all_pranayama)
        dietary = _deduplicate_preserve_order(all_dietary)
        contraindications = _deduplicate_preserve_order(all_contraindications)

        return AyurvedicAnalysis(
            dosha_assessment=dosha_assessment,
            remedies=prioritised,
            lifestyle_recommendations=lifestyle,
            yoga_asanas=yoga,
            pranayama=pranayama,
            dietary_principles=dietary,
            contraindications=contraindications,
            general_disclaimer=_DEFAULT_DISCLAIMER,
        )

    # -- internal helpers ----------------------------------------------------

    def _collect_condition_keys(
        self,
        conditions: list[str],
        abdomen_findings: list[dict[str, Any]],
    ) -> list[str]:
        """Merge direct condition keys with keys derived from abdomen findings.

        Returns a deduplicated, order-preserved list of condition keys that
        exist in the knowledge base.
        """
        seen: set[str] = set()
        result: list[str] = []

        # Direct condition keys
        for cond in conditions:
            key = cond.strip().lower().replace(" ", "_")
            if key and key not in seen:
                seen.add(key)
                result.append(key)

        # Map abdomen findings to condition keys
        for finding in abdomen_findings:
            finding_text = finding.get("finding", "") if isinstance(finding, dict) else str(finding)
            mapped = self._map_abdomen_to_key(finding_text)
            if mapped and mapped not in seen:
                seen.add(mapped)
                result.append(mapped)

        return result

    def _map_abdomen_to_key(self, finding: str) -> str | None:
        """Map an abdomen finding description to a condition key.

        Parameters
        ----------
        finding : str
            Free-text abdomen finding such as ``"Grade 1 fatty liver"`` or
            ``"Hepatomegaly (enlarged liver)"``.

        Returns
        -------
        str | None
            Matching condition key, or *None* if no mapping found.
        """
        if not finding:
            return None

        normalised = finding.strip().lower()

        # Exact match first
        if normalised in self._abdomen_mappings:
            return self._abdomen_mappings[normalised]

        # Substring / partial match (e.g. "Hepatomegaly (enlarged liver)" contains "hepatomegaly")
        for pattern, key in self._abdomen_mappings.items():
            if pattern in normalised or normalised in pattern:
                return key

        logger.debug("No Ayurvedic mapping for abdomen finding: %r", finding)
        return None

    def _prioritize_remedies(
        self,
        all_remedies: list[dict[str, Any]],
    ) -> list[AyurvedicRemedy]:
        """Deduplicate remedies by name and prioritise those addressing multiple conditions.

        Remedies that appear for more conditions are ranked higher because they
        provide broader therapeutic coverage.

        Parameters
        ----------
        all_remedies : list[dict]
            Each element is ``{"remedy": <dict>, "condition_key": <str>}``.

        Returns
        -------
        list[AyurvedicRemedy]
            Up to :attr:`_MAX_REMEDIES` deduplicated, prioritised remedy objects.
        """
        if not all_remedies:
            return []

        # Group by remedy name → collect condition keys
        grouped: dict[str, dict[str, Any]] = {}
        condition_sets: dict[str, list[str]] = {}

        for entry in all_remedies:
            remedy = entry["remedy"]
            cond_key = entry["condition_key"]
            name = remedy.get("name", "Unknown")

            if name not in grouped:
                grouped[name] = remedy
                condition_sets[name] = []

            if cond_key not in condition_sets[name]:
                condition_sets[name].append(cond_key)

        # Sort by number of conditions addressed (descending), then alphabetically
        sorted_names = sorted(
            grouped.keys(),
            key=lambda n: (-len(condition_sets[n]), n),
        )

        # Build AyurvedicRemedy objects (limit to max)
        result: list[AyurvedicRemedy] = []
        for name in sorted_names[: self._MAX_REMEDIES]:
            r = grouped[name]
            result.append(
                AyurvedicRemedy(
                    name=name,
                    ingredients=r.get("ingredients", []),
                    preparation=r.get("preparation", ""),
                    dosage=r.get("dosage", ""),
                    source=r.get("source", ""),
                    mechanism=r.get("mechanism", ""),
                    for_conditions=condition_sets[name],
                )
            )

        logger.info(
            "Prioritised %d/%d unique remedies (top addresses %d condition(s))",
            len(result),
            len(grouped),
            len(condition_sets[sorted_names[0]]) if sorted_names else 0,
        )
        return result

    @staticmethod
    def _build_dosha_assessment(doshas: list[str]) -> str:
        """Build a human-readable dosha involvement summary.

        Parameters
        ----------
        doshas : list[str]
            Dosha descriptions collected from each matched condition.

        Returns
        -------
        str
            A semicolon-separated summary, or a default message if no doshas
            are available.
        """
        if not doshas:
            return "No specific dosha assessment available for the detected conditions."

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for d in doshas:
            if d not in seen:
                seen.add(d)
                unique.append(d)

        # Count primary dosha mentions for a summary prefix
        dosha_names = ["Vata", "Pitta", "Kapha"]
        counts: Counter[str] = Counter()
        combined_text = " ".join(unique)
        for name in dosha_names:
            if name.lower() in combined_text.lower():
                # Count occurrences across all condition-dosha strings
                counts[name] = combined_text.lower().count(name.lower())

        if counts:
            dominant = counts.most_common()
            primary = ", ".join(f"{name}" for name, _ in dominant if _ > 0)
            prefix = f"Primary dosha involvement: {primary}. "
        else:
            prefix = ""

        detail = "; ".join(unique)
        return f"{prefix}Condition-wise: {detail}."

    def __repr__(self) -> str:
        n = len(self._conditions)
        return f"AyurvedicAdvisor(conditions_loaded={n})"


# ---------------------------------------------------------------------------
# Module-level utility
# ---------------------------------------------------------------------------


def _deduplicate_preserve_order(items: list[str]) -> list[str]:
    """Return *items* with duplicates removed, preserving first-seen order.

    Comparison is case-insensitive but the original casing of the first
    occurrence is retained.
    """
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result
