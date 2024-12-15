#!/bin/bash
set -e

SCRIPT_VERSION="1.0.0"
DRY_RUN=${DRY_RUN:-}
QUIET=${QUIET:-}
NO_DEPENDENCIES=${NO_DEPENDENCIES:-}
USE_VENV=${USE_VENV:-false}

show_banner() {
    [ -z "$QUIET" ] && echo "
██████╗  █████╗ ██╗███████╗██╗  ██╗
██╔══██╗██╔══██╗██║██╔════╝██║  ██║
██████╔╝███████║██║███████╗███████║
██╔══██╗██╔══██║██║╚════██║██╔══██║
██████╔╝██║  ██║██║███████║██║  ██║
╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝

Installing baish...
"
}

log() {
    [ -z "$QUIET" ] && echo "==> $@"
}

command_exists() {
    command -v "$@" > /dev/null 2>&1
}

is_dry_run() {
    [ -n "$DRY_RUN" ]
}

check_python_requirements() {
    log "Checking python requirements..."
    if ! command_exists python3; then
        echo "Error: python3 is not installed"
        exit 1
    fi

    # Simple Python version check without bc
    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        echo "Error: Python 3.10 or higher required (found $PYTHON_VERSION)"
        exit 1
    fi
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo "Python $PYTHON_VERSION found, continuing..."

    # Check pip/pip3
    if ! command_exists pip3 && ! command_exists pip; then
        echo "Error: pip is not installed"
        echo "       Please install pip or pip3 and try again."
        echo "       On Ubuntu/Debian, you can install it with 'apt install python3-pip'."
        exit 1
    else
        echo "pip found, continuing..."
    fi

    # Check venv module if USE_VENV is set
    if [ -n "$USE_VENV" ]; then
        if ! python3 -c "import venv" 2>/dev/null; then
            echo "Error: Python venv module not available. Install python3-venv package."
            exit 1
        fi
    fi
}

install_dependencies() {
    if [ "$(uname)" = "Darwin" ]; then
        if ! command_exists brew; then
            log "Error: Attempting to install libmagic on macOS, but brew is not installed."
            log "       Either install brew or install libmagic manually."
            log "       Then run with --no-dependencies to skip this step."
            exit 1
        fi
        $sh_c "brew install libmagic"
    elif [ "$(uname)" = "Linux" ]; then
        $sh_c "apt update > /dev/null 2>&1"
        $sh_c "apt install -y libmagic1 > /dev/null 2>&1"
    else
        log "Unsupported operating system: $(uname)"
        exit 1
    fi
}

do_install() {
    user="$(id -un 2>/dev/null || true)"
    sh_c='bash -c'  # Changed from sh -c to bash -c
    if [ "$user" != 'root' ]; then
        if command_exists sudo; then
            sh_c='sudo -E bash -c'  # Changed to use bash explicitly
        else
            echo "Error: this installer needs root privileges"
            exit 1
        fi
    fi

    if is_dry_run; then
        sh_c="echo"
    fi

    log "Installing dependencies..."
    if [ -z "$NO_DEPENDENCIES" ]; then
        install_dependencies
    fi

    log "Creating configuration directory..."
    $sh_c "mkdir -p ~/.baish"

    if [ "$USE_VENV" = true ]; then
        log "Setting up a python virtual environment for baish..."
        $sh_c "mkdir -p ~/.baish"
        $sh_c "python3 -m venv ~/.baish/python-venv"
        $sh_c ". ~/.baish/python-venv/bin/activate && ~/.baish/python-venv/bin/pip install -q baish"
    else
        log "Installing baish with system python..."   
        $sh_c "pip install baish"
    fi
    
    if [ ! -f "${HOME}/.baish/config.yaml" ]; then
        log "Creating default configuration..."
        $sh_c "cat > ~/.baish/config.yaml << EOF
default_llm: openai
llms:
  openai:
    provider: openai
    model: gpt-4-turbo-preview
    temperature: 0.1
    token_limit: 128000
  claude:
    provider: anthropic
    model: claude-3-opus-20240229
    temperature: 0.1
    token_limit: 128000
EOF"
    fi
}

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            ;;
        --quiet)
            QUIET=1
            ;;
        --version)
            echo "baish installer version $SCRIPT_VERSION"
            exit 0
            ;;
        --use-venv)
            USE_VENV=true
            ;;
        --no-dependencies)
            NO_DEPENDENCIES=1
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -h, --help          Show this help message"
            echo "  --version           Show version information"
            echo "  --dry-run           Show what would be done"
            echo "  --quiet             Suppress output"
            echo "  --no-dependencies   Skip installing system dependencies"
            echo "  --use-venv          Use virtual environment to install baish"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
    shift
done

show_banner
check_python_requirements
do_install
log "Baish installed successfully!"
log "Now either setup your OpenAI or Claude API keys in your environment variables,"
log "or setup the ~/.baish/config.yaml file with the LLM providers you would like to use."
log "You can also run 'baish --help' to get started."
log "If you installed with --use-venv, you can activate the virtual environment with"
log "source ~/.baish/python-venv/bin/activate"
log "and run baish from there."
