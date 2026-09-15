import importlib.util
from pathlib import Path
from types import ModuleType

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"


def load_validator(kind: str) -> ModuleType:
    path = CONTRACTS / kind / "tests" / "validate_contract.py"
    spec = importlib.util.spec_from_file_location(f"{kind}_contract_validator", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
