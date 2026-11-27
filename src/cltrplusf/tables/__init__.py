"""Financial tables read from the words a PDF prints: every number kept, header lines apart,
wrapped labels joined, and rows nested into sections checked by the table's own arithmetic."""

from cltrplusf.tables.model import Cell, Piece, Row, Table
from cltrplusf.tables.read import keys, read_table, read_tables

__all__ = ["Cell", "Piece", "Row", "Table", "keys", "read_table", "read_tables"]
