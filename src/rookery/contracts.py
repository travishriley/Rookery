"""Bounded, immutable envelopes for the eleven v0.1.0 record shapes.

Only the packaged schema is read. No caller-supplied path, URL or executable is
accepted. Semantic policy and canonical record hashing are deliberately absent.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from importlib.resources import files
import json
import math
import re
from types import MappingProxyType
from typing import Literal, NewType, TypeAlias, cast

from jsonschema import Draft202012Validator, FormatChecker, validators
from jsonschema.exceptions import best_match
from referencing import Registry
from referencing.exceptions import NoSuchResource


MAX_RECORD_BYTES = 1024 * 1024
MAX_DEPTH = 64
MAX_NODES = 50000
MAX_NUMBER_CHARS = 256
RecordId = NewType("RecordId", str)
JsonValue: TypeAlias = None | bool | int | Decimal | str | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]


class RecordKind(StrEnum):
    PRINTER_IDENTITY = "PrinterIdentity"
    SOURCE_SNAPSHOT = "SourceSnapshot"
    BACKUP_RECEIPT = "BackupReceipt"
    CALIBRATION_DEFINITION = "CalibrationDefinition"
    EXPERIMENT_MANIFEST = "ExperimentManifest"
    EVIDENCE_BUNDLE = "EvidenceBundle"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    CHANGE_PROPOSAL = "ChangeProposal"
    APPROVAL_RECORD = "ApprovalRecord"
    ACTIVATION_OBSERVATION = "ActivationObservation"
    EXPERIMENT_RESULT = "ExperimentResult"


class ContractError(ValueError):
    """Stable error code and field location, without echoing input values."""

    def __init__(self, code: str, path: tuple[str | int, ...] = ()):
        self.code = code
        self.path = path
        location = "/".join(str(part) for part in path) or "(record root)"
        super().__init__(f"{code}: {location}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate_key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ContractError("non_finite_number")


def _integer(text):
    if len(text) > MAX_NUMBER_CHARS:
        raise ContractError("number_too_long")
    return int(text)


def _decimal(text):
    if len(text) > MAX_NUMBER_CHARS:
        raise ContractError("number_too_long")
    value = Decimal(text)
    # Bound magnitude without converting the stored value to a rounded float.
    approximate = float(value)
    if not math.isfinite(approximate) or (value != 0 and approximate == 0):
        raise ContractError("number_out_of_range")
    return value


def _check_tree(value):
    pending = [(value, 0)]
    count = 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > MAX_NODES:
            raise ContractError("too_many_nodes")
        if depth > MAX_DEPTH:
            raise ContractError("too_deep")
        if isinstance(node, dict):
            pending.extend((item, depth + 1) for pair in node.items() for item in pair)
        elif isinstance(node, list):
            pending.extend((item, depth + 1) for item in node)
        elif isinstance(node, str):
            try:
                node.encode("utf-8")
            except UnicodeEncodeError:
                raise ContractError("invalid_unicode") from None


def _decode(raw: bytes):
    if type(raw) is not bytes:
        raise ContractError("bytes_required")
    if len(raw) > MAX_RECORD_BYTES:
        raise ContractError("record_too_large")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_int=_integer, parse_float=_decimal, parse_constant=_reject_constant)
    except ContractError:
        raise
    except UnicodeDecodeError:
        raise ContractError("invalid_utf8") from None
    except RecursionError:
        raise ContractError("too_deep") from None
    except (ValueError, ArithmeticError):
        raise ContractError("invalid_json") from None
    _check_tree(value)
    return value


def _no_remote_schema(uri):
    raise NoSuchResource(ref=uri)


_FORMATS = FormatChecker()


@_FORMATS.checks("date-time", raises=ValueError)
def _utc_datetime(value):
    if not isinstance(value, str):
        return True
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z", value):
        return False
    datetime.fromisoformat(value)
    return True


def _is_integer(_checker, value):
    # JSON Schema integers are mathematical integers, including JSON tokens like 1.0.
    return (type(value) is int or
            isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value())


_Validator = validators.extend(Draft202012Validator, type_checker=
                               Draft202012Validator.TYPE_CHECKER.redefine("integer", _is_integer))


@lru_cache(maxsize=1)
def _schema():
    resource = files("rookery.schemas").joinpath("0.1.0/rookery.schema.json")
    schema = json.loads(resource.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


@lru_cache(maxsize=len(RecordKind))
def _validator(kind: RecordKind):
    schema = {key: value for key, value in _schema().items() if key != "$id"}
    schema["oneOf"] = [{"$ref": f"#/$defs/{kind.value}"}]
    return _Validator(schema, format_checker=_FORMATS, registry=Registry(retrieve=_no_remote_schema))


def _freeze(value) -> JsonValue:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class Record:
    """Schema-valid data, not an authenticated approval or verified operation.

    Nested objects and arrays are recursively immutable. Numeric decimals and
    timestamp text retain their input precision; raw_json retains the exact bytes.
    Full per-field domain models and canonical identities remain B01 follow-ups.
    """

    raw_json: bytes = field(repr=False)
    data: Mapping[str, JsonValue] = field(init=False, repr=False)
    __hash__ = None

    def __post_init__(self):
        value = _decode(self.raw_json)
        if not isinstance(value, dict):
            raise ContractError("object_required")
        if value.get("schema_version") != "0.1.0":
            raise ContractError("unsupported_version", ("schema_version",))
        try:
            kind = RecordKind(value.get("kind"))
        except (TypeError, ValueError):
            raise ContractError("unknown_kind", ("kind",)) from None
        failure = best_match(_validator(kind).iter_errors(value))
        if failure is not None:
            raise ContractError(f"schema_{failure.validator}", tuple(failure.absolute_path))
        object.__setattr__(self, "data", _freeze(value))

    @property
    def kind(self) -> RecordKind:
        return RecordKind(self.data["kind"])

    @property
    def id(self) -> RecordId:
        return RecordId(cast(str, self.data["id"]))

    @property
    def schema_version(self) -> Literal["0.1.0"]:
        return "0.1.0"

    @property
    def created_at(self) -> str:
        # Do not silently truncate fractional seconds to datetime's microseconds.
        return cast(str, self.data["created_at"])


def parse_record(raw_json: bytes) -> Record:
    """Parse one in-memory record. This function never opens a user-supplied path."""
    return Record(raw_json)
