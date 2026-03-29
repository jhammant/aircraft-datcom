"""
DATCOM input file parser.

Reads the classic DATCOM namelist-style input format (``$NAME ... $``)
used by the FORTRAN program.  Each namelist group is parsed into a
Python dictionary.  Control cards (CASEID, NEXT CASE, SAVE, BUILD,
TRIM, DAMP, DIM, DUMP, NACA-*) are returned as separate entries.

Input format
------------
The DATCOM input is a sequence of FORTRAN namelist groups and control
cards::

    $FLTCON NMACH=1.0, MACH(1)=0.60, NALPHA=5., ALSCHD(1)=-2.,0.,2.,4.,8.$
    $OPTINS SREF=8.85, CBARR=2.46, BLREF=4.28$
    $SYNTHS XCG=4.14, ZCG=-0.20$
    $BODY NX=10.0, X(1)=0.0, 0.258, ...$
    CASEID MY ANALYSIS CASE 1
    SAVE
    NEXT CASE

Namelist names recognized:
    FLTCON, OPTINS, SYNTHS, BODY, WGPLNF, WGSCHR, HTPLNF, HTSCHR,
    VTPLNF, VTSCHR, SYMFLP, ASYFLP, PROPWR, JETPWR, TVTPAN, LARWB,
    TRNJET, HYPEFF, EXPR01, EXPR02
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DatcomCase:
    """One analysis case parsed from a DATCOM input file.

    Attributes
    ----------
    case_id : str
        Case identifier string.
    namelists : dict[str, dict[str, object]]
        Parsed namelist groups.  Keys are group names (e.g. ``'FLTCON'``),
        values are dicts mapping variable names to values (float, list of
        float, bool, or str).
    controls : list[str]
        Control cards (SAVE, TRIM, DAMP, BUILD, etc.).
    naca : list[str]
        NACA airfoil specification cards.
    dim : str
        Dimensional system (``'FT'`` or ``'M'``).
    """
    case_id: str = ""
    namelists: dict = field(default_factory=dict)
    controls: list = field(default_factory=list)
    naca: list = field(default_factory=list)
    dim: str = "FT"


def _parse_namelist_body(body: str) -> dict[str, object]:
    """Parse the body of a single namelist group into a dict.

    Handles:
    - Simple scalars: ``SREF=8.85``
    - Array elements: ``MACH(1)=0.60,0.80,1.20``
    - Booleans: ``VERTUP=.TRUE.``
    - Repeated values: ``2*0.141`` (FORTRAN repeat notation)
    """
    result: dict[str, object] = {}

    # Normalize: remove newlines, collapse spaces
    body = body.replace("\n", " ").replace("\r", " ")
    # Remove trailing $ if present
    body = body.rstrip().rstrip("$").strip()

    # Split on commas, but respect that commas inside values are separators
    # Strategy: split on `name=` boundaries
    # Find all assignments: name=value or name(index)=value
    # Pattern: word (optional (digits)) = value_stuff
    tokens = re.split(r',\s*(?=[A-Za-z])', body)

    current_name = None
    current_values: list = []

    for token in tokens:
        token = token.strip()
        if not token:
            continue

        # Check for assignment
        m = re.match(r'([A-Za-z]\w*)(?:\(\d+\))?\s*=\s*(.*)', token)
        if m:
            # Save previous
            if current_name is not None:
                _store(result, current_name, current_values)

            current_name = m.group(1).upper()
            val_str = m.group(2).strip()
            current_values = _parse_values(val_str)
        else:
            # Continuation values
            current_values.extend(_parse_values(token))

    # Save last
    if current_name is not None:
        _store(result, current_name, current_values)

    return result


def _parse_values(s: str) -> list:
    """Parse a comma/space-separated value string into a list."""
    values = []
    # Split on commas and spaces
    parts = re.split(r'[,\s]+', s.strip())
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Boolean
        if p.upper() in (".TRUE.", ".FALSE."):
            values.append(p.upper() == ".TRUE.")
        # FORTRAN repeat: N*value
        elif "*" in p:
            m = re.match(r'(\d+)\*(.+)', p)
            if m:
                count = int(m.group(1))
                val = _to_number(m.group(2))
                values.extend([val] * count)
        else:
            values.append(_to_number(p))
    return values


def _to_number(s: str):
    """Convert a string to float, handling FORTRAN D-exponent notation."""
    s = s.strip().upper().replace("D", "E")
    try:
        return float(s)
    except ValueError:
        return s


def _store(result: dict, name: str, values: list):
    """Store parsed values: scalar if single, list if multiple."""
    if len(values) == 1:
        result[name] = values[0]
    elif len(values) > 1:
        result[name] = values
    # empty list → skip


def parse_datcom_input(text: str) -> list[DatcomCase]:
    """Parse a complete DATCOM input file into a list of cases.

    Parameters
    ----------
    text : str
        Contents of a DATCOM input file.

    Returns
    -------
    list[DatcomCase]
        One :class:`DatcomCase` per ``NEXT CASE`` boundary (plus the last
        case).
    """
    cases: list[DatcomCase] = []
    current = DatcomCase()

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # --- Namelist group: starts with $ ---
        if stripped.startswith("$"):
            # Collect until closing $
            nl_text = stripped[1:]  # remove leading $
            # Check if the closing $ is on this line
            while nl_text.count("$") < 1 and i + 1 < len(lines):
                i += 1
                nl_text += " " + lines[i].strip()

            # Extract name and body
            # Format: $NAME var=val, var=val$
            # or:     $NAME var=val, var=val $
            m = re.match(r'(\w+)\s+(.*)', nl_text)
            if m:
                nl_name = m.group(1).upper()
                nl_body = m.group(2)
                # Remove trailing $
                if "$" in nl_body:
                    nl_body = nl_body[:nl_body.rindex("$")]
                parsed = _parse_namelist_body(nl_body)

                # Merge into existing namelist of same name (DATCOM allows
                # multiple $FLTCON groups etc.)
                if nl_name in current.namelists:
                    current.namelists[nl_name].update(parsed)
                else:
                    current.namelists[nl_name] = parsed

            i += 1
            continue

        # --- Control cards ---
        upper = stripped.upper()

        if upper.startswith("CASEID"):
            current.case_id = stripped[6:].strip()
        elif upper.startswith("NACA-"):
            current.naca.append(stripped)
        elif upper.startswith("DIM"):
            parts = stripped.split()
            if len(parts) > 1:
                current.dim = parts[1].upper()
        elif upper == "NEXT CASE":
            cases.append(current)
            # Start new case inheriting namelists (DATCOM saves state)
            new = DatcomCase()
            # Deep copy namelists for inheritance
            for k, v in current.namelists.items():
                new.namelists[k] = dict(v)
            new.dim = current.dim
            current = new
        elif upper in ("SAVE", "TRIM", "DAMP", "BUILD", "PART", "PLOT"):
            current.controls.append(upper)
        elif upper.startswith("DUMP"):
            current.controls.append(stripped.upper())
        else:
            # Unknown control card - store as-is
            current.controls.append(stripped)

        i += 1

    # Append final case
    if current.case_id or current.namelists:
        cases.append(current)

    return cases


def parse_datcom_file(path: str | Path) -> list[DatcomCase]:
    """Parse a DATCOM input file from disk.

    Parameters
    ----------
    path : str or Path
        Path to the input file.

    Returns
    -------
    list[DatcomCase]
    """
    return parse_datcom_input(Path(path).read_text(encoding="ascii", errors="replace"))
