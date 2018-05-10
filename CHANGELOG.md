# Change Log

This document tracks changes to Mix.nlu's sample Python application.

## 2017-08-11
* [misc] Minor linting and `.pylintrc` improvements.

## 2017-07-11

* [feature] Removed Speex in favor of Opus for audio encoding.
* [feature] Improved memory usage of audio buffers.
* [feature] Improved resource freeing for normal and error cases.
* [feature] Added `-u` and `--user-id` as aliases for `--user_id`.
* [misc] Added a tentative pylint style guide.
* [misc] Bumped to aiohttp 2 for better WebSocket connection code.
* [misc] Refactored and modernized asyncio code
* [misc] Refactored NCS logic into client, session and transaction classes.
* [misc] Various linting/readability improvements.
* [doc] Added install steps for `yum` and `apt-get`.
* [doc] Fixed typos in the README.
* [fix] Fixed multiple channels to mono conversion.
* [fix] Fixed various misleading comments and docstrings.

## 2017-04-14

* [doc] Support Windows installation.

## 2017-04-06

* [misc] Bumped `pyaudio` to 0.2.11.
* [misc] Stop installing `asyncio` for Python >= 3.5.

## 2017-01-30

* [doc] Updated install steps for Mac for Speex >= 1.2.0 (added `speexdsp`).

## 2016-12-15

* [doc] Fixed a typo in the README.
* [misc] Updated Python dependencies: `aiohttp` and `pyaudio`.
* [misc] Ignore `.DS_store` file from Git.

## 2016-11-21

* [doc] Added a self-referencial CHANGELOG file.

## 2016-11-18

* [feature] Added per-user data upload and data wipe commands.
* [feature] Added a configurable `user_id` parameter to all commands.

## 2016-03-15

* [feature] Added a configurable `language` parameter, instead of hardcoding "eng-USA".

## 2016-02-23

* [doc] Improved troubleshooting of C-bindings libraries.
* [doc] Improved virtualenv documentation.

## 2016-02-11

* [feature] Added a `.gitignore` to ensure credentials are not pushed.
* [fix] Removed partially broken TTS and ASR-only commands.
* [feature] Switched to [argparse](https://docs.python.org/3/library/argparse.html) for the CLI parameters.
* [misc] Added a context manager for the audio recorder.
* [feature] Made `Recorder` class more flexible outside of default values.
* [misc] Improved and linted the module's code.

## 2016-01-16

* [fix] Fixed microphone detection by using the default input device ID.
* [doc] Added usage information on CLI misuse.
* [doc] Added some FAQ, and their solution.
* [doc] Improved wording, and markdown formatting of the README.

## 2015-12-15

* [doc] Added setup information on how to install speex (Mac/Unix).
* [misc] Removed unused dependencies from the `requirements.txt`.
* [doc] Improved the formatting in the README.

## 2015-11-03

* Initial release.
