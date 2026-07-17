#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Tests for vram + configure_vram -- part of Auto VRAM Optimizer.
#  Copyright (C) 2026  KeilerHirsch. Licensed under the GNU GPL v3 or later.
#
#  Pure-logic tests: no registry, no GPU and no game install required.
#  Run with:  python -m unittest test_vram   (from the tool/ directory)

from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import configure_vram as cv
import vram


class CoerceIntTests(unittest.TestCase):
    def test_positive_int_passes_through(self):
        self.assertEqual(vram._coerce_positive_int(8585740288), 8585740288)

    def test_zero_and_negative_are_unknown(self):
        self.assertIsNone(vram._coerce_positive_int(0))
        self.assertIsNone(vram._coerce_positive_int(-5))

    def test_reg_binary_little_endian_bytes(self):
        # The exact blob an integrated GPU reported: 0x40000000 = 1 GiB.
        self.assertEqual(vram._coerce_positive_int(b"\x00\x00\x00\x40"), 1073741824)

    def test_empty_bytes_are_unknown(self):
        self.assertIsNone(vram._coerce_positive_int(b""))

    def test_other_types_are_unknown(self):
        self.assertIsNone(vram._coerce_positive_int("8 GB"))
        self.assertIsNone(vram._coerce_positive_int(None))


class BudgetTests(unittest.TestCase):
    def test_eight_gb_card_yields_five(self):
        # 8 GB cards report ~7.99 GiB; round -> 8, minus 3 headroom = 5.
        # (Earlier releases used -2 and returned 6, which OOM-crashed heavy maps.)
        self.assertEqual(vram.recommended_budget_gib(7.996), 5.0)

    def test_large_card_capped_by_fraction(self):
        # 16 GB: headroom would allow 13, but the 75% cap holds it at 12.
        self.assertEqual(vram.recommended_budget_gib(16.0), 12.0)
        # 24 GB: min(24-3, 24*0.75) = min(21, 18) = 18.
        self.assertEqual(vram.recommended_budget_gib(24.0), 18.0)

    def test_six_gb_card(self):
        # 6 GB: min(6-3, 6*0.75) = min(3, 4.5) = 3.
        self.assertEqual(vram.recommended_budget_gib(6.0), 3.0)

    def test_floor_clamp_applies_when_headroom_and_fraction_are_both_below_it(self):
        # 4 GB: min(1,3)=1, below the 2.0 floor -> clamp to 2.0 (2.0 <= 3.0 = 75% of 4, so
        # the floor itself never exceeds the fraction cap here -> clamp is safe.
        self.assertEqual(vram.recommended_budget_gib(4.0), 2.0)
        # 3 GB: min(0,2.25)=0, floor 2.0 <= fraction cap 2.25 -> clamp to 2.0 (66.7% of 3).
        self.assertEqual(vram.recommended_budget_gib(3.0), 2.0)

    def test_floor_never_exceeds_the_fraction_cap_on_small_cards(self):
        # Regression test for the HIGH finding (2026-07-17): floor_gib=2.0 applied
        # unconditionally let a 1 GiB iGPU get a 2.0 GiB budget (200% of its VRAM)
        # and a 2 GiB card get exactly 100%. The floor must never win against the
        # fraction cap once the card is small enough for that to matter.
        self.assertEqual(vram.recommended_budget_gib(1.0), 0.75)  # 75% of 1 GiB
        self.assertEqual(vram.recommended_budget_gib(2.0), 1.5)   # 75% of 2 GiB

    def test_breakdown_matches_recommended_budget_across_all_sizes(self):
        # budget_breakdown() and recommended_budget_gib() must always agree --
        # the status message is built from the former, the mod settings file
        # from the latter, and they must never describe two different numbers.
        for card_gib in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64):
            with self.subTest(card_gib=card_gib):
                breakdown = vram.budget_breakdown(float(card_gib))
                self.assertEqual(breakdown.budget, vram.recommended_budget_gib(float(card_gib)))

    def test_breakdown_reports_headroom_and_fraction_for_an_eight_gb_card(self):
        breakdown = vram.budget_breakdown(7.996)
        self.assertEqual(breakdown.rounded, 8)
        self.assertEqual(breakdown.by_headroom, 5.0)   # 8 - 3
        self.assertEqual(breakdown.by_fraction, 6.0)   # 8 * 0.75
        self.assertEqual(breakdown.budget, 5.0)         # min(6.0, max(2.0, 5.0))

    def test_budget_never_exceeds_the_physical_card_across_all_sizes(self):
        # The invariant the old floor violated, executed across the whole domain
        # rather than reasoned about in the abstract (see the "execute the
        # formula" lesson from the 2026-07-17 session).
        for card_gib in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64):
            with self.subTest(card_gib=card_gib):
                budget = vram.recommended_budget_gib(float(card_gib))
                self.assertLessEqual(budget, card_gib)


class NvidiaSmiParseTests(unittest.TestCase):
    def _run(self, returncode, stdout):
        result = mock.Mock(returncode=returncode, stdout=stdout)
        with mock.patch.object(vram.subprocess, "run", return_value=result):
            return vram.nvidia_smi_vram_bytes()

    def test_picks_largest_and_converts_mib(self):
        self.assertEqual(self._run(0, "8192\n4096\n"), 8192 * 1024 * 1024)

    def test_nonzero_return_is_zero(self):
        self.assertEqual(self._run(9, "8192\n"), 0)

    def test_missing_binary_is_zero(self):
        with mock.patch.object(vram.subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(vram.nvidia_smi_vram_bytes(), 0)


class WriteSettingsTests(unittest.TestCase):
    def test_written_xml_matches_the_mod_contract(self):
        # The mod's Lua reads getXMLFloat("textureStreamingBudget#vramGiB"),
        # i.e. root element <textureStreamingBudget vramGiB="...">.
        with tempfile.TemporaryDirectory() as d:
            profile = Path(d)
            out = cv.write_settings(6.0, profile)
            self.assertEqual(out, profile / "modSettings" / f"{cv.MOD_NAME}.xml")
            self.assertTrue(out.is_file())
            root = ET.parse(out).getroot()
            self.assertEqual(root.tag, "textureStreamingBudget")
            self.assertEqual(root.attrib["vramGiB"], "6.0")
            self.assertEqual(root.attrib["formulaGen"], str(vram.FORMULA_GEN))

    def test_settings_filename_matches_mod(self):
        # The written filename MUST equal the mod name the Lua reads back.
        self.assertEqual(cv.MOD_NAME, "FS25_AutoVRAMOptimizer")

    def test_creates_modsettings_dir(self):
        with tempfile.TemporaryDirectory() as d:
            profile = Path(d) / "fresh"
            out = cv.write_settings(4.0, profile)
            self.assertTrue(out.parent.is_dir())


class FindProfileTests(unittest.TestCase):
    def test_finds_default_documents_path(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            (home / "Documents" / "My Games" / "FarmingSimulator2025").mkdir(parents=True)
            with mock.patch.object(cv.Path, "home", return_value=home):
                self.assertIsNotNone(cv.find_profile_dir())

    def test_returns_none_when_absent(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(cv.Path, "home", return_value=Path(d)):
                self.assertIsNone(cv.find_profile_dir())


if __name__ == "__main__":
    unittest.main()
