# Mix.nlu sample Python application

This document will guide you through the installation, configuration and execution of the Mix.nlu Python sample app. You can also find a troubleshooting section at the end for common problems.

*Note: This file is best viewed in a GitHub-flavored MarkDown editor, such as [jbt.github.io/markdown-editor](https://jbt.github.io/markdown-editor)*

## Installation

### 1. Install [PortAudio](http://www.portaudio.com/) to access your audio devices, and [Opus](http://opus-codec.org/) for faster audio streaming.

**Windows**:

Download and install the latest [Cygwin](https://cygwin.com/install.html), with the following packages:

- git
- libportaudio2
- libportaudio-devel
- python3
- python3-devel
- python3-pip
- libopus0
- libopus-devel

**Mac OS** (using [Homebrew](http://brew.sh/)):

```shell
brew install portaudio opus
```

**UNIX**:

With your package manager (`yum`, `apt-get`), install the following packages:

- libportaudio2
- portaudio19-dev
- libopus0
- libopus-dev

Alternatively, to build from source:

```shell
wget http://www.portaudio.com/archives/pa_stable_v19_20140130.tgz
tar xzf pa_stable_v19_20140130.tgz
cd portaudio/
sudo ./configure
sudo make
sudo make install
sudo ldconfig
cd ..
wget https://archive.mozilla.org/pub/opus/opus-1.2.1.tar.gz
tar xzf opus-1.2.1.tar.gz
cd opus-1.2.1/
sudo ./configure
sudo make
sudo make install
sudo ldconfig
```

### 2. Set up your [virtual environment](https://docs.python.org/3/tutorial/venv.html#creating-virtual-environments) with python 3.4+ :

```shell
python3 -m venv nlu_env
source nlu_env/bin/activate
pip install -r requirements.txt
```

## Configuration

Your `app_id`, `app_key`, and `context_tag` have been prepopulated in the `creds.json` file. Your `app_id` and 128-byte `app_key` come from your [Nuance Developers account](https://developer.nuance.com/public/index.php?task=account).

If you need to modify any of these variables, simply replace the existing strings in the `creds.json` file.  (For example, you may want to perform transactions using a different `context_tag` than what was prepopulated for you.)

*NOTE: If you have no context tag existing, an empty string is populated for the context tag key in the `creds.json` file. As soon as you set up an Application Config, you need to replace this field with the tag you desire to use in your transactions.*

## Running the client

To run the app, navigate to where your `nlu.py` file is located, activate your virtual environment:

```shell
source nlu_env/bin/activate
```

then run one of the following commands:

* For audio + NLU:

    ```shell
    python nlu.py audio
    # 1. Start recording when prompted;
    # 2. Press <enter> when done.

    python nlu.py --user_id="<user-identifier>" audio
    # 1. Start recording when prompted;
    # 2. Press <enter> when done.
    ```

* For text + NLU:

    ```shell
    python nlu.py text "This is the sentence you want to test"
    python nlu.py --user_id="<user-identifier>" text "This is the sentence you want to test"
    ```

* For per user concept data:

    ```shell
    python nlu.py --user_id="<user-identifier>" data_upload "<concept-name>" "dynamic_list.sample.json"
    ```

    ```shell
    python nlu.py --user_id="<user-identifier>" data_wipe
    ```

* To display CLI usage:

    ```shell
    python nlu.py --help
    ```

## Troubleshooting

1. Running the sample gives me a `SyntaxError`.

    Ensure you're running Python 3.4+

    ```shell
    python --version
    ```

2. `pyaudio` fails to install, with the following error message:
    ```shell
    src/_portaudiomodule.c:29:10: fatal error: 'portaudio.h' file not found
    #include "portaudio.h"
             ^
    1 error generated.
    error: command '/usr/bin/clang' failed with exit status 1
    ```

    or `opuslib` fails to import with the following exception:

    ```shell
    >>> import opuslib
    Traceback (most recent call last):
    [...]
        'Could not find opus library. Make sure it is installed.')
    Exception: Could not find opus library. Make sure it is installed.
    ```

    This problem might occur when the corresponding C libraries were not installed in the expected directory. You will need to install the Python packages that depend on them with additional options:

    ```shell
    pip install --global-option='build_ext' --global-option='-I/usr/local/include' --global-option='-L/usr/local/lib' pyaudio opuslib
    ```

3. The `pip install` command fails with `error: invalid command 'bdist_wheel'`

    Make sure you have `wheel` installed:

    ```shell
    pip install wheel
    pip install -r requirements.txt
    ```
