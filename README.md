BulletDroid
=======
[![CodeFactor](https://www.codefactor.io/repository/github/lunapy17/bulletdroid/badge)](https://www.codefactor.io/repository/github/lunapy17/bulletdroid)

Inspired by OpenBullet, this repository offers a powerful webtesting toolkit tailored for Android devices. The application presents an attempt of a user-friendly GUI built with Kivy, powered by a Python backend. Designed for a mobile experience, this tool is designed to execute requests, being suitable for data scraping and pentesting using custom configs, multi-threading, and proxy support.

## Features

- **User-friendly Interface**: An intuitive GUI built with the Kivy framework.
- **Custom Configs**: Offers flexibility to customize the checking process with config files.
- **Multi-threading Support**: Enables faster processing.
- **Proxy Support**: Accepts all types of proxy.

NOTE: You must allow Storage Permission at App Settings

![image](https://github.com/LunaPy17/BulletDroid/assets/69711934/eedb332d-4c07-4f4d-9973-8ba39502c9b1)

![image](https://github.com/LunaPy17/BulletDroid/assets/69711934/591b7d87-2d3d-4e2a-b851-337ff98d9d99)

## Config Blocks

NOTE: You can see config examples in [Configs Carpet](https://github.com/LunaPy17/BulletDroid/tree/main/configs).

* REQUEST - Handle HTTP requests based on provided parameters (Headers, Postdata, etc).
* FIND - Parse a substring between two delimiters in a variable.
* SAVE - Set a string variable.
* PRINT - Show at logs a Variable or String
* RESULT - Return the response at display.

## Requirements

* python 3.x
* kivy
* retry_requests

## Installation

1. Clone the repository
```bash
git clone https://github.com/LunaPy17/BulletDroid
```

2. Install the required packages
```bash
pip install -r requirements.txt
```

3. Execute the app
```bash
python main.py
```

## License

This project is licensed under the GNU General Public License v3.0 [License](https://github.com/LunaPy17/BulletDroid/blob/main/LICENSE). See the LICENSE file for details.
