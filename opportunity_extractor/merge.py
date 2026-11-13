"""Combine the share files from many students into one de-duplicated master sheet."""
from __future__ import annotations

import glob
import os
from datetime import date, datetime, timedelta
from typing import Dict, List

from .workbook import read_opportunities, same_title_key, write_master


def _files(inputs: List[str]) -> List[str]:
    found = []
    for item in inputs:
        if os.path.isdir(item):
            found += sorted(glob.glob(os.path.join(item, "**", "*.xlsx"), recursive=True))
        else:
            found += sorted(glob.glob(item)) or [item]
    keep = []
    for f in found:
        name = os.path.basename(f).lower()
        if name.startswith(("~$", "do_not_share")) or "do_not_share" in name:
            continue  # Excel lock files and private review files
        keep.append(f)
    return keep


def merge(inputs: List[str], output: str) -> Dict:
    files = [f for f in _files(inputs) if os.path.abspath(f) != os.path.abspath(output)]
    rows, skipped = [], []
    for f in files:
        try:
            rows += read_opportunities(f)
        except Exception as exc:  # not a share file
            skipped.append(f"{os.path.basename(f)} ({exc})")

    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    by_id: Dict[str, int] = {}
    by_title: Dict[str, List[int]] = {}
    for i, row in enumerate(rows):
        for mid in str(row.get("Message-IDs") or "").split():
            if mid in by_id:
                union(i, by_id[mid])
            else:
                by_id[mid] = i
        key = same_title_key(row)
        if key:
            seen = row.get("First seen") if isinstance(row.get("First seen"), datetime) else None
            for j in by_title.get(key, []):
                other = rows[j].get("First seen") if isinstance(rows[j].get("First seen"), datetime) else None
                if not seen or not other or abs(seen - other) <= timedelta(days=60):
                    union(i, j)
            by_title.setdefault(key, []).append(i)

    groups: Dict[int, List[Dict]] = {}
    for i, row in enumerate(rows):
        groups.setdefault(find(i), []).append(row)

    merged = []
    for members in groups.values():
        best = max(members, key=lambda r: (r.get("Last update") or datetime.min, len(str(r.get("Summary") or ""))))
        row = dict(best)
        deadlines = [r["Deadline"] for r in members if isinstance(r.get("Deadline"), date)]
        row["Deadline"] = max(deadlines) if deadlines else None
        sources = sorted({str(s).strip() for r in members for s in str(r.get("Shared by") or "").split(",") if str(s).strip()})
        row["Shared by"] = ", ".join(sources)
        row["Times shared"] = len(sources) or len(members)
        firsts = [r["First seen"] for r in members if isinstance(r.get("First seen"), datetime)]
        lasts = [r["Last update"] for r in members if isinstance(r.get("Last update"), datetime)]
        row["First seen"] = min(firsts) if firsts else row.get("First seen")
        row["Last update"] = max(lasts) if lasts else row.get("Last update")
        row["Message-IDs"] = " ".join(sorted({m for r in members for m in str(r.get("Message-IDs") or "").split()}))
        merged.append(row)

    meta = {"files": len(files) - len(skipped), "rows_in": len(rows), "made": f"{datetime.now():%d %b %Y %H:%M}"}
    write_master(output, merged, meta)
    return {"files": meta["files"], "rows_in": len(rows), "unique": len(merged), "skipped": skipped}
