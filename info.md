# GPM

Uses the existing [GPM install script](https://github.com/tomasbedrich/gpm/blob/main/install/install.sh) and adds what that script does not configure: HACS install, a UI to pick an already installed custom integration folder, a private GitHub repository and token, and how often to check (manual, hourly, daily, weekly, and similar).

{% if installed %}
## Configure

**Settings → Devices & services → Add integration → GPM**

1. Choose the integration folder.
2. Enter the GitHub repository, branch, and a read-only token if the repo is private.
3. Choose manual or automatic updates, and how often to check.

The first check never installs. After that, manual mode waits for you to press **Install** on the Update entity. Automatic mode downloads new commits on the schedule you picked. Restart Home Assistant after an install.

If HACS also updates that integration, ignore it in HACS so the two do not overwrite each other.
{% endif %}

{% if not installed %}
## Install

Add this repository to HACS as a custom integration, download **GPM**, and restart Home Assistant.

Repository: `https://github.com/HammondAutomationHub/HomeAssistnat-GPM`
{% endif %}
