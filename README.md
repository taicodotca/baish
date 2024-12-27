![Baish Logo](img/baish.png)

# Baish (Bash AI Shield)

`curl thisisapotentiallyunsafescript.com/script.sh | baish -s | bash`

Baish is a security-focused tool that uses Large Language Models (LLMs) and other heuristics to analyse shell scripts before they are executed. It's designed to be used as a more secure alternative to the common `curl | bash` pattern.

Importantly, Baish is a cybersecurity learning project, where the developers have a relatively narrow solution to implement, but still learn a lot about the problem space. For example, how to use LLMs, how to secure them, and how to take and understand untrusted input.

## About TAICO

The [Toronto Artificial Intelligence and Cybersecurity Organization (TAICO)](https://taico.ca) is a group of AI and cybersecurity experts who meet monthly to discuss the latest trends and technologies in the field. Baish is a project of TAICO.

## Installation

### Prerequisites

* An API key from a supported LLM provider, e.g. OpenAI, Anthropic, Groq, etc. or a local LLM.
* Knowing which model from the provider you are going to use.
* Python 3.10 or later
* pip or pip3 installed
* libmagic (for file type detection)
  * Ubuntu/Debian: `apt install libmagic1`
  * RHEL/CentOS: `dnf install file-libs`
  * macOS: `brew install libmagic`

### Install

* Ensure to have the prerequisites installed
* Install with pipx is recommended
* Install with pip is also supported

#### Prerequisites

Ensure you have prerequisites installed. Currently the install script won't install the prerequisites for you.

On Linux:

```bash
sudo apt install libmagic1
```

On macOS:

```bash
brew install libmagic
```

#### Install with pipx

First, install [pipx](https://github.com/pypa/pipx). There are instructions for Mac, Linux, and Windows on the pipx website.

Then, install baish with pipx:

```bash
pipx install baish
```

Follow the pipx instructions to setup the alias in your shell, and at that point you can run `baish` as normal.

#### Install with pip

>NOTE: It's recommended to use pipx to install baish, as it creates a virtual environment to install the dependencies in.

```bash
pip install baish
```

### Configure

Ensure to set your API key in your environment variables, e.g. `export OPENAI_API_KEY=...` or `export ANTHROPIC_API_KEY=...`

Edit the `~/.baish/config.yaml` file to your liking.

e.g. use the `haiku` model from Anthropic:

```yaml
default_llm: haiku # default model to use
llms:
  haiku: # memorable name
    provider: anthropic # provider name
    model: claude-3-5-haiku-latest # model name
    temperature: 0.1 # temperature
```

Now you can run baish!

## Usage

* Technically, you can pipe any file to baish, but it's really meant to be used with shell scripts, especially via the `curl evil.com/evil.sh | baish` pattern.

```bash
curl -sSL https://thisisapotentiallyunsafescript.com/script.sh | baish
```

Baish will output the harm score, complexity score, and an explanation for why the script is either safe or not.

You can also run using the `--input` flag, which will read from a file instead of stdin.

```bash
baish --input some-script.sh
```

### Setting Provider and Model

You can set the provider and model in the `config.yaml` file.   

E.g. `config.yaml`:

```yaml
default_llm: haiku # default model to use
llms:
  haiku: # memorable name
    provider: anthropic # provider name
    model: claude-3-5-haiku-latest # model name
    temperature: 0.1 # temperature

  other_model:
    provider: groq
    model: llama3-70b-8192
    temperature: 0.1
```

## Example Output

Here's an example of the output of a real world script that Baish analyzed. In fact, it's the install script for Baish itself!

```text
$ curl -sSL https://raw.githubusercontent.com/taicodotca/baish/main/install.sh | baish 
⠋ Analyzing file...
╭──────────────────────────────── Baish - Bash AI Shield ────────────────────────────────╮
│ Analysis Results - 2024-12-21_06-55-35_e9fa19e5_script.sh                              │
│                                                                                        │
│ Harm Score:       2/10 ████────────────────                                            │
│ Complexity Score: 8/10 ████████████████────                                            │
│ Uses Root:    False                                                                    │
│                                                                                        │
│ File type: text/x-shellscript                                                          │
│                                                                                        │
│ Explanation:                                                                           │
│ The script is a bash installer for baish, a tool that sets up a Python virtual         │
│ environment and installs baish. It checks for system dependencies, Python              │
│ requirements, and installs baish using pip. It also sets up an alias for baish in the  │
│ user's shell configuration file.                                                       │
│                                                                                        │
│ Script saved to: /home/curtis/.baish/scripts/2024-12-21_06-55-35_e9fa19e5_script.sh    │
│ To execute, run: bash                                                                  │
│ /home/curtis/.baish/scripts/2024-12-21_06-55-35_e9fa19e5_script.sh                     │
│                                                                                        │
│ ⚠️  AI-based analysis is not perfect and should not be considered a complete security   │
│ audit. For complete trust in a script, you should analyze it in detail yourself. Baish │
│ has downloaded the script so you can review and execute it in your own environment.    │
╰────────────────────────────────────────────────────────────────────────────────────────╯
```

## Caveats and Disclaimers

⚠️ Baish's analysis is not foolproof! This is a proof of concept! To be completely sure that a script is safe, you would have to review and analyze it yourself.

⚠️ Different LLM providers will give different results. One provider and one model may give a script a low risk score, while another model or provider gives a high risk score. You would have to experiment with different providers and models to see which one you trust the most.

⚠️ Baish is in heavy development. Expect breaking changes.

⚠️ Using local Ollama for local LLMs is still experimental and may not work as expected, mostly due to small context windows.

## Documentation

See the [docs](docs/index.md) for more information.
