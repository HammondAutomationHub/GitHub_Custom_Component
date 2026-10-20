# GPM

This uses the existing [GPM install script](https://github.com/tomasbedrich/gpm/blob/main/install/install.sh) and adds the configuration that script does not include.

The script finds Home Assistant, installs GPM, and writes a `gpm:` block into `configuration.yaml`. This repository keeps that role and adds:

- Install from HACS, then configure everything in the Home Assistant UI
- Choose which custom integration folder to update (one installed by HACS, or any other folder in `custom_components` with a `manifest.json`)
- Point that folder at a private GitHub repository
- Provide a token for that repository
- Choose manual updates, or an automatic check on a schedule (hourly, every 6 or 12 hours, daily, or weekly)

GPM is installed with HACS. It then updates integrations that are already on disk.

## What you can configure

For each integration folder:

- The folder to update, chosen from integrations already on disk
- A GitHub repository (`https://github.com/owner/repo` or `owner/repo`)
- A branch to follow
- A GitHub token, required for private repositories
- Manual or automatic install
- How often to check: only when you ask, hourly, every 6 hours, every 12 hours, daily, or weekly

## Install with HACS

1. In HACS, open **Integrations**.
2. Open the top-right menu and choose **Custom repositories**.
3. Add this repository as an **Integration**:

   `https://github.com/HammondAutomationHub/HomeAssistnat-GPM`

   The repository name is spelled `HomeAssistnat-GPM`.
4. In the HACS integrations list, find **GPM** and download it.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration** and choose **GPM**.

HACS needs the files in `custom_components/gpm` on the default branch. This repository is laid out that way.

## Install without HACS

Copy `custom_components/gpm` into your Home Assistant config directory:

```text
<config>/custom_components/gpm
```

Restart Home Assistant, then add the **GPM** integration from **Settings → Devices & services**.

## Create a GitHub token

Private repositories need a token. A token is also worth adding for public repositories, because GitHub allows very few unauthenticated API calls per hour.

Use a fine-grained personal access token:

1. On GitHub, open **Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Give it access only to the repositories GPM should read.
3. Under **Repository permissions**, set **Contents** to **Read-only**.
4. Generate the token and paste it into the GPM token field.

Do not put the token in the repository URL. GPM rejects URLs that contain credentials.

The token is stored in Home Assistant's config entry storage (`.storage/core.config_entries`), which is how Home Assistant stores integration secrets. Use a read-only token and protect backups of the config directory.

## Configure an integration

The config flow has three steps.

1. **Folder.** GPM lists directories in `custom_components` that contain a `manifest.json`. It does not list itself. Install the custom integration with HACS or by copying it in before you add it to GPM.
2. **Repository.** Enter the GitHub URL or `owner/repo`, the branch (default `main`), and the token if the repo is private. GPM checks that the branch exists and that the repo contains this integration. The expected layouts are:
   - `custom_components/<folder>/manifest.json` (the usual HACS layout)
   - `manifest.json` at the repository root, with `domain` equal to the folder name
3. **Schedule.**
   - **Manual** reports an update and waits for you to install it.
   - **Automatic** downloads the update when a later check finds a new commit.
   - Automatic mode needs a real interval. "Only when I check" cannot be combined with automatic installs.

The first check does not install anything. If the version in the local `manifest.json` already matches the remote manifest, GPM treats that commit as what is installed. If the versions differ, the Update entity shows an update and waits for you, even in automatic mode. The next scheduled check can install automatically.

Changing the branch, token, or schedule later is done from the integration's **Configure** button. Leave the token blank there to keep the saved token. If GitHub starts rejecting the token, Home Assistant opens a reauthentication prompt.

Each folder can only be configured once.

## Install an update

GPM adds one device per folder:

| Entity | What it does |
| --- | --- |
| Update | Shows the installed and remote versions. **Install** downloads the current remote commit. |
| Check for updates | Checks GitHub now. |
| Reinstall | Downloads the remote commit again, even when the versions already match. |

The Update entity's release notes are the remote commit message, and the release URL opens that commit on GitHub.

You can also call these services:

- `gpm.check_updates` — optional `folder`. Omit it to check every GPM entry.
- `gpm.install_update` — `folder` is required.

Manual mode still checks once when Home Assistant starts, so the Update entity has a version to show. After that it checks only when you press the button, call the service, or a schedule is set.

Automatic mode checks on the interval you chose (and once at startup after the first bootstrap). When it downloads an update, GPM raises a repair: **Restart required to finish the GPM update**. Custom component code is not reloaded until you restart Home Assistant.

## Using this with HACS

GPM does not install new integrations and it does not browse the HACS store. HACS (or a manual copy) does the first install. GPM then keeps that folder in sync with a GitHub branch.

If HACS is also set to update that same integration, the two will overwrite each other. After GPM owns the updates, ignore that repository in HACS or remove it from HACS. Leaving the files in `custom_components` is enough for GPM.

GPM follows the branch you name. It does not follow GitHub Releases unless that branch moves when you publish one.

## Troubleshooting

| Message | What to do |
| --- | --- |
| No custom integrations were found | Install one into `custom_components/<domain>` first. The folder needs a `manifest.json`. |
| Repository not found | Confirm the `owner/repo` name. For a private repo, the token must be allowed to read it. GitHub hides private repos it will not show, so a missing token looks like a missing repo. |
| GitHub rejected the token | Create a new fine-grained token with Contents: Read-only and reauthenticate. |
| Branch was not found | Check the branch name. The default is `main`. |
| Could not find manifest.json | The repo must contain `custom_components/<folder>/manifest.json`, or a root `manifest.json` whose `domain` is the folder name. |
| Manifest domain does not match | The folder name and the manifest `domain` must be the same. |
| Rate limit reached | Add a token, or check less often than hourly. |
| Restart required | Restart Home Assistant after GPM writes new component files. |

Debug logs:

```yaml
logger:
  logs:
    custom_components.gpm: debug
```

GPM does not log the token.

## Development

Requires Python 3.12.

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements_test.txt
.venv\Scripts\python -m pytest
```

On Linux or macOS, use `.venv/bin/python` instead of `.venv\Scripts\python`.

The tests cover repository parsing, the manual/automatic decision, archive installation (including rejection of path traversal and symlinks), token handling, and a private-repository check followed by an install. They do not boot a full Home Assistant UI.

## Limits

- GitHub.com only. GitHub Enterprise Server is not supported.
- GPM will not update its own folder.
- Updates copy the integration files. They do not run the integration's own migrations beyond what that integration does on the next Home Assistant start.
- A bad commit on the tracked branch can break the next restart. Use manual mode for integrations you cannot do without, and keep Home Assistant backups.
- Automatic install still needs a restart before the new code runs.
- The download is limited to 100 MB so a repository cannot fill the disk unnoticed.
- Built on the [tomasbedrich/gpm](https://github.com/tomasbedrich/gpm) installer. The additions are HACS install, UI setup, per-folder updates, private GitHub authentication, and a check schedule. Dashboard resources from that project are unchanged here. Updates are downloaded with the GitHub API, so a git binary is not required.
