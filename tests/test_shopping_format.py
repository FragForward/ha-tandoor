"""Tests for the shopping list format (docs/spec/shopping-list.md, K2-K4, K6, K8-K10)."""

import pathlib
import sys
import unittest

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "tandoor")
)

import shopping_format as sf  # noqa: E402


def changes(entry, item, option):
    """Shortcut: entry=(food, amount, unit, checked), item=(summary, description, checked)."""
    return sf.update_changes(
        entry_food=entry[0],
        entry_amount=entry[1],
        entry_unit=entry[2],
        entry_checked=entry[3],
        item_summary=item[0],
        item_description=item[1],
        item_checked=item[2],
        amount_in_description=option,
    )


class SummaryFormat(unittest.TestCase):
    def test_k2_summary_without_empty_parts(self):
        self.assertEqual(sf.format_summary("Mehl", 2.0, "kg"), "2 kg Mehl")
        self.assertEqual(sf.format_summary("Eier", 3.0, None), "3 Eier")
        self.assertEqual(sf.format_summary("Salz", 0.0, None), "Salz")
        self.assertEqual(sf.format_summary("Salz", 0.0, ""), "Salz")

    def test_k6_description_amount_and_unit(self):
        self.assertEqual(sf.format_amount_unit(2.0, "kg"), "2 kg")
        self.assertEqual(sf.format_amount_unit(3.0, None), "3")
        self.assertEqual(sf.format_amount_unit(1.5, "Esslöffel"), "1.5 Esslöffel")
        self.assertIsNone(sf.format_amount_unit(0.0, None))


class CreateFields(unittest.TestCase):
    def test_k3_option_off_parses_leading_amount(self):
        self.assertEqual(sf.create_fields("2 Onions", None, False), ("Onions", 2.0, None))
        self.assertEqual(sf.create_fields("1,5 Milch", None, False), ("Milch", 1.5, None))
        self.assertEqual(sf.create_fields("Salz", None, False), ("Salz", 0.0, None))
        self.assertEqual(sf.create_fields("   ", None, False)[0], "")

    def test_k8_option_on_reads_description(self):
        self.assertEqual(sf.create_fields("Mehl", "2 kg", True), ("Mehl", 2.0, "kg"))
        self.assertEqual(sf.create_fields("Eier", "2", True), ("Eier", 2.0, None))
        self.assertEqual(sf.create_fields("Milch", "1,5 l", True), ("Milch", 1.5, "l"))
        self.assertEqual(sf.create_fields("Mehl", "2 kg, organic", True), ("Mehl", 2.0, "kg"))
        self.assertEqual(sf.create_fields("Mehl", "organic", True), ("Mehl", 0.0, None))
        self.assertEqual(sf.create_fields("Mehl", None, True), ("Mehl", 0.0, None))
        self.assertEqual(sf.create_fields("Mehl", "   ", True), ("Mehl", 0.0, None))
        # K8: the summary is not parsed when the option is on
        self.assertEqual(sf.create_fields("2 Onions", None, True), ("2 Onions", 0.0, None))

    def test_k8_long_unit_kept(self):
        self.assertEqual(
            sf.create_fields("Hefe", "2 Packung(en)", True), ("Hefe", 2.0, "Packung(en)")
        )


class UpdateChanges(unittest.TestCase):
    def test_k4_option_off_check_off_sends_only_status(self):
        entry = ("Mehl", 2.0, "kg", False)
        self.assertEqual(changes(entry, ("2 kg Mehl", None, True), False), {"checked": True})

    def test_k4_option_off_changed_summary_parsed(self):
        entry = ("Mehl", 2.0, None, False)
        self.assertEqual(
            changes(entry, ("3 Mehl", None, False), False),
            {"food_name": "Mehl", "amount": 3.0},
        )

    def test_k9_option_on_check_off_keeps_amount_unit_food(self):
        """The bug in PR #25: checking off reset amount to 0 and unit to ''."""
        entry = ("Mehl", 2.0, "kg", False)
        self.assertEqual(changes(entry, ("Mehl", "2 kg", True), True), {"checked": True})
        entry = ("Eier", 3.0, None, True)
        self.assertEqual(changes(entry, ("Eier", "3", False), True), {"checked": False})
        entry = ("Salz", 0.0, None, False)
        self.assertEqual(changes(entry, ("Salz", None, True), True), {"checked": True})

    def test_k9_untrimmed_tandoor_values_do_not_count_as_change(self):
        """Tandoor names with trailing spaces must not trigger a rename on check-off."""
        entry = ("Mehl ", 2.0, "kg ", False)
        self.assertEqual(changes(entry, ("Mehl", "2 kg", True), True), {"checked": True})
        self.assertEqual(changes(entry, ("2 kg Mehl", None, True), False), {"checked": True})

    def test_k10_option_on_changed_description(self):
        entry = ("Mehl", 2.0, "kg", False)
        self.assertEqual(
            changes(entry, ("Mehl", "500 g", False), True),
            {"amount": 500.0, "unit_name": "g"},
        )

    def test_k10_option_on_cleared_description_removes_unit(self):
        entry = ("Mehl", 2.0, "kg", False)
        self.assertEqual(
            changes(entry, ("Mehl", "", False), True), {"amount": 0.0, "unit_name": ""}
        )
        self.assertEqual(
            changes(entry, ("Mehl", None, False), True), {"amount": 0.0, "unit_name": ""}
        )

    def test_k10_option_on_rename_only_when_changed(self):
        entry = ("Mehl", 2.0, "kg", False)
        self.assertEqual(
            changes(entry, ("Dinkelmehl", "2 kg", False), True), {"food_name": "Dinkelmehl"}
        )
        self.assertEqual(changes(entry, ("Mehl", "2 kg", False), True), {})


if __name__ == "__main__":
    unittest.main()
