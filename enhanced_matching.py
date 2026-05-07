#!/usr/bin/env python3
"""Matching logic for CAD devices vs master Excel devices."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Optional

from enhanced_models import CadDevice, ExcelDevice


def similarity_score(text1: str, text2: str) -> float:
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, text1.upper(), text2.upper()).ratio()


def keyword_overlap(set1: set[str], set2: set[str]) -> float:
    """Calculate keyword overlap score."""
    if not set1 or not set2:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union) if union else 0.0


def match_cad_to_excel(cad_device: CadDevice, excel_devices: list[ExcelDevice]) -> Optional[ExcelDevice]:
    """Find the best matching Excel device for a CAD device."""
    if not excel_devices:
        return None

    best_match = None
    best_score = 0.0

    cad_keywords = cad_device.match_keywords
    cad_system = cad_device.inferred_system_type

    for excel_dev in excel_devices:
        if excel_dev.matched:
            continue

        score = 0.0

        if excel_dev.system_type == cad_system:
            score += 0.3
        elif excel_dev.system_type and cad_system and cad_system[:4].upper() in excel_dev.system_type.upper():
            score += 0.15

        overlap = keyword_overlap(cad_keywords, excel_dev.match_keywords)
        score += overlap * 0.4

        name_sim = similarity_score(cad_device.raw_name, excel_dev.name)
        score += name_sim * 0.2

        cad_numbers = re.findall(r"\d+", cad_device.raw_name)
        if cad_numbers and excel_dev.abbreviated_name and excel_dev.abbreviated_name in cad_numbers:
            score += 0.1

        if score > best_score:
            best_score = score
            best_match = excel_dev

    if best_match and best_score > 0.25:
        best_match.matched = True
        return best_match

    return None
