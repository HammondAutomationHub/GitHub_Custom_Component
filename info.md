# GPM

Uses the existing [GPM install script](https://github.com/tomasbedrich/gpm/blob/main/install/install.sh) and adds what that script does not configure: install from HACS or manually, a UI to pick a custom integration that was installed from HACS or copied in manually, a private GitHub repository and token, and how often to check (manual, hourly, daily, weekly, and similar).

{% if installed %}
## Configure

**Settings → Devices & services → Add integration → GPM**

1. Choose the integration folder. The integration can already be installed from HACS or copied in manually.
2. Enter the GitHub repository, branch, and a read-only token if the repo is private.
3. Choose manual or automatic updates, and how often to check.

The first check never installs. After that, manual mode waits for you to press **Install** on the Update entity. Automatic mode downloads new commits on the schedule you picked. Restart Home Assistant after an install.

If HACS also updates that integration, ignore it in HACS so the two do not overwrite each other.
{% endif %}

{% if not installed %}
## Install

Install GPM from HACS, or copy `custom_components/gpm` into your config folder manually, then restart Home Assistant.

Repository: `https://github.com/HammondAutomationHub/HomeAssistnat-GPM`
{% endif %}
