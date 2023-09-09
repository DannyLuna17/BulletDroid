BulletDroid
=======
[![CodeFactor](https://www.codefactor.io/repository/github/lunapy17/bulletdroid/badge)](https://www.codefactor.io/repository/github/lunapy17/bulletdroid)

Inspired by OpenBullet, this repository offers a powerful webtesting toolkit tailored for Android devices. The application presents an attempt of a user-friendly GUI built with Kivy, powered by a Python backend. Designed for a mobile experience, this tool is designed to execute requests, being suitable for data scraping and pentesting using custom configs, multi-threading, and proxy support.

## Features

- **User-friendly Interface**: An intuitive GUI built with the Kivy framework.
- **Custom Configs**: Offers flexibility to customize the checking process with config files.
- **Multi-threading Support**: Enables faster processing.
- **Proxy Support**: Accepts all types of proxy. (HTTP, SOCKS4, SOCKS5, SOCKS4A, SOCKS5H)
- **Data Scraping**: Extracts data from websites.
- **Pentesting**: Tests the security of websites.

NOTE: You must allow Storage Permission at App Settings

![image](https://github.com/LunaPy17/BulletDroid/assets/69711934/eb330c2b-f35c-4869-ac04-e1b41dfa7e2b)

![image](https://github.com/LunaPy17/BulletDroid/assets/69711934/93397795-9edb-4ecb-a481-d815e6f9ba08)

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

## Contributing

Thanks for your interest in contributing! Your contributions are highly appreciated. Feel free to open an issue or submit a pull request for any bugs/improvements.

Please read the [Contributing Guidelines](https://github.com/LunaPy17/BulletDroid/blob/main/docs/contributing.md) for more details about how to contribute and support the project.

## License

This project is licensed under the GNU General Public License v3.0 [License](https://github.com/LunaPy17/BulletDroid/blob/main/LICENSE). See the LICENSE file for details.
