"""Check that built distributions contain independent models and no import-only material."""

import sys
import tarfile
import zipfile
from pathlib import Path


def check(names):
    paths = [Path(name) for name in names]
    assert not any("reference" in p.parts or "references" in p.parts for p in paths)
    assert not any(p.name == "device_contracts.json" for p in paths)
    assert not any(p.name == "export_device_contracts.py" for p in paths)
    assert not any("__pycache__" in p.parts or p.name == ".DS_Store" for p in paths)
    models = [
        p for p in paths if "scp_lab" in p.parts and "models" in p.parts and p.suffix == ".json"
    ]
    configs = [
        p for p in paths if "scp_lab" in p.parts and "devices" in p.parts and p.suffix == ".json"
    ]
    assert len(models) == 46, models
    assert len(configs) == 48, configs


directory = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
wheels, sources = list(directory.glob("*.whl")), list(directory.glob("*.tar.gz"))
assert wheels and sources, "Build both wheel and source distribution first"
for artifact in wheels + sources:
    if artifact.suffix == ".whl":
        with zipfile.ZipFile(artifact) as archive:
            check(archive.namelist())
    else:
        with tarfile.open(artifact) as archive:
            names = archive.getnames()
            check(names)
            assert any(name.endswith("docs/zh-CN/backends.md") for name in names)
            assert any(
                name.endswith(
                    "examples/adapters/example_lab/plate_reader/models/example_reader.json"
                )
                for name in names
            )
    print(f"Release layout verified: {artifact.name}")
