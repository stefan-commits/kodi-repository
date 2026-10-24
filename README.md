# Stefan's Kodi Repository

Installable multi-add-on repository for Kodi 19+ with preserved release ZIPs, a generated catalog, and a publishing workflow. Currently includes **NordVPN CLI 6.0.4** (Linux; requires the NordVPN Linux app).

## Install in Kodi

1. [Download the repository ZIP](https://stefan-commits.github.io/kodi-repository/repository.stefan-commits/repository.stefan-commits-1.0.0.zip).
2. In Kodi, enable **Settings → System → Add-ons → Unknown sources**.
3. Choose **Add-ons → Install from zip file** and select the downloaded ZIP.
4. Choose **Install from repository → Stefan's Kodi Repository → Program add-ons → NordVPN CLI**.
5. Enable automatic add-on updates to receive future releases published here.

[Download page](https://stefan-commits.github.io/kodi-repository/) · [Direct installer fallback](https://raw.githubusercontent.com/stefan-commits/kodi-repository/main/docs/repository.stefan-commits/repository.stefan-commits-1.0.0.zip)

You can also add the download-page URL as a Kodi file-manager source, then browse its repository directory to install the ZIP.

## Publish another add-on or an update

Keep each add-on's development in its own source repository. Publish a GitHub Release with its installable ZIP, then open this repository's **Actions → Import add-on release → Run workflow**. Enter the public source repository, release tag, and exact ZIP filename. This supports new add-on IDs and updates equally. The workflow imports the exact ZIP, validates it, updates the catalog and commits the result to `main`. No extra token is required for public releases.

Publishing is intentionally initiated by a maintainer; releases in upstream repositories are not automatically imported. Future automation can invoke the same workflow through GitHub's workflow-dispatch API.

Each ZIP must contain one `addon.id/` directory with `addon.xml`, runtime files and declared artwork. Use stable numeric `major.minor.patch` versions. Increase the version in `addon.xml` for every changed release. Replacing an existing version or downgrading the active version is rejected. Retain published ZIPs so existing links continue working.

Local alternative (Python 3.9+, no third-party dependencies):

```sh
python3 tools/repository.py import /path/to/plugin.example-1.0.0.zip --source https://github.com/OWNER/PROJECT/tree/v1.0.0
python3 -m unittest discover -s tests -v
python3 tools/repository.py build --check
git add catalog.json docs
git commit -m 'Publish plugin.example 1.0.0'
git push
```

## Layout and delivery

- `catalog.json`: current version, source link and SHA-256 for each add-on.
- `docs/<addon-id>/<addon-id>-<version>.zip`: immutable packages; older versions remain downloadable.
- `docs/addons.xml` and `.md5`: generated Kodi catalog and change marker.
- `docs/index.html`: installation page, hosted on GitHub Pages.
- `repository.stefan-commits/`: source of the repository installer.
- `tools/`: package importer, validator and installer builder.
- `.github/workflows/`: validation on pushes/PRs and manual release import.

Kodi fetches the catalog and ZIPs over HTTPS from the public `main/docs` raw URLs. It does not depend on Pages deployment completion. GitHub Pages deploys `docs/` through the Deploy download page workflow after pushes or a successful release import. The MD5 file is Kodi's catalog change marker, not a security signature. GitHub raw hosting does not provide Kodi's content-hash headers, so the repository uses `hashes=false`; SHA-256 sidecars and catalog checksums are provided for verification.

Repository format follows the [Kodi repository specification](https://kodi.wiki/view/Add-on_repositories). Add-ons declare their own Kodi/platform compatibility; the repository is available on Kodi 19+. There is currently one stable channel; add separate catalog directories/repository `<dir>` entries if incompatible Kodi generations need different builds later.

## Update the repository installer

Only needed when repository metadata or endpoints change, not for ordinary add-on releases. Edit `repository.stefan-commits/addon.xml` and increase its version, then:

```sh
python3 tools/package_repository.py
python3 tools/repository.py import .work/repository.stefan-commits-1.0.1.zip --source https://github.com/stefan-commits/kodi-repository
```

Replace the example version with the actual new version. Update the installer links in this README, validate, commit and push. Installed repository add-ons can update through the same catalog.

## Licensing and provenance

Repository tooling and installer: MIT. NordVPN CLI: GPL-3.0-or-later, with its original license inside the unchanged ZIP. [Exact NordVPN 6.0.4 source](https://github.com/stefan-commits/NordVPN-Kodi-Plugin/tree/v6.0.4). New add-ons retain their own licenses and must include corresponding source/distribution notices as required. This repository and NordVPN CLI are unofficial and are not affiliated with NordVPN or Kodi.
