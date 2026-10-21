# GitHub - Custom_Component

GitHub - Custom_Component keeps a custom integration that is already installed under `custom_components` in step with a GitHub repository.

You choose the folder, the repository and branch, and whether updates are manual or automatic. Private repositories use a read-only token. Rolling back to an older tag or commit pauses updates on that revision until you resume them.

GitHub - Custom_Component and the integrations it updates can each be installed from HACS or copied in manually. Both end up in `custom_components`. GitHub - Custom_Component then manages only the folders you add.

## What you configure

Each folder gets its own entry:

- The integration folder, chosen from directories already on disk that contain a `manifest.json`
- A GitHub repository (`https://github.com/owner/repo` or `owner/repo`)
- The branch to follow
- A GitHub token, required for private repositories and recommended for public ones
- Manual or automatic install
- How often to check: only when you ask, hourly, every 6 hours, every 12 hours, daily, or weekly

## Install with HACS

1. In HACS, open **Integrations**.
2. Open the top-right menu and choose **Custom repositories**.
3. Add this repository as an **Integration**:

   `https://github.com/HammondAutomationHub/GitHub_Custom_Component`
4. In the HACS integrations list, find **GitHub - Custom_Component** and download it.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration** and choose **GitHub - Custom_Component**.

HACS reads `custom_components/github_custom_component` from the default branch. This repository is laid out that way.

## Install manually

Copy `custom_components/github_custom_component` into your Home Assistant config directory:

```text
<config>/custom_components/github_custom_component
```

Restart Home Assistant, then add **GitHub - Custom_Component** from **Settings → Devices & services**.

## Create a GitHub token

Private repositories need a token. Add one for public repositories too. GitHub allows very few unauthenticated API calls per hour.

Use a fine-grained personal access token:

1. On GitHub, open **Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Give it access only to the repositories GitHub - Custom_Component should read.
3. Under **Repository permissions**, set **Contents** to **Read-only**.
4. Generate the token and paste it into the token field.

Leave the token out of the repository URL. GitHub - Custom_Component rejects URLs that contain credentials.

Home Assistant stores the token in `.storage/core.config_entries`, the same place it stores other integration secrets. Use a read-only token and protect backups of the config directory.

## Add a folder

The setup dialog has three steps.

1. **Folder.** The list is every `custom_components` directory that has a `manifest.json`, except GitHub - Custom_Component itself. Install that integration from HACS or copy it in manually before adding it here.
2. **Repository.** Enter the GitHub URL or `owner/repo`, the branch (default `main`), and the token when the repository is private. GitHub - Custom_Component checks that the branch exists and that the repository contains this integration. Either layout works:
   - `custom_components/<folder>/manifest.json`, the usual HACS layout
   - `manifest.json` at the repository root, with `domain` equal to the folder name
3. **Schedule.**
   - **Manual** reports an update and waits for you to install it.
   - **Automatic** downloads the update when a later check finds a new commit.
   - Automatic mode needs an interval. "Only when I check" cannot be combined with automatic installs.

The first check never installs. When the local `manifest.json` version already matches the remote manifest, that commit is recorded as installed. When the versions differ, the Update entity shows an update and waits, including in automatic mode. A later scheduled check can install it.

Change the branch, token, or schedule later from the integration's **Configure** button. Leave the token blank there to keep the saved token. When GitHub rejects the token, Home Assistant opens a reauthentication prompt.

Each folder can be configured once.

## Devices

GitHub - Custom_Component adds one device per folder.

| Entity | What it does |
| --- | --- |
| Update | Shows the installed and remote versions, including a new commit that did not change the manifest version. After a rollback, the title says updates are paused. **Install** downloads the latest commit on the branch and turns **Updates paused** off. |
| Status | States the last check: up to date, an update is available, updates are paused, or the check failed. |
| Installed version | The version in the folder now. |
| Version to deploy | The version the last check found on the branch. **Install** deploys that version. |
| Check for updates | Checks GitHub now. A failed check shows the error. The result is on **Status** and on the update card. |
| Rollback version | Lists tags, then recent commits. It starts at "Choose a version to roll back". Choosing one does not install it. |
| Install version and pause | Installs the chosen tag or commit and turns **Updates paused** on. |
| Reinstall | While updates are paused, downloads that same revision again. Otherwise downloads the latest commit, even when the versions already match. |
| Updates paused | Turns on after a rollback. While it is on, automatic mode leaves the folder on the installed revision. Turn it off to follow the branch again. |

The dashboard card **GitHub - Custom_Component** is included. After a Home Assistant restart, reload the browser. On any dashboard, choose **Edit dashboard → Add card → By card** and search for **GitHub - Custom_Component**. On **By entity**, pick **Check for updates** or **Status** for that folder. The card is listed under **Community**. It shows Update, Check for updates, Rollback version, Install version and pause, Reinstall, Updates paused, and Status. Add the card again on each page where you want that folder.

