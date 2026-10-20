# GitHub - Custom_Component

Keeps a custom integration that is already installed under `custom_components` in step with a GitHub repository. Install GitHub - Custom_Component from HACS or copy it in manually. Point a folder at a repository, add a read-only token when the repository is private, and choose a manual or scheduled check.

{% if installed %}
## Configure

**Settings → Devices & services → Add integration → GitHub - Custom_Component**

1. Choose the integration folder. Install that integration from HACS or copy it in manually first.
2. Enter the GitHub repository, branch, and a read-only token when the repository is private.
3. Choose manual or automatic updates, and how often to check.

The first check never installs. After that, manual mode waits for **Install** on the Update entity. Automatic mode downloads new commits on the schedule you picked. Restart Home Assistant after an install.

A public repository can later be made private. Leave the folder in `custom_components`, change the GitHub repository to private, and point GitHub - Custom_Component at it with a read-only token.

To roll back, choose a tag or commit under **Rollback version**, then press **Install version and pause**. **Updates paused** turns on. The update card and a repair item say the folder stays on that revision until you turn the pause off or install the latest commit.

When HACS also updates that integration, ignore it in HACS so the two do not overwrite the same folder.
{% endif %}

{% if not installed %}
## Install

Install GitHub - Custom_Component from HACS, or copy `custom_components/github_custom_component` into your config folder manually, then restart Home Assistant.

Repository: `https://github.com/HammondAutomationHub/GitHub_Custom_Component`
{% endif %}
