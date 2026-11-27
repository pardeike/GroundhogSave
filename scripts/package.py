#!/usr/bin/env python3
"""Build a local package without rewriting the frozen root payload."""

import hashlib
import contextlib
import csv
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent
PUBLISHED_URL = "https://github.com/pardeike/GroundhogSave/releases/download/v1.0.0.0/GroundhogSave.zip"
PUBLISHED_SHA256 = "51a9ab83bae1f7dd2f4cc0fce2ad96dfec0d75de7e9169394346bb8e597a49f0"
# These hashes describe the original checkout, which differs from the release.
FROZEN_ROOT = {
    "Assemblies/CrossPromotion.dll": "12d0a079d9a7de569986641610f7aeb354ab85f6ff08c288c1c30c5effdac733",
    "Assemblies/GroundhogSave.dll": "b6aeb8cea80533c23b6876c6817096988f7df88ad94b53be561dd31957cb1e7f",
    "Languages/English/Keyed/Text.xml": "96b39654799863d766fedeefef5b89b61b4dfe5ed793e41b35d2fce9fefedaf0",
    "Languages/German/Keyed/Text.xml": "fef90f80a73bd45871454a6b8b40362313f91dad5573c707286504fda48be030",
}
PUBLISHED_FILES = (*FROZEN_ROOT, "About/ModIcon.png", "About/Preview.png")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def files_under(folder):
    return {
        p.relative_to(ROOT).as_posix(): p.read_bytes()
        for p in (ROOT / folder).rglob("*")
        if p.is_file() and p.name != ".DS_Store" and not p.name.startswith("._")
    }


def verify_legacy():
    actual = files_under("Assemblies") | files_under("Languages")
    require(set(actual) == set(FROZEN_ROOT), "The frozen root payload has missing or additional files.")
    for name, expected in FROZEN_ROOT.items():
        require(hashlib.sha256(actual[name]).hexdigest() == expected, f"Frozen root file changed: {name}")


def published_payload():
    archive = ROOT / ".builds/published-v1.0.0.0.zip"
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(PUBLISHED_URL, timeout=60) as response:
            data = response.read()
        require(hashlib.sha256(data).hexdigest() == PUBLISHED_SHA256, "Published archive checksum mismatch.")
        archive.write_bytes(data)
    require(hashlib.sha256(archive.read_bytes()).hexdigest() == PUBLISHED_SHA256,
            f"Published archive checksum mismatch. Remove {archive} and retry.")
    with ZipFile(archive) as release:
        return {name: release.read(name) for name in PUBLISHED_FILES}


def package():
    verify_legacy()
    published = published_payload()
    current = files_under("1.7")
    dlls = {name for name in current if name.endswith(".dll")}
    require(dlls == {"1.7/Assemblies/GroundhogSave.dll", "1.7/Assemblies/CrossPromotion.dll"},
            "Build 1.7 first. Its only runtime DLLs must be GroundhogSave.dll and CrossPromotion.dll.")
    # Explicitly include runtime files. Debug symbols and development files never enter the ZIP.
    current = {name: data for name, data in current.items()
               if name in dlls or name.startswith("1.7/Languages/") and name.endswith(".xml")}
    for name in ("1.7/Languages/English/Keyed/Text.xml", "1.7/Languages/German/Keyed/Text.xml"):
        require(name in current, f"Missing 1.7 language resource: {name}")

    version = ET.parse(ROOT / "Directory.Build.props").findtext(".//ModVersion")
    about = ET.parse(ROOT / "About/About.xml")
    manifest = ET.parse(ROOT / "About/Manifest.xml")
    require(about.findtext("packageId") == "brrainz.groundhogsave", "Unexpected package ID.")
    require(about.findtext("modVersion") == manifest.findtext("version") == version,
            "About.xml and Manifest.xml must match ModVersion.")
    require([e.text for e in about.findall("supportedVersions/li")] == ["1.6", "1.7"],
            "About.xml must advertise only RimWorld 1.6 and 1.7.")
    require([e.text for e in manifest.findall("targetVersions/li")] == ["1.6.0", "1.7.0"],
            "Manifest.xml must target RimWorld 1.6 and 1.7.")
    load_folders = ET.parse(ROOT / "LoadFolders.xml")
    require([e.text for e in load_folders.findall("v1.6/li")] == ["/"], "1.6 must load only the root.")
    require([e.text for e in load_folders.findall("v1.7/li")] == ["1.7"], "1.7 must load only 1.7/.")

    payload = published | current
    for name in ("About/About.xml", "About/Manifest.xml", "About/PublishedFileId.txt",
                 "LoadFolders.xml", "LICENSE", "README.md"):
        payload[name] = (ROOT / name).read_bytes()
    destination = ROOT / ".builds/package"
    stage = destination / "GroundhogSave"
    destination.mkdir(parents=True, exist_ok=True)
    if stage.exists():
        shutil.rmtree(stage)
    for name, data in payload.items():
        path = stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    output = destination / "GroundhogSave.zip"
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name in sorted(payload):
            archive.write(stage / name, name)
    with ZipFile(output) as archive:
        actual = {name: archive.read(name) for name in archive.namelist()}
    require(actual == payload, "ZIP contents differ from the staged payload.")
    require(all(actual[name] == data for name, data in published.items()), "Packaged 1.6 payload changed.")
    verify_legacy()
    return payload, published, output


