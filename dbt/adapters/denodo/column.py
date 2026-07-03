from dataclasses import dataclass
from typing import ClassVar, Dict

from dbt.adapters.base.column import Column


@dataclass
class DenodoColumn(Column):
    """Column implementation using Denodo VDP data type names.

    VDP scalar types (Denodo 8): boolean, date, decimal, double, float, int,
    long, text, time, timestamp, timestamptz, intervalday, intervalyearmonth,
    blob, xml.
    """

    TYPE_LABELS: ClassVar[Dict[str, str]] = {
        "STRING": "TEXT",
        "VARCHAR": "TEXT",
        "TIMESTAMP": "TIMESTAMP",
        "FLOAT": "DOUBLE",
        "INTEGER": "INT",
        "BIGINT": "LONG",
        "BOOLEAN": "BOOLEAN",
    }

    @property
    def data_type(self) -> str:
        # VDP's `text` type does not take a length modifier the way
        # varchar(n) does, and numeric precision comes from the source
        # metadata, so render the bare dtype instead of dtype(size).
        return self.dtype

    def is_string(self) -> bool:
        return self.dtype.lower() in ("text", "varchar", "char")

    def is_number(self) -> bool:
        return self.is_integer() or self.is_numeric() or self.is_float()

    def is_integer(self) -> bool:
        return self.dtype.lower() in ("int", "long")

    def is_numeric(self) -> bool:
        return self.dtype.lower() == "decimal"

    def is_float(self) -> bool:
        return self.dtype.lower() in ("float", "double")

    def string_size(self) -> int:
        if not self.is_string():
            from dbt_common.exceptions import DbtRuntimeError

            raise DbtRuntimeError("Called string_size() on non-string field!")
        return int(self.char_size) if self.char_size else 65535

    @classmethod
    def string_type(cls, size: int) -> str:
        return "text"

    @classmethod
    def numeric_type(cls, dtype: str, precision: int, scale: int) -> str:
        # VDP `decimal` does not reliably accept (precision, scale) modifiers
        # through VQL casts, so keep the bare type.
        return "decimal"

    def __repr__(self) -> str:
        return f"<DenodoColumn {self.name} ({self.data_type})>"
