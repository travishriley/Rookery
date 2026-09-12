"""Regression checks for PR #14's offline design tooling, not product policy."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir
import unittest

import check_design as design


class DesignReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = design.parse((design.ROOT / "schemas/0.1.0/rookery.schema.json").read_text(encoding="utf-8"))
        cls.examples = design.parse((design.ROOT / "schemas/0.1.0/examples.json").read_text(encoding="utf-8"))

    def test_bad_id_reports_the_field(self):
        example = deepcopy(self.examples[0])
        example["id"] = "bad id with spaces"
        self.assertIn("id:", design.explain(self.schema, example))

    def test_calendar_and_fractional_seconds(self):
        validator = design.make_validator(design.subschema(self.schema, "Time"))
        self.assertTrue(validator.is_valid("2026-09-12T12:00:00.123456789Z"))
        for value in ["2026-02-30T12:00:00Z", "2026-09-12T23:59:60Z", "2026-09-12T12:00:00Z\n"]:
            with self.subTest(value=value):
                self.assertFalse(validator.is_valid(value))

    def test_windows_path_terminator(self):
        validator = design.make_validator(design.subschema(self.schema, "Path"))
        self.assertTrue(validator.is_valid("nested/printer.cfg"))
        for value in ["printer.cfg\n", "printer.cfg\r\n", "nested/NUL", "nested./printer.cfg"]:
            with self.subTest(value=value):
                self.assertFalse(validator.is_valid(value))

    def test_reviewed_schema_mutations_are_detected(self):
        def drop_condition(node):
            node.pop("if")
            node.pop("then")

        # Mutate only in-memory schema copies; no working files or device paths are written.
        mutations = {
            "model risk containment": lambda d: drop_condition(d["DiagnosticResponse"]),
            "bounded proposal domain": lambda d: drop_condition(d["ProposalPayload"]),
            "path containment": lambda d: d["Path"].pop("pattern"),
            "matched activation evidence": lambda d: d["ActivationObservation"]["allOf"].pop(2),
            "backup read-back evidence": lambda d: drop_condition(d["BackupReceipt"]),
            "one independent change": lambda d: d["ProposalPayload"]["properties"]["changes"].pop("maxItems"),
            "non-null proposed value": lambda d: d["Change"]["properties"].update(proposed_value={"$ref": "#/$defs/Scalar"}),
            "numeric type agreement": lambda d: d["Change"]["allOf"].pop(1),
            "string type agreement": lambda d: d["Change"]["allOf"].pop(0),
            "boolean type agreement": lambda d: d["Change"]["allOf"].pop(2),
            "Klipper identity evidence": lambda d: d["PrinterIdentity"]["allOf"].pop(1),
            "Klipper hardware reference": lambda d: d["PrinterIdentity"]["allOf"].pop(2),
            "unique snapshot entries": lambda d: d["SourceSnapshot"]["properties"]["files"].pop("uniqueItems"),
            "unique capture entries": lambda d: d["EvidenceBundle"]["properties"]["captures"].pop("uniqueItems"),
            "candidate proposal binding": lambda d: d["CandidateBindings"]["properties"].pop("proposal_digest"),
            "reviewed range domain": lambda d: d["Range"]["required"].remove("domain"),
        }
        for label, mutate in mutations.items():
            with self.subTest(rule=label):
                schema = deepcopy(self.schema)
                mutate(schema["$defs"])
                with self.assertRaises(ValueError):
                    design.check_examples(schema, self.examples)
                    design.check_supplemental(schema, self.examples)

    def test_all_reference_link_forms_and_images(self):
        text = "[full][target] [target][] [target] ![image][asset]\n\n[target]: target.md\n[asset]: image.png\n"
        self.assertEqual(list(design.markdown_targets(text)), ["target.md", "target.md", "target.md", "image.png"])

    def test_code_fences_and_inline_code_are_not_links(self):
        text = (
            "``[inline](missing.md)``\n\n"
            "~~~markdown\n[tilde](missing.md)\n~~~\n\n"
            "````markdown\n```\n[nested](missing.md)\n```\n````\n\n"
            "    [indented](missing.md)\n\n"
            "<!-- [comment](missing.md) -->\n\n"
            "[real](README.md)\n"
        )
        self.assertEqual(list(design.markdown_targets(text)), ["README.md"])

    def test_autolinks_and_table_links_are_parsed(self):
        text = "<https://example.invalid>\n\n| Title |\n| --- |\n| [local](target.md) |\n"
        self.assertEqual(list(design.markdown_targets(text)), ["https://example.invalid", "target.md"])

    def test_prompt_links_directories_and_encoded_paths(self):
        with TemporaryDirectory(prefix="rookery-design-review-") as directory:
            root = Path(directory).resolve()
            self.assertTrue(root.is_relative_to(Path(gettempdir()).resolve()))
            (root / "prompts").mkdir()
            (root / "prompts/target (copy).md").write_text("Target", encoding="utf-8")
            prompt = root / "prompts/prompt.md"
            prompt.write_text("[target][]\n\n[target]: <target (copy).md>\n", encoding="utf-8")
            (root / "README.md").write_text("[directory](prompts/) <https://example.invalid>\n", encoding="utf-8")
            self.assertEqual(design.check_links(root), 2)
            prompt.write_text("[target][]\n\n[target]: missing.md\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing link: prompts"):
                design.check_links(root)

    def test_link_containment_and_missing_images(self):
        with TemporaryDirectory(prefix="rookery-design-review-") as directory:
            root = Path(directory).resolve()
            self.assertTrue(root.is_relative_to(Path(gettempdir()).resolve()))
            readme = root / "README.md"
            readme.write_text("[escape](%2e%2e/outside.md)\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Link escapes repository"):
                design.check_links(root)
            readme.write_text("![evidence](missing.png)\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing link"):
                design.check_links(root)


if __name__ == "__main__":
    unittest.main()