def read_tree(root):
    files = {}
    for path in root.rglob("*"):
        require(not path.is_symlink(), f"Refusing symlink in installed payload: {path}")
        if path.is_file() and path.name != ".DS_Store" and not path.name.startswith("._"):
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def deploy_root(value):
    logical = Path(os.path.abspath(os.path.expanduser(value)))
    require(logical.is_dir(), f"Mods directory does not exist: {logical}")
    physical = logical.resolve(strict=True)
    require(logical.name.casefold() == physical.name.casefold() == "mods",
            "RIMWORLD_MOD_DIR must logically and physically name an existing Mods directory.")
    destination = physical / "GroundhogSave"
    require(not destination.is_symlink(), f"Refusing symlinked mod destination: {destination}")
    require(not destination.exists() or destination.is_dir(), f"Not a mod directory: {destination}")
    require(destination != ROOT and destination not in ROOT.parents, "Deployment would overwrite the source checkout.")
    require(not (physical / "GroundhogSave.zip").is_symlink(), "Refusing symlinked ZIP destination.")
    return physical, destination


def ensure_stopped():
    command = ["tasklist", "/FO", "CSV", "/NH"] if os.name == "nt" else ["ps", "-A", "-o", "pid=,comm="]
    result = subprocess.run(command, capture_output=True, text=True)
    require(result.returncode == 0, "Cannot determine whether RimWorld is running. Deployment refused.")
    if os.name == "nt":
        names = [row[0] for row in csv.reader(result.stdout.splitlines()) if row]
    else:
        names = [line.strip().split(None, 1)[1] for line in result.stdout.splitlines() if len(line.strip().split(None, 1)) == 2]
    pattern = r"RimWorld(?:Win64|Linux)?(?:\.exe)?|RimWorld by Ludeon Studios"
    require(not any(re.fullmatch(pattern, Path(name).name, re.IGNORECASE) for name in names),
            "RimWorld is running. Deployment refused. This workflow never stops the game.")


def verify_installed_legacy(destination, published):
    if not destination.exists():
        return
    installed = read_tree(destination)
    legacy = {name: data for name, data in installed.items()
              if name in published or name.startswith(("Assemblies/", "Languages/"))}
    for name, expected in published.items():
        require(legacy.get(name) == expected,
                f"Installed frozen 1.6 file differs or is missing: {destination / name}. No files were changed.")
    require(set(legacy) == set(published), "Installed frozen 1.6 payload has additional files. No files were changed.")


@contextlib.contextmanager
def deployment_lock(mods):
    path = mods / ".GroundhogSave.deploy.lock"
    require(not path.is_symlink(), f"Refusing symlinked deployment lock: {path}")
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Closing the handle releases the lock, including after cancellation.
        yield


def check_deploy(value):
    mods, destination = deploy_root(value)
    ensure_stopped()
    verify_installed_legacy(destination, published_payload())


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def deploy(value):
    mods, destination = deploy_root(value)
    with deployment_lock(mods):
        ensure_stopped()
        verify_installed_legacy(destination, published_payload())
        payload, published, archive = package()
        installed = read_tree(destination) if destination.exists() else {}
        unexpected = set(installed) - set(payload)
        require(not unexpected, f"Installed payload has unexpected files: {', '.join(sorted(unexpected))}. No files were changed.")
        ensure_stopped()
        if not destination.exists():
            # Install the complete initial payload in one directory rename.
            with tempfile.TemporaryDirectory(prefix=".GroundhogSave-", dir=mods) as temporary:
                stage = Path(temporary) / "GroundhogSave"
                for name, data in payload.items():
                    path = stage / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                stage.rename(destination)
        else:
            for name, data in payload.items():
                if name not in published and installed.get(name) != data:
                    atomic_write(destination / name, data)
        require(read_tree(destination) == payload, "Installed files differ from the verified package.")
        verify_installed_legacy(destination, published)
        atomic_write(mods / "GroundhogSave.zip", archive.read_bytes())
        with ZipFile(mods / "GroundhogSave.zip") as deployed_zip:
            require({name: deployed_zip.read(name) for name in deployed_zip.namelist()} == read_tree(destination),
                    "Deployment ZIP differs from installed files.")
        verify_legacy()


if __name__ == "__main__":
    try:
        action = sys.argv[1:]
        if action == ["verify-legacy"]:
            verify_legacy()
        elif action == ["package"]:
            package()
        elif len(action) == 2 and action[0] == "check-deploy":
            check_deploy(action[1])
        elif len(action) == 2 and action[0] == "deploy":
            deploy(action[1])
        else:
            raise ValueError("Usage: package.py verify-legacy|package|check-deploy MODS|deploy MODS")
    except (OSError, ValueError) as error:
        print(f"error: GroundhogSave: {error}", file=sys.stderr)
        sys.exit(1)
