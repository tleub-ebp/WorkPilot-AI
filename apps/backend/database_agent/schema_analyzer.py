"""
Schema Analyzer — Introspect current database schema.

Supports PostgreSQL, MySQL/MariaDB, SQLite, SQL Server via connection
string auto-detection.  Returns a structured representation of tables,
columns, indexes and constraints.

100% algorithmic — no LLM dependency.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DatabaseEngine(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    SQLSERVER = "sqlserver"
    UNKNOWN = "unknown"


@dataclass
class ColumnInfo:
    """Describes a single column in a table."""

    name: str
    data_type: str
    nullable: bool = True
    default: str | None = None
    is_primary_key: bool = False
    is_unique: bool = False
    foreign_key: str | None = None  # "table.column" reference
    max_length: int | None = None

    @property
    def is_text_type(self) -> bool:
        upper = self.data_type.upper()
        return any(t in upper for t in ("VARCHAR", "TEXT", "CHAR", "NVARCHAR", "CLOB"))

    @property
    def is_numeric_type(self) -> bool:
        upper = self.data_type.upper()
        return any(
            t in upper
            for t in (
                "INT",
                "FLOAT",
                "DECIMAL",
                "NUMERIC",
                "REAL",
                "DOUBLE",
                "SERIAL",
                "BIGSERIAL",
            )
        )


@dataclass
class IndexInfo:
    """Describes an index on a table."""

    name: str
    columns: list[str]
    is_unique: bool = False
    is_primary: bool = False


@dataclass
class ConstraintInfo:
    """Describes a constraint (FK, check, etc.)."""

    name: str
    constraint_type: str  # "foreign_key", "check", "unique"
    columns: list[str] = field(default_factory=list)
    reference_table: str | None = None
    reference_columns: list[str] = field(default_factory=list)


@dataclass
class TableInfo:
    """Full description of a database table."""

    name: str
    schema: str = "public"
    columns: list[ColumnInfo] = field(default_factory=list)
    indexes: list[IndexInfo] = field(default_factory=list)
    constraints: list[ConstraintInfo] = field(default_factory=list)
    estimated_rows: int = 0

    def get_column(self, name: str) -> ColumnInfo | None:
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def get_primary_keys(self) -> list[ColumnInfo]:
        return [c for c in self.columns if c.is_primary_key]

    def get_foreign_keys(self) -> list[ConstraintInfo]:
        return [c for c in self.constraints if c.constraint_type == "foreign_key"]


class SchemaAnalyzer:
    """Analyze database schema from connection metadata or SQL DDL.

    For offline/local analysis, ``analyze_ddl()`` parses CREATE TABLE
    statements without requiring a live database connection.
    """

    @staticmethod
    def detect_engine(connection_string: str) -> DatabaseEngine:
        """Auto-detect database engine from a connection string."""
        cs = connection_string.lower()
        if "postgresql" in cs or "postgres" in cs or cs.startswith("pg:"):
            return DatabaseEngine.POSTGRESQL
        if "mysql" in cs or "mariadb" in cs:
            return DatabaseEngine.MYSQL
        if "sqlite" in cs or cs.endswith(".db") or cs.endswith(".sqlite3"):
            return DatabaseEngine.SQLITE
        if "sqlserver" in cs or "mssql" in cs:
            return DatabaseEngine.SQLSERVER
        return DatabaseEngine.UNKNOWN

    def analyze_ddl(self, ddl: str) -> list[TableInfo]:
        """Parse CREATE TABLE statements and return structured TableInfo list.

        This is a simplified parser for common SQL DDL syntax.
        """
        tables: list[TableInfo] = []
        create_pattern = re.compile(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\"?(\w+)\"?\.)?\"?(\w+)\"?\s*\((.*?)\);",
            re.IGNORECASE | re.DOTALL,
        )

        for match in create_pattern.finditer(ddl):
            schema = match.group(1) or "public"
            table_name = match.group(2)
            body = match.group(3)
            columns = self._parse_columns(body)
            tables.append(TableInfo(name=table_name, schema=schema, columns=columns))

        return tables

    def classify_change(self, table: TableInfo, change_description: str) -> str:
        """Classify a schema change as 'non_destructive' or 'destructive'.

        Simple heuristic based on keywords.
        """
        desc = change_description.lower()

        destructive_keywords = [
            "rename column",
            "rename table",
            "change type",
            "alter type",
            "drop column",
            "drop table",
            "split table",
            "merge table",
            "remove column",
            "delete column",
        ]
        for kw in destructive_keywords:
            if kw in desc:
                return "destructive"

        non_destructive_keywords = [
            "add column",
            "add index",
            "add table",
            "create table",
            "create index",
            "add constraint",
            "add nullable",
        ]
        for kw in non_destructive_keywords:
            if kw in desc:
                return "non_destructive"

        return "destructive"  # default to safe assumption

    def _parse_columns(self, body: str) -> list[ColumnInfo]:
        """Parse column definitions from a CREATE TABLE body."""
        columns: list[ColumnInfo] = []
        # Split by comma but respect parentheses
        parts = self._split_column_defs(body)

        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Skip constraints at the table level
            upper = part.upper().lstrip()
            if upper.startswith(
                ("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK", "CONSTRAINT", "INDEX")
            ):
                continue

            col = self._parse_single_column(part)
            if col:
                columns.append(col)

        return columns

    @staticmethod
    def _split_column_defs(body: str) -> list[str]:
        """Split column definitions by comma, respecting parentheses."""
        parts = []
        depth = 0
        current = []
        for char in body:
            if char == "(":
                depth += 1
                current.append(char)
            elif char == ")":
                depth -= 1
                current.append(char)
            elif char == "," and depth == 0:
                parts.append("".join(current))
                current = []
            else:
                current.append(char)
        if current:
            parts.append("".join(current))
        return parts

    @staticmethod
    def _parse_single_column(definition: str) -> ColumnInfo | None:
        """Parse a single column definition string."""
        # Match: column_name TYPE[(len)] [NOT NULL] [DEFAULT x] [PRIMARY KEY] [REFERENCES ...]
        pattern = re.compile(
            r"\"?(\w+)\"?\s+(\w+(?:\([^)]*\))?)"
            r"(.*)",
            re.IGNORECASE,
        )
        match = pattern.match(definition.strip())
        if not match:
            return None

        name = match.group(1)
        data_type = match.group(2)
        rest_raw = match.group(3)
        rest = rest_raw.upper()

        nullable = "NOT NULL" not in rest
        is_pk = "PRIMARY KEY" in rest
        is_unique = "UNIQUE" in rest

        # Extract default
        default = None
        default_match = re.search(r"DEFAULT\s+(\S+)", rest_raw, re.IGNORECASE)
        if default_match:
            default = default_match.group(1).strip("'\"")

        # Extract foreign key reference (use original case)
        fk = None
        ref_match = re.search(
            r"REFERENCES\s+\"?(\w+)\"?\s*\(\"?(\w+)\"?\)", rest_raw, re.IGNORECASE
        )
        if ref_match:
            fk = f"{ref_match.group(1)}.{ref_match.group(2)}"

        # Extract max_length
        max_length = None
        len_match = re.search(r"\((\d+)\)", data_type)
        if len_match:
            max_length = int(len_match.group(1))

        return ColumnInfo(
            name=name,
            data_type=data_type,
            nullable=nullable,
            default=default,
            is_primary_key=is_pk,
            is_unique=is_unique,
            foreign_key=fk,
            max_length=max_length,
        )
