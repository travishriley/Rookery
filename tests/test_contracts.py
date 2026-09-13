"""Synthetic parsing tests, not a policy, backup, or OS-boundary test suite."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from importlib import metadata, resources
import json
from pathlib import Path
import tomllib
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from referencing.exceptions import NoSuchResource

from rookery import ContractError, Record, RecordKind, parse_record
from rookery import contracts
from tools import check_design as design


ROOT = Path(__file__).resolve().parents[1]


def wire(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False).encode("utf-8")


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.examples = json.loads((ROOT / "schemas/0.1.0/examples.json").read_text(encoding="utf-8"))
        cls.by_kind = {value["kind"]: value for value in cls.examples}

    def assert_rejected(self, raw, code=None):
        with self.assertRaises(ContractError) as failure:
            parse_record(raw)
        if code is not None:
            self.assertEqual(failure.exception.code, code)
        return failure.exception

    def test_all_eleven_kinds_have_valid_immutable_envelopes(self):
        self.assertEqual({value["kind"] for value in self.examples}, {kind.value for kind in RecordKind})
        for value in self.examples:
            with self.subTest(kind=value["kind"]):
                raw = wire(value)
                record = parse_record(raw)
                self.assertIsInstance(record, Record)
                self.assertIsInstance(record.kind, RecordKind)
                self.assertEqual(record.kind, value["kind"])
                self.assertEqual(record.id, value["id"])
                self.assertEqual(record.schema_version, "0.1.0")
                self.assertEqual(record.created_at, value["created_at"])
                self.assertEqual(record.raw_json, raw)

    def test_design_record_probes_also_exercise_the_product_parser(self):
        schema = json.loads((ROOT / "schemas/0.1.0/rookery.schema.json").read_text(encoding="utf-8"))
        factory = design.make_validator
        case = self

        class ParityValidator:
            def __init__(self, source):
                self.reference = factory(source)

            def is_valid(self, value):
                expected = self.reference.is_valid(value)
                try:
                    parse_record(wire(value))
                    actual = True
                except ContractError:
                    actual = False
                case.assertEqual(actual, expected, f"Schema/parser parity: {value.get('kind')}")
                return actual

            def iter_errors(self, value):
                return self.reference.iter_errors(value)

        with patch.object(design, "make_validator", ParityValidator):
            positive, negative = design.check_examples(schema, self.examples)
        self.assertGreater(positive, 11)
        self.assertGreater(negative, 90)

    def test_packaged_schema_is_the_authoritative_schema(self):
        packaged = resources.files("rookery.schemas").joinpath("0.1.0/rookery.schema.json")
        self.assertEqual(packaged.read_bytes(), (ROOT / "schemas/0.1.0/rookery.schema.json").read_bytes())
        Draft202012Validator.check_schema(json.loads(packaged.read_bytes()))
        self.assertEqual(metadata.version("rookery-core"), "0.1.0.dev1")
        self.assertTrue(resources.files("rookery").joinpath("py.typed").is_file())
        # Exercise a real wheel install, not an accidentally importable source tree.
        self.assertFalse(Path(contracts.__file__).resolve().is_relative_to(ROOT / "src"))

    def test_runtime_dependency_pins_match_installed_versions(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        for requirement in project["dependencies"]:
            name, version = requirement.split("==")
            with self.subTest(package=name):
                self.assertEqual(metadata.version(name), version)

    def test_schema_version_kind_and_root_fail_closed(self):
        for value in [None, [], "PrinterIdentity", True, 0]:
            with self.subTest(value=value):
                self.assert_rejected(wire(value), "object_required")
        for field, value, code in [
            ("schema_version", "0.2.0", "unsupported_version"),
            ("schema_version", 1, "unsupported_version"),
            ("kind", "ApplyReceipt", "unknown_kind"),
            ("kind", {}, "unknown_kind"),
            ("kind", None, "unknown_kind"),
        ]:
            changed = deepcopy(self.examples[0])
            changed[field] = value
            self.assert_rejected(wire(changed), code)

    def test_python_objects_paths_and_text_are_not_an_input_interface(self):
        for value in [self.examples[0], "printer.cfg", Path("printer.cfg"), bytearray(wire(self.examples[0]))]:
            with self.subTest(type=type(value)):
                self.assert_rejected(value, "bytes_required")

    def test_duplicate_keys_include_nested_and_escaped_names(self):
        for raw in [b'{"id":"one","id":"two"}', b'{"id":1,"\\u0069d":2}',
                    b'{"outer":{"value":1,"value":2}}']:
            self.assert_rejected(raw, "duplicate_key")

    def test_nonfinite_overflow_underflow_and_long_numbers(self):
        for token in ["NaN", "Infinity", "-Infinity"]:
            self.assert_rejected(('{"n":' + token + '}').encode(), "non_finite_number")
        for token in ["1e309", "-1e309", "1e-9999"]:
            self.assert_rejected(('{"n":' + token + '}').encode(), "number_out_of_range")
        for token in ["1" * 257, "0." + "1" * 257]:
            self.assert_rejected(('{"n":' + token + '}').encode(), "number_too_long")

    def test_malformed_json_and_non_utf8_are_rejected(self):
        for raw in [b"", b"{", b"{}{}", b'{"n":01}', b'{"n":1,}', b"\xef\xbb\xbf{}"]:
            self.assert_rejected(raw, "invalid_json")
        for raw in [b"\xff", b"\xff\xfe{\x00}\x00"]:
            self.assert_rejected(raw, "invalid_utf8")
        for raw in [b'{"label":"\\ud800"}', b'{"\\udfff":1}']:
            self.assert_rejected(raw, "invalid_unicode")

    def test_resource_limits_reject_before_schema_evaluation(self):
        self.assert_rejected(b" " * (contracts.MAX_RECORD_BYTES + 1), "record_too_large")
        self.assert_rejected(b"[" * 65 + b"0" + b"]" * 65, "too_deep")
        self.assert_rejected(b"[" * 2000 + b"0" + b"]" * 2000, "too_deep")
        many = b"[" + b"0," * contracts.MAX_NODES + b"0]"
        self.assert_rejected(many, "too_many_nodes")

    def test_nested_data_and_original_bytes_are_immutable(self):
        source = deepcopy(self.by_kind["SourceSnapshot"])
        record = parse_record(wire(source))
        source["files"][0]["path"] = "different.json"
        self.assertEqual(record.data["files"][0]["path"], "process.json")
        with self.assertRaises(FrozenInstanceError):
            record.raw_json = b"{}"
        with self.assertRaises(TypeError):
            record.data["id"] = "different"
        with self.assertRaises(TypeError):
            record.data["files"][0]["path"] = "different.json"
        with self.assertRaises(TypeError):
            record.data["files"][0] = {}
        with self.assertRaises(TypeError):
            hash(record)
        with self.assertRaises(ContractError):
            replace(record, raw_json=b"{}")

    def test_resource_limit_boundaries_are_not_off_by_one(self):
        raw = wire(self.examples[0])
        raw += b" " * (contracts.MAX_RECORD_BYTES - len(raw))
        self.assertEqual(parse_record(raw).raw_json, raw)
        self.assert_rejected(b"[" * 64 + b"0" + b"]" * 64, "object_required")
        nodes_at_limit = b"[" + b"0," * (contracts.MAX_NODES - 2) + b"0]"
        self.assert_rejected(nodes_at_limit, "object_required")
        value = deepcopy(self.by_kind["ChangeProposal"])
        value["changes"][0]["proposed_value"] = int("1" * contracts.MAX_NUMBER_CHARS)
        self.assertIsInstance(parse_record(wire(value)), Record)

    def test_exact_decimal_and_timestamp_precision_are_preserved(self):
        value = deepcopy(self.by_kind["ChangeProposal"])
        value["created_at"] = "2026-09-12T12:00:00.123456789123456789Z"
        raw = wire(value).replace(b'"proposed_value": 2', b'"proposed_value": 0.10000000000000000000001')
        record = parse_record(raw)
        self.assertEqual(record.data["changes"][0]["proposed_value"], Decimal("0.10000000000000000000001"))
        self.assertEqual(record.created_at, value["created_at"])
        self.assertEqual(record.raw_json, raw)

    def test_large_integers_are_not_rounded_to_binary64(self):
        value = deepcopy(self.by_kind["ChangeProposal"])
        value["changes"][0]["proposed_value"] = 9007199254740993
        record = parse_record(wire(value))
        self.assertEqual(record.data["changes"][0]["proposed_value"], 9007199254740993)

    def test_integer_schema_semantics_without_boolean_or_string_coercion(self):
        raw = wire(self.by_kind["ExperimentManifest"])
        self.assertEqual(parse_record(raw.replace(b'"revision": 1', b'"revision": 1.0')).data["revision"], Decimal("1.0"))
        for token in [b"1.5", b"true", b'"1"']:
            self.assert_rejected(raw.replace(b'"revision": 1', b'"revision": ' + token))

    def test_dates_ids_and_digests_require_complete_valid_values(self):
        for value in ["2026-02-30T12:00:00Z", "2026-09-12T23:59:60Z", "2026-09-12T12:00:00+00:00"]:
            changed = deepcopy(self.examples[0])
            changed["created_at"] = value
            self.assert_rejected(wire(changed))
        for field, value in [("id", "synthetic\n"), ("hardware_digest", "sha256:" + "a" * 64 + "\n")]:
            changed = deepcopy(self.examples[0])
            changed[field] = value
            self.assert_rejected(wire(changed))

    def test_validation_errors_do_not_echo_private_values(self):
        value = deepcopy(self.examples[0])
        value["id"] = "do not echo this private content"
        error = self.assert_rejected(wire(value))
        self.assertEqual(error.path, ("id",))
        self.assertNotIn(value["id"], str(error))
        self.assertNotIn(value["label"], repr(parse_record(wire(self.examples[0]))))

    def test_unknown_properties_and_script_strings_are_inert_data(self):
        value = deepcopy(self.examples[0])
        value["arbitrary_script"] = "untrusted text"
        self.assert_rejected(wire(value))
        value = deepcopy(self.examples[0])
        value["label"] = "https://example.invalid/ is data; never fetch or execute"
        with patch("socket.socket", side_effect=AssertionError("unexpected socket")), \
             patch("subprocess.Popen", side_effect=AssertionError("unexpected process")):
            self.assertEqual(parse_record(wire(value)).data["label"], value["label"])
        with self.assertRaises(NoSuchResource):
            contracts._no_remote_schema("https://example.invalid/schema")

    def test_shape_acceptance_explicitly_does_not_enforce_semantic_policy(self):
        value = deepcopy(self.by_kind["CalibrationDefinition"])
        value["ranges"][0].update(minimum=300, maximum=10)
        self.assertIsInstance(parse_record(wire(value)), Record)
        value = deepcopy(self.by_kind["SourceSnapshot"])
        second = deepcopy(value["files"][0])
        second["digest"] = "sha256:" + "7" * 64
        value["files"].append(second)
        self.assertIsInstance(parse_record(wire(value)), Record)
        # These acceptance results are limitations, never backup/authorization verdicts.


if __name__ == "__main__":
    unittest.main()