The Update entity's release notes are the commit message. The release URL opens that commit on GitHub. While updates are paused, the notes also say that automatic checks will leave the folder where it is.

Open either **Rollback version** or **Install version and pause** to read that installing the selected version pauses updates.

## Roll back

On the device, open **Rollback version**, choose a tag or a recent commit, then press **Install version and pause**. GitHub - Custom_Component replaces `custom_components/<folder>` with that revision and turns **Updates paused** on. The update card, the **Updates paused** switch, and a repair item all say the folder is held on that revision.

Turn **Updates paused** off when the next check should follow the branch again. **Install** on the Update entity moves to the latest commit and clears the pause. You can also turn **Updates paused** on without rolling back, which holds whatever is installed now.

Restart Home Assistant after a rollback, the same as after any other install. Custom component code loads on startup.

The version list shows up to 15 tags, then recent commits on the configured branch that are not already represented by a tag. The dropdown choice is remembered until restart. The pause itself is saved.

## Services

- `github_custom_component.check_updates` — optional `folder`. Omit it to check every entry.
- `github_custom_component.install_update` — `folder` is required. Installs the latest commit and clears a pause.
- `github_custom_component.rollback` — `folder` and `version` are required. `version` is a tag name, such as `v1.2.0`, or a commit SHA. The install pauses updates.

Manual mode checks once when Home Assistant starts, so the Update entity has a version to show, and again when you press **Check for updates** or call the service. Automatic mode checks on the interval you chose, including once at startup after the first check. A download raises the repair **Restart required to finish the update**.

## Using this with HACS

The first install of each integration is yours: HACS, or a copy into `custom_components`. GitHub - Custom_Component then keeps that folder in step with the GitHub branch you named.

When HACS is also set to update that same integration, the two overwrite each other. After GitHub - Custom_Component owns the folder, ignore that repository in HACS or remove it from HACS. Leave the files in `custom_components`.

GitHub - Custom_Component follows the branch. A GitHub Release is installed when that branch contains the release commit.

## FAQ

### I started with a public GitHub repository and want to make it private

Leave the folder in `custom_components/<folder>`. GitHub - Custom_Component takes over updates after the GitHub repository is private.

1. Leave the installed folder where it is.
2. On GitHub, change that repository from public to private.
3. Create a fine-grained token that can read the private repository. Set **Contents** to **Read-only**.
4. Add GitHub - Custom_Component, choose that folder, enter the repository and branch, and paste the token.
5. If HACS was updating the public repository, ignore or remove it in HACS. HACS can no longer read a private repository it is not allowed to see, and both updaters would write the same folder.

You change the repository's visibility on GitHub. The first check does not reinstall when the local version already matches. Later commits on the private repository are what GitHub - Custom_Component offers to install.

## Troubleshooting

| Message | What to do |
| --- | --- |
| No custom integrations were found | Install one into `custom_components/<domain>` first. The folder needs a `manifest.json`. |
| Repository not found | Confirm `owner/repo`. For a private repository, the token must be allowed to read it. GitHub answers as if the repository does not exist when the token cannot see it. |
| GitHub rejected the token | Create a new fine-grained token with Contents: Read-only, then reauthenticate. |
| Branch was not found | Check the branch name. The default is `main`. |
| Could not find manifest.json | The repository needs `custom_components/<folder>/manifest.json`, or a root `manifest.json` whose `domain` is the folder name. |
| Manifest domain does not match | The folder name and the manifest `domain` must be the same. |
| Rate limit reached | Add a token, or check less often than hourly. |
| Restart required | Restart Home Assistant after GitHub - Custom_Component writes new component files. |

Debug logs:

```yaml
logger:
  logs:
    custom_components.github_custom_component: debug
```

The token is never written to the log.

## Development

Requires Python 3.12.

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements_test.txt
.venv\Scripts\python -m pytest
```

On Linux or macOS, use `.venv/bin/python` instead of `.venv\Scripts\python`.

The tests cover repository parsing, the manual and automatic decision, archive installation (including rejection of path traversal and symlinks), token handling, and a private-repository check followed by an install. They do not boot the Home Assistant UI.

## Limits

- GitHub.com only. GitHub Enterprise Server is not supported.
- GitHub - Custom_Component will not update its own folder.
- An update copies the integration files into place. The integration's own migrations run when Home Assistant starts.
- A bad commit on the tracked branch can break the next restart. Use manual mode for integrations you depend on, and keep Home Assistant backups.
- An automatic install still needs a restart before the new code runs.
- The download is limited to 100 MB.
- Updates are downloaded with the GitHub API, so a git binary is not required.
