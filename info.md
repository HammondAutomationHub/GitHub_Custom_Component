# GPM

Updates custom integrations that are already installed under `custom_components`. Install GPM from HACS or copy it in manually. Choose a folder that was installed from HACS or copied in manually, point it at a GitHub repository with a token when the repo is private, and choose how often to check (manual, hourly, daily, weekly, and similar).

{% if installed %}
## Configure

**Settings → Devices & services → Add integration → GPM**

1. Choose the integration folder. The integration can already be installed from HACS or copied in manually.
2. Enter the GitHub repository, branch, and a read-only token if the repo is private.
3. Choose manual or automatic updates, and how often to check.

The first check never installs. After that, manual mode waits for you to press **Install** on the Update entity. Automatic mode downloads new commits on the schedule you picked. Restart Home Assistant after an install.

One reason to use GPM is a repository that started public and is now private. Leave the folder in `custom_components`, make the GitHub repo private, and point GPM at it with a read-only token.

To roll back, choose a tag or commit under **Rollback version**, then press **Install version and pause**. That turns **Updates paused** on. The update card and a repair item both say the folder stays on that revision until you turn the pause off or install the latest commit.

If HACS also updates that integration, ignore it in HACS so the two do not overwrite each other.
{% endif %}

{% if not installed %}
## Install

Install GPM from HACS, or copy `custom_components/gpm` into your config folder manually, then restart Home Assistant.

Repository: `https://github.com/HammondAutomationHub/HomeAssistant-GPM`
{% endif %}
