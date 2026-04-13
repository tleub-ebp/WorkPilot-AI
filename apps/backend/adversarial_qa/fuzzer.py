"""
Fuzzer — Generate malformed/boundary inputs for testing.

Produces inputs that test boundaries, type coercion, encoding, and
overflow scenarios.  100% algorithmic — no LLM dependency.
"""

from __future__ import annotations

import logging
import random
import string
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class FuzzStrategy(str, Enum):
    BOUNDARY = "boundary"  # Min/max values, empty, null
    TYPE_COERCION = "type_coercion"  # Wrong types
    ENCODING = "encoding"  # Unicode, UTF-8 edge cases
    OVERFLOW = "overflow"  # Huge strings, deep nesting
    FORMAT = "format"  # Malformed JSON, XML, SQL
    SPECIAL_CHARS = "special_chars"  # Quotes, backslashes, null bytes


@dataclass
class FuzzResult:
    """A single fuzz test case."""

    strategy: FuzzStrategy
    input_value: Any
    description: str
    field_name: str = ""
    expected_behavior: str = "should handle gracefully"
    is_crash: bool = False
    error_message: str = ""


class Fuzzer:
    """Generate fuzz inputs for function/API testing.

    Usage::

        fuzzer = Fuzzer(seed=42)
        cases = fuzzer.generate_for_string("username", max_length=50)
        for case in cases:
            # Feed case.input_value into the function under test
            ...
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def generate_for_string(
        self, field_name: str = "input", max_length: int = 255
    ) -> list[FuzzResult]:
        """Generate fuzz cases for a string input."""
        cases: list[FuzzResult] = []

        # Boundary
        cases.append(
            FuzzResult(
                strategy=FuzzStrategy.BOUNDARY,
                input_value="",
                description="Empty string",
                field_name=field_name,
            )
        )
        cases.append(
            FuzzResult(
                strategy=FuzzStrategy.BOUNDARY,
                input_value=" ",
                description="Single space",
                field_name=field_name,
            )
        )
        cases.append(
            FuzzResult(
                strategy=FuzzStrategy.BOUNDARY,
                input_value="a" * max_length,
                description=f"Exact max length ({max_length})",
                field_name=field_name,
            )
        )
        cases.append(
            FuzzResult(
                strategy=FuzzStrategy.BOUNDARY,
                input_value="a" * (max_length + 1),
                description=f"Over max length ({max_length + 1})",
                field_name=field_name,
            )
        )

        # Special chars
        for char, name in [
            ("'", "single quote"),
            ('"', "double quote"),
            ("\\", "backslash"),
            ("\0", "null byte"),
            ("\n", "newline"),
            ("\t", "tab"),
            ("<script>alert(1)</script>", "XSS payload"),
        ]:
            cases.append(
                FuzzResult(
                    strategy=FuzzStrategy.SPECIAL_CHARS,
                    input_value=char,
                    description=f"Special character: {name}",
                    field_name=field_name,
                )
            )

        # Encoding
        cases.append(
            FuzzResult(
                strategy=FuzzStrategy.ENCODING,
                input_value="\u202e\u0041\u0042",
                description="Right-to-left override",
                field_name=field_name,
            )
        )
        cases.append(
            FuzzResult(
                strategy=FuzzStrategy.ENCODING,
                input_value="é à ü ñ ß",
                description="Accented characters",
                field_name=field_name,
            )
        )
        cases.append(
            FuzzResult(
                strategy=FuzzStrategy.ENCODING,
                input_value="🔥🎉💀",
                description="Emoji characters",
                field_name=field_name,
            )
        )
        cases.append(
            FuzzResult(
                strategy=FuzzStrategy.ENCODING,
                input_value="\xff\xfe",
                description="Invalid UTF-8 bytes",
                field_name=field_name,
            )
        )

        # Overflow
        cases.append(
            FuzzResult(
                strategy=FuzzStrategy.OVERFLOW,
                input_value="x" * 10_000,
                description="Very long string (10K)",
                field_name=field_name,
            )
        )
        cases.append(
            FuzzResult(
                strategy=FuzzStrategy.OVERFLOW,
                input_value="x" * 1_000_000,
                description="Huge string (1M)",
                field_name=field_name,
            )
        )

        return cases

    def generate_for_number(
        self, field_name: str = "value", min_val: int = 0, max_val: int = 2**31 - 1
    ) -> list[FuzzResult]:
        """Generate fuzz cases for numeric input."""
        cases: list[FuzzResult] = []

        for val, desc in [
            (0, "Zero"),
            (-1, "Negative one"),
            (min_val, f"Min value ({min_val})"),
            (max_val, f"Max value ({max_val})"),
            (max_val + 1, f"Over max ({max_val + 1})"),
            (min_val - 1, f"Under min ({min_val - 1})"),
            (2**63, "Very large int (2^63)"),
            (-(2**63), "Very negative int (-2^63)"),
        ]:
            cases.append(
                FuzzResult(
                    strategy=FuzzStrategy.BOUNDARY,
                    input_value=val,
                    description=desc,
                    field_name=field_name,
                )
            )

        # Type coercion
        for val, desc in [
            ("not_a_number", "String instead of number"),
            (None, "None/null"),
            (float("inf"), "Infinity"),
            (float("-inf"), "Negative infinity"),
            (float("nan"), "NaN"),
            (3.14, "Float instead of int"),
        ]:
            cases.append(
                FuzzResult(
                    strategy=FuzzStrategy.TYPE_COERCION,
                    input_value=val,
                    description=desc,
                    field_name=field_name,
                )
            )

        return cases

    def generate_for_json(self, field_name: str = "payload") -> list[FuzzResult]:
        """Generate malformed JSON payloads."""
        cases: list[FuzzResult] = []

        malformed = [
            ("", "Empty string"),
            ("{", "Unclosed brace"),
            ('{"key": }', "Missing value"),
            ('{"key": "value",}', "Trailing comma"),
            ("null", "Null literal"),
            ("[]", "Empty array"),
            ('{"a": ' * 100 + '"x"' + "}" * 100, "Deeply nested (100 levels)"),
            ('{"key": "' + "x" * 10_000 + '"}', "Very long value"),
        ]

        for payload, desc in malformed:
            cases.append(
                FuzzResult(
                    strategy=FuzzStrategy.FORMAT,
                    input_value=payload,
                    description=f"Malformed JSON: {desc}",
                    field_name=field_name,
                )
            )

        return cases

    def generate_random_string(self, length: int = 100) -> str:
        """Generate a random string with mixed character types."""
        chars = string.ascii_letters + string.digits + string.punctuation + " \t\n"
        return "".join(self._rng.choice(chars) for _ in range(length))
