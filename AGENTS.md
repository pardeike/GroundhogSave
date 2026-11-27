# Project workflow

- Run `./scripts/build-quiet.sh -c Release` for the normal RimWorld 1.7 workflow.
- If `RIMWORLD_MOD_DIR` is unset or empty, the normal workflow only builds locally.
- Add `--package` to build and verify `.builds/package/GroundhogSave.zip`.
- Add `--check` to build, package, and test only against disposable Mods directories.
- Set `RIMWORLD_MOD_DIR` to an existing RimWorld Mods directory for the normal build, guarded install, and verified ZIP.
- If the game runs, deployment fails. The workflow never starts or stops the game.
- `--package` explicitly disables deployment, including when `RIMWORLD_MOD_DIR` is inherited.
- Read `scripts/README.md` before packaging or changing the version layout.
- Keep the original root `Assemblies/` and `Languages/` unchanged.
- Build current code into `1.7/`. Put current resources under `1.7/`.
- The root DLL differs from the published 1.6 DLL. Never package the checkout by copying its root payload.
- Package 1.6 from the checksum-pinned v1.0.0.0 release archive, only in ignored staging output.
- Before updating an existing installation, require its frozen DLLs, languages, and artwork to match the published payload exactly.
- Never rewrite existing frozen files. Refuse mismatches, missing frozen files, extra payload files, and symlinked destinations.
