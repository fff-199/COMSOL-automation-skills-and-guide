from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None  # type: ignore


DEFAULT_MODULES = [
    "Electrochemistry_Module",
    "Fuel_Cell_and_Electrolyzer_Module",
    "Electrodeposition_Module",
    "Corrosion_Module",
    "Battery_Design_Module",
    "CFD_Module",
    "Microfluidics_Module",
    "Porous_Media_Flow_Module",
    "Pipe_Flow_Module",
    "COMSOL_Multiphysics",
]


@dataclass
class ExampleRecord:
    module: str
    category: str
    name: str
    path: Path

    def as_dict(self) -> dict[str, str]:
        return {
            "module": self.module,
            "category": self.category,
            "name": self.name,
            "path": str(self.path),
        }


def discover_comsol_root() -> Path:
    env_value = None
    for key in ("COMSOL_ROOT", "COMSOL_HOME"):
        value = os.environ.get(key)
        if value:
            env_value = Path(value)
            break
    if env_value and (env_value / "applications").exists():
        return env_value
    root = _registry_root()
    if root:
        return root
    for candidate in _common_roots():
        if (candidate / "applications").exists():
            return candidate
    raise SystemExit("Could not locate COMSOL Multiphysics root. Set COMSOL_ROOT first.")


def _registry_root() -> Path | None:
    if winreg is None:
        return None
    locations = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\COMSOL63"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\COMSOL63"),
    ]
    for hive, subkey in locations:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                uninstall, _ = winreg.QueryValueEx(key, "UninstallString")
        except OSError:
            continue
        match = re.search(r"([A-Za-z]:\\[^\"\s]+?\\bin\\win64\\setup\.exe)", str(uninstall))
        if match:
            return Path(match.group(1)).parents[2]
    return None


def _common_roots() -> list[Path]:
    candidates: list[Path] = []
    for drive in ("C", "D", "E", "F", "G"):
        root = Path(f"{drive}:\\")
        if not root.exists():
            continue
        for base in (root / "Program Files", root):
            candidates.extend(_scan_for_comsol(base))
    return candidates


def _scan_for_comsol(base: Path) -> list[Path]:
    roots: list[Path] = []
    try:
        children = list(base.iterdir())
    except OSError:
        return roots

    for child in children:
        if not child.is_dir() or "COMSOL" not in child.name.upper():
            continue
        for candidate in (child, child / "Multiphysics"):
            if (candidate / "applications").exists():
                roots.append(candidate)
        try:
            grandchildren = list(child.iterdir())
        except OSError:
            continue
        for grandchild in grandchildren:
            if grandchild.is_dir() and (grandchild / "applications").exists():
                roots.append(grandchild)
    return roots


def collect_examples(root: Path, modules: list[str], include_geom: bool) -> list[ExampleRecord]:
    records: list[ExampleRecord] = []
    applications = root / "applications"
    for module in modules:
        module_dir = applications / module
        if not module_dir.exists():
            continue
        for path in sorted(module_dir.rglob("*.mph")):
            if not include_geom and path.stem.endswith("_geom_sequence"):
                continue
            rel = path.relative_to(applications)
            parts = rel.parts
            category = parts[1] if len(parts) > 2 else "root"
            records.append(
                ExampleRecord(
                    module=parts[0],
                    category=category,
                    name=path.stem,
                    path=path,
                )
            )
    return records


def filter_examples(records: list[ExampleRecord], keywords: list[str]) -> list[ExampleRecord]:
    if not keywords:
        return records
    lowered = [keyword.lower() for keyword in keywords]
    filtered: list[ExampleRecord] = []
    for record in records:
        haystack = f"{record.module} {record.category} {record.name} {record.path}".lower()
        if all(keyword in haystack for keyword in lowered):
            filtered.append(record)
    return filtered


def print_table(records: list[ExampleRecord], limit: int) -> None:
    records = records[:limit]
    if not records:
        print("No matching examples found.")
        return
    module_w = max(len("module"), *(len(r.module) for r in records))
    category_w = max(len("category"), *(len(r.category) for r in records))
    name_w = max(len("name"), *(len(r.name) for r in records))
    print(f"{'module':<{module_w}}  {'category':<{category_w}}  {'name':<{name_w}}  path")
    print(f"{'-' * module_w}  {'-' * category_w}  {'-' * name_w}  ----")
    for record in records:
        print(
            f"{record.module:<{module_w}}  {record.category:<{category_w}}  {record.name:<{name_w}}  {record.path}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Find local COMSOL electrochemistry and flow examples.")
    parser.add_argument("--root", type=Path, default=None, help="Override COMSOL Multiphysics root")
    parser.add_argument(
        "--module",
        action="append",
        default=[],
        help="Module folder under applications/. Repeatable. Default is the electrochem+flow set.",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="Case-insensitive keyword filter applied to module/category/name/path. Repeatable.",
    )
    parser.add_argument("--include-geom-sequence", action="store_true", help="Include *_geom_sequence.mph")
    parser.add_argument("--limit", type=int, default=80, help="Maximum rows to print")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    root = args.root.resolve() if args.root else discover_comsol_root()
    modules = args.module or DEFAULT_MODULES
    records = collect_examples(root, modules, include_geom=args.include_geom_sequence)
    records = filter_examples(records, args.keyword)
    if args.json:
        print(json.dumps([record.as_dict() for record in records[: args.limit]], ensure_ascii=False, indent=2))
    else:
        print(f"COMSOL root: {root}")
        print_table(records, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
