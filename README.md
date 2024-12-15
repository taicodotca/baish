![Baish Logo](img/baish.png)

# Baish (Bash AI Shield)

`curl thisisapotentiallyunsafescript.com/script.sh | baish -s | bash`

Baish is a security-focused tool that uses Large Language Models (LLMs) and other heuristics to analyse shell scripts before they are executed. It's designed to be used as a more secure alternative to the common `curl | bash` pattern.

Importantly, Baish is a cybersecurity learning project, where the developers have a relatively narrow solution to implement, but still learn a lot about the problem space. For example, how to use LLMs, how to secure them, and how to take and understand untrusted input.

## Security 

The underlying problems are the same in almost every application, and we are trying to use different heuristics in combination with general AI capabilities to build a cybersecurity tool. So there are two parts to the project:

1. Build a tool that uses LLMs to help improve security
2. Understand how to use LLMs themselves more securely

## Table of Contents
- [About TAICO](#about-taico)
- [Suggested Usage - LLM Context Window](#suggested-usage---llm-context-window)
- [Caveats and Disclaimers](#caveats-and-disclaimers)
- [Features](#features)
- [Large Language Model Provider Support](#large-language-model-provider-support)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [From PyPI](#from-pypi)
- [Usage](#usage)
  - [Setting Provider and Model](#setting-provider-and-model)
  - [Using Ollama](#using-ollama)
- [Examples](#examples)
  - [Shield Mode](#shield-mode)
- [Logging and Stored Scripts](#logging-and-stored-scripts)
- [Known Issues](#known-issues)
- [Future Work and TODOs](#future-work-and-todos)
- [Further Reading](#further-reading)

## About TAICO

The [Toronto Artificial Intelligence and Cybersecurity Organization (TAICO)](https://taico.ca) is a group of AI and cybersecurity experts who meet monthly to discuss the latest trends and technologies in the field. Baish is a project of TAICO.

## Suggested Usage - LLM Context Window

At this time, it is best to use a LLM provider that has a large context window, for example Anthropic, which has a 200,000 token context window. Using other LLMs with a short context window may currently result in errors, which is not necessarily their fault, it's that Baish needs more work to deal with small context windows. OpenAI has a 128K token window as well for most models. Best to use a provider that has a large context window, at least greater than 8192 tokens.

## Caveats and Disclaimers

⚠️ Baish's analysis is not foolproof! This is a proof of concept! To be completely sure that a script is safe, you would have to review and analyze it yourself.

⚠️ Different LLM providers will give different results. One provider and one model may give a script a low risk score, while another model or provider gives a high risk score. You would have to experiment with different providers and models to see which one you trust the most.

⚠️ Baish is in heavy development. Expect breaking changes.

⚠️ Using local Ollama for local LLMs is still experimental and may not work as expected, mostly due to small context windows.

## Features

- Accepts files on stdin, ala the `curl | bash` pattern, but instead you would do `curl | baish --shield | bash`
- Can analyze any file, not just shell scripts curled to bash
- Analyzes scripts using various configurable LLMs for potential security risks
- Provides a harm score (1-10) indicating potential dangerous operations (higher is more dangerous)
- Provides a complexity score (1-10) indicating how complex the script is (higher is more complex)
- Saves downloaded scripts for later review 
- Logs all requests and responses from LLMs along with the script ID
- Uses YARA rules and other heuristics to detect potential prompt injection

## Large Language Model Provider Support

Baish currently supports the following providers:

* Groq
* Anthropic
* OpenAI
* Experimental support for Ollama for local LLMs, e.g. llama3, mistral, etc.

It is straightforward to add support for other providers, pretty much anything LangChain supports, and contributions are welcome!



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

Run the install script:

```bash
curl -sSL https://raw.githubusercontent.com/taico-org/baish/main/install.sh -o install.sh
chmod +x install.sh
./install.sh
```

or install with pip:

```bash
pip install baish
```

Edit the `~/.baish/config.yaml` file to your liking.

Set your API key in your environment variables, e.g. `export OPENAI_API_KEY=...` or `export ANTHROPIC_API_KEY=...`

Now you can run baish!V

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

### Using Ollama

If using Ollama, you can also specify the base URL, though it will default to `http://localhost:11434` if not specified.

```yaml
other_model:
  provider: ollama
  model: llama3:latest
  url: http://localhost:11434
```

Currently our prompt is quite long, and for example when using llama3, the prompt length is 2048 by default, so you may see errors like this:

```
time=2024-12-08T11:22:33.343-05:00 level=WARN source=runner.go:129 msg="truncating input prompt" limit=2048 prompt=2815 keep=25 new=2048
```

You can increase the context window with the following command:

```
$ ollama run llama3 /set parameter num_ctx 4096
You've set the `num_ctx` parameter to 4096. This parameter is used in some machine 
learning models, such as transformer-based architectures, and specifies the number of 
context windows or attention heads to use.
<output abbreviated>
```

## Examples

Here's a few examples of real world scripts that Baish can help you analyze before execution. These are mostly about installing real world software.

```text
$ curl -fsSL https://ollama.com/install.sh | ./baish
⠙ Analyzing file...
╭────────────────────────────── Baish - Bash AI Shield ───────────────────────────────╮
│ Analysis Results - script_1732984526.sh                                             │
│                                                                                     │
│ Harm Score:       2/10 ████────────────────                                         │
│ Complexity Score: 8/10 ████████████████────                                         │
│ Uses Root:    True                                                                  │
│                                                                                     │
│ File type: text/x-shellscript                                                       │
│                                                                                     │
│ Explanation:                                                                        │
│ This script is a Linux installer for Ollama, a software package. It installs Ollama │
│ on the system, detects the operating system architecture, and installs the          │
│ appropriate version of Ollama. It also checks for and installs NVIDIA CUDA drivers  │
│ if necessary. The script uses various tools and commands to perform these tasks,    │
│ including curl, tar, and dpkg. The script is designed to be run as root and         │
│ modifies the system by installing software and configuring system settings.         │
│                                                                                     │
│ Script saved to: /home/ubuntu/.baish/scripts/script_1732984526.sh                   │
│ To execute, run: bash /home/ubuntu/.baish/scripts/script_1732984526.sh              │
│                                                                                     │
│ ⚠️  AI-based analysis is not perfect and should not be considered a complete         │
│ security audit. For complete trust in a script, you should analyze it in detail     │
│ yourself. Baish has downloaded the script so you can review and execute it in your  │
│ own environment.                                                                    │
╰─────────────────────────────────────────────────────────────────────────────────────╯
```

Install rvm:

```
curl -sSL https://get.rvm.io | baish --debug
```

Install rust:

```
curl --silent https://sh.rustup.rs | baish
```

Install docker:

```
curl -fsSL https://get.docker.com | baish --debug
```

### Shield Mode

Baish can also be used in "shield" mode, which will error out if the script is not safe.

```
curl -sSL https://thisisapotentiallyunsafescript.com/script.sh | baish -s | bash
```

E.g. of running an unsafe script through baish in shield mode, where bash will execute the output of baish, in this case outputting an error message:

```bash
$ cat tests/fixtures/secret-upload.sh | baish -s | bash
Script unsafe: High risk score detected
```

Or without piping to bash. Note how the output is a "script" itself, echoing the output to the terminal which bash will then execute:

```bash
$ cat tests/fixtures/secret-upload.sh | baish -s
echo "Script unsafe: High risk score detected"
```

## Logging and Stored Scripts

Baish logs all requests and responses from LLMs along with the script ID. It also saves the script to disk with the ID so it can be reviewed later.

Below we see the results of one Baish run.

```
$ tree ~/.baish/
/home/ubuntu/.baish/
├── logs
│   └── 2024-12-05_15-50-43_c6f3de91_llm.jsonl
└── scripts
    └── 2024-12-05_15-50-43_c6f3de91_script.sh

3 directories, 2 files
```

## Known Issues

* LLMs with short context windows (like some local models) may fail to analyze longer scripts due to prompt length limitations. Even commercial models with short context windows can fail to analyze longer scripts. 

## Future Work and TODOs

| Feature | Status | Description | Details |
|---------|--------|-------------|----------|
| Work with no configuration | TODO | Work with no configuration | Work with no configuration file, just look for an API key in the environment, make it as easy as possible to get started |
| OpenAI Support | DONE | Support OpenAI | Support OpenAI for LLM provider |
| JSON Output | DONE | Structured output format | Enables programmatic parsing of Baish results |
| LLM Logging | DONE | Request/response tracking | Log all LLM interactions with script IDs for audit trails |
| Prompt Injection Detection | DONE | YARA-based detection | Use YARA rules to identify potential prompt injection attempts |
| Shield Mode | DONE | Safe execution pipeline | Enable `curl \| baish \| bash` pattern with security controls |
| System Prompts | DONE | LLM prompt configuration | Configure system prompts for supported LLM providers |
| Prompt Injection Detection with YARA | DONE | YARA-based detection | Use YARA rules to identify potential prompt injection attempts |
| Root Usage Detection | IN PROGRESS | Improve detection | Enhance accuracy of root privilege usage detection |
| End to End Tests | IN PROGRESS | Dockerized tests | Run end to end tests in Docker |
| Atomic Red Team Integration | TODO | Use ART for testing | Use Atomic Red Team tests to validate Baish's detection capabilities against known malicious patterns |
| CI/CD Mode | TODO | Add pipeline integration | Create a specialized mode for CI/CD environments |
| Directory Analysis | TODO | Bulk file scanning | Analyze multiple files and generate comprehensive security reports |
| Custom YARA Rules | TODO | User-defined rules | Allow users to add their own YARA rules for custom threat detection |
| N/A Scoring | TODO | Better non-script handling | Display N/A instead of scores for non-scripts or prompt injection cases |
| Vector DB Memory | TODO | Long-term analysis storage | Implement vector database for historical analysis and pattern recognition |
| LLM Self-evaluation | TODO | Prompt injection checks | Enable LLMs to self-evaluate for prompt injection vulnerabilities |
| Token Length Management | TODO | Better chunking | Improve text chunking for large scripts using LangChain |
| Custom Prompts | TODO | User-defined prompts | Allow users to specify custom analysis prompts |
| Guardrails Integration | TODO | Add guardrails-ai | Integrate with guardrails-ai for additional security checks |
| Script Deobfuscation | TODO | Pre-analysis cleanup | Implement deobfuscation using tools like debash |
| VM Sandbox | TODO | Isolated execution | Run scripts in VM sandbox before actual execution |
| Shell Compilation | TODO | Compiled shell scripts | Support for compiled shell scripts using shc |
| One-time API Keys | TODO | Temporary credentials | Implement single-use API keys for safer execution |
| Base64 Detection | TODO | Encoded content handling | Detect and handle base64 encoded content |
| VirusTotal Integration | TODO | Hash checking | Check script hashes against VirusTotal database |
| VM Detonation | TODO | Dynamic analysis | Execute scripts in isolated environments for behavior analysis |
| Ollama JSON Support | TODO | JSON output | Support for Ollama JSON output format which comes in version 0.5 |
| Fix Debug logging | TODO | Debug logging | Right now many if debug statements are left in the code |
| Results Manager Coverage | TODO | Results Manager | Results Manager should manage logs, results, and scripts |
| Fix Config Expectation in Unit Tests | TODO | Unit Tests | Some unit tests expect a config file to exist, but it may not |

## Further Reading

* https://www.seancassidy.me/dont-pipe-to-your-shell.html
* https://www.djm.org.uk/posts/protect-yourself-from-non-obvious-dangers-curl-url-pipe-sh/index.html
* https://github.com/djm/pipe-to-sh-poc
* https://www.arp242.net/curl-to-sh.html
* https://github.com/greyhat-academy/malbash
