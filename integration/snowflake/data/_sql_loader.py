"""Internal SQL file loading utilities.

This module provides utilities for loading and formatting SQL queries
from the sql/ directory. It is intended for internal use within the
data package only.
"""

from pathlib import Path

_SQL_DIR = Path(__file__).parent / "sql"


def load_sql(path: str, **kwargs: str) -> str:
    """Load SQL query from file with optional parameter substitution.

    Loads SQL content from data/sql/{path} and applies string formatting
    if keyword arguments are provided.

    Args:
        path: Relative path to SQL file within data/sql/ directory
            (e.g., "preparation/analyze_stores.sql").
        **kwargs: Named parameters to substitute in the SQL using .format().

    Raises:
        FileNotFoundError: If the SQL file does not exist.
        KeyError: If a placeholder in the SQL file is not provided in kwargs.
    """
    sql_file: Path = _SQL_DIR / path
    content: str = sql_file.read_text()

    if kwargs:
        return content.format(**kwargs)

    return content
