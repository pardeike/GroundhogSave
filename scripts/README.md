# Build, package, and install

Run `./scripts/build-quiet.sh -c Release` for the normal workflow.
If `RIMWORLD_MOD_DIR` is unset or empty, this command only builds locally.
If `RIMWORLD_MOD_DIR` names an existing Mods directory, it builds, installs, and produces a verified ZIP.
The build writes runtime DLLs to `1.7/Assemblies/`.
It targets RimWorld 1.7, AnyCPU, and .NET SDK 10.0.400.
It uses Krafs 1.7.4990-unstable and Harmony reference assemblies 3.0.0-rc.4.
CrossPromotion is 1.1.2. TaskPubliciser is 1.0.3.
These are the latest compatible versions checked against NuGet on 2026-10-31.

```sh
RIMWORLD_MOD_DIR="/path/to/Mods" ./scripts/build-quiet.sh -c Release
```

The installed mod is `$RIMWORLD_MOD_DIR/GroundhogSave/`.
The verified deployment archive is `$RIMWORLD_MOD_DIR/GroundhogSave.zip`.
The same operation retains its verified staging output under `.builds/package/`.
An ordinary `dotnet build Source/GroundhogSave.csproj -c Release` uses the same deployment targets when the environment variable is set.
Pass the deployment root through the environment when using the quiet wrapper.

Run `./scripts/build-quiet.sh -c Release --package` to build and verify a package without installing it.
This mode explicitly disables deployment, even when `RIMWORLD_MOD_DIR` is inherited.
It works while the game runs because it never checks or changes game state.
The outputs are `.builds/package/GroundhogSave/` and `.builds/package/GroundhogSave.zip`.
The MSBuild equivalent is `dotnet build Source/GroundhogSave.csproj -c Release -t:PackageMod -p:RIMWORLD_MOD_DIR=`.

Run `./scripts/build-quiet.sh -c Release --check` to build, package, and run the workflow checks.
This mode also disables deployment to the configured Mods directory.
The checks install only into disposable Mods directories under `.builds/`.
They simulate stopped-game process inspection for the isolated integration build.
Separate checks cover running-game detection and failed process inspection.

All quiet commands print `ok` only after every requested step and verification succeeds.
Full output goes to `.builds/build.log`.
Cancellation stops the build process and its children.

Deployment refuses a running game or a failed process inspection.
The workflow never starts or stops the game.
The supplied root must logically and physically name an existing directory called Mods.
Deployment refuses symlinked mod or ZIP destinations and symlinks inside an installed payload.
A per-destination operating-system lock prevents concurrent installers.

If the mod destination is absent, deployment initializes it from the complete verified staged payload.
It installs that initial payload through one directory rename.
If the destination exists, all frozen DLLs, languages, and artwork must match the pinned published payload exactly.
A mismatch, missing frozen file, or extra payload file stops deployment before changing installed payload files.
Matching frozen files are never rewritten, replaced, or deleted.
Updates change only current 1.7 files and shared metadata or documentation that differ.
Each changed file and the deployment ZIP use an atomic replacement.
The installer verifies installed bytes against the staged package and then verifies the deployment ZIP against installed bytes.

The original root `Assemblies/` and `Languages/` remain unchanged.
Their hashes are checked before and after every build.
The repository's root GroundhogSave DLL differs from the published 1.6 DLL.
Its language XML has the same content but different line endings.
Do not publish the checkout directly.

Packaging downloads the v1.0.0.0 GitHub release into `.builds/published-v1.0.0.0.zip` on first use.
It checks the archive's SHA-256 before using it.
The pinned SHA-256 is `51a9ab83bae1f7dd2f4cc0fce2ad96dfec0d75de7e9169394346bb8e597a49f0`.
The archive's DLLs, language files, and artwork match the Steam payload inspected during the port.
Packaging uses those exact published bytes for the package's root payload.
It never copies them over the repository's root files.
If the archive is unavailable or its checksum fails, packaging stops.

`LoadFolders.xml` keeps 1.6 loading only the root and makes 1.7 load only `1.7/`.
The package retains the published 1.6 DLLs and languages while adding the separate 1.7 payload.
Packaging verifies version metadata, load folders, the permitted runtime DLLs, and ZIP contents.
It excludes debug symbols, private Harmony assemblies, source, and build tools.
Current 1.7 dependency DLLs are independent of the frozen published dependency DLLs.

When the mod version changes, update `Directory.Build.props`, `About/About.xml`, and `About/Manifest.xml` together.
Local builds check metadata during packaging and do not rewrite it.
