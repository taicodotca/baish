#!/bin/bash
set -e

SCRIPT_VERSION="1.0.0"
DRY_RUN=${DRY_RUN:-}
QUIET=${QUIET:-}
USE_VENV=${USE_VENV:-true}

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

check_dependencies() {
    log "Checking system dependencies..."
    if [ "$(uname)" = "Darwin" ]; then
        if ! command_exists brew; then
            echo "Error: brew is required to check for libmagic"
            echo "Install from https://brew.sh"
            exit 1
        fi
        if ! brew list libmagic &>/dev/null; then
            echo "Error: libmagic not found"
            echo "Install with: brew install libmagic"
            exit 1
        fi
    elif [ "$(uname)" = "Linux" ]; then
        if ! ldconfig -p | grep -q libmagic; then
            echo "Error: libmagic not found"
            echo "Install with: sudo apt install libmagic1 (Debian/Ubuntu)"
            echo "           or sudo dnf install file-libs (Fedora)"
            echo "           or sudo pacman -S file (Arch)"
            exit 1
        fi
    else
        echo "Unsupported operating system: $(uname)"
        exit 1
    fi
}

check_python_requirements() {
    log "Checking python requirements..."
    if ! command_exists python3; then
        echo "Error: python3 is not installed"
        exit 1
    fi

    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        echo "Error: Python 3.10 or higher required (found $PYTHON_VERSION)"
        exit 1
    fi
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo "Python $PYTHON_VERSION found, continuing..."

    if ! command_exists pip3 && ! command_exists pip; then
        echo "Error: pip is not installed"
        echo "On Ubuntu/Debian: apt install python3-pip"
        echo "On Fedora: dnf install python3-pip"
        echo "On macOS: brew install python3"
        exit 1
    fi

    if [ "$USE_VENV" = true ] && ! python3 -c "import venv" 2>/dev/null; then
        echo "Error: Python venv module not available"
        echo "On Ubuntu/Debian: apt install python3-venv"
        echo "On Fedora: dnf install python3-venv"
        exit 1
    fi
}

do_install() {
    log "Creating configuration directory..."
    mkdir -p "${HOME}/.baish"

    if [ "$USE_VENV" = true ]; then
        log "Setting up a python virtual environment for baish..."
        python3 -m venv "${HOME}/.baish/python-venv"
        . "${HOME}/.baish/python-venv/bin/activate"
        pip install -q baish
    else
        log "Installing baish with system python..."   
        pip install --user baish
    fi
    
    if [ ! -f "${HOME}/.baish/config.yaml" ]; then
        log "Creating default configuration..."
        cat > "${HOME}/.baish/config.yaml" << EOF
default_llm: openai
llms:
  openai:
    provider: openai
    model: gpt-4o-mini
    temperature: 0.1
    token_limit: 128000
  claude:
    provider: anthropic
    model: claude-3-5-sonnet-latest
    temperature: 0.1
    token_limit: 200000
EOF
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
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -h, --help          Show this help message"
            echo "  --version           Show version information"
            echo "  --dry-run           Show what would be done"
            echo "  --quiet             Suppress output"
            echo "  --no-venv           Do not use virtual environment to install baish"
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
check_dependencies
check_python_requirements
do_install
log "Baish installed successfully!"
log "Now either setup your OpenAI or Claude API keys in your environment variables,"
log "or setup the ~/.baish/config.yaml file with the LLM providers you would like to use."
log "You can also run 'baish --help' to get started."
log "If you installed with --use-venv, you can activate the virtual environment with"
log "source ~/.baish/python-venv/bin/activate"
log "and run baish from there."