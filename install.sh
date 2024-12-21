#!/bin/bash
set -e

SCRIPT_VERSION="1.0.2"
DRY_RUN=${DRY_RUN:-false}
QUIET=${QUIET:-}
USE_VENV=${USE_VENV:-true}

sh_c() {
    if is_dry_run; then
        echo "$@"
    else
        eval "$@"
    fi
}

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
    [ "$DRY_RUN" = true ]
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
        log "Error: python3 is not installed"
        exit 1
    fi

    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        log "Error: Python 3.10 or higher required (found $PYTHON_VERSION)"
        exit 1
    fi
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log "Python $PYTHON_VERSION found, continuing..."

    if ! command_exists pip3 && ! command_exists pip; then
        log "Error: pip is not installed"
        log "On Ubuntu/Debian: apt install python3-pip"
        log "On Fedora: dnf install python3-pip"
        log "On macOS: brew install python3"
        exit 1
    fi

    if [ "$USE_VENV" = true ]; then
        if ! python3 -c "import venv, ensurepip" 2>/dev/null; then
            PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
            log "Error: Python venv and ensurepip modules not available"
            log "On Ubuntu/Debian: sudo apt install python3-venv python3-pip"
            log "On Fedora: sudo dnf install python3-venv python3-pip"
            exit 1
        fi
    fi
}

do_install() {
    log "Creating configuration directory..."
    sh_c "mkdir -p \"${HOME}/.baish\""

    if [ "$USE_VENV" = true ]; then
        log "Setting up a python virtual environment for baish..."
        sh_c "python3 -m venv \"${HOME}/.baish/python-venv\""
        sh_c ". \"${HOME}/.baish/python-venv/bin/activate\""
        sh_c "pip install -q baish"
    else
        log "Installing baish with system python..."   
        sh_c "pip install --user baish"
    fi
    
    if [ ! -f "${HOME}/.baish/config.yaml" ]; then
        log "Creating default configuration..."
        sh_c "cat > \"${HOME}/.baish/config.yaml\" << 'EOF'
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
EOF"
    fi
}

setup_alias() {
    log "Setting up baish alias..."
    SHELL_RC=""
    if [ -n "$BASH_VERSION" ]; then
        SHELL_RC="${HOME}/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="${HOME}/.zshrc"
    fi

    if [ -n "$SHELL_RC" ]; then
        if ! sh_c "grep -q \"alias baish=\" \"$SHELL_RC\" 2>/dev/null"; then
            if [ "$USE_VENV" = true ]; then
                sh_c "echo 'alias baish=\"${HOME}/.baish/python-venv/bin/baish\"' >> \"$SHELL_RC\""
            else
                sh_c "echo 'alias baish=\"baish\"' >> \"$SHELL_RC\""
            fi
            log "Added baish alias to $SHELL_RC"
        fi
    fi
}

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            ;;
        --quiet)
            QUIET=1
            ;;
        --version)
            echo "baish installer version $SCRIPT_VERSION"
            exit 0
            ;;
        --no-venv)
            USE_VENV=false
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

if [ "$USE_VENV" = true ]; then
    log "Using virtual environment"
else
    log "Not using virtual environment"
fi

if [ "$DRY_RUN" = true ]; then
    log "Dry run mode enabled, only echoing commands"
fi

check_dependencies
check_python_requirements
do_install
setup_alias

if [ "$(uname)" = "Linux" ]; then
    log "IMPORTANT!!!: Run the following command to use baish:"
    log "source ~/.bashrc"
    log "This sets up the baish alias in your shell"
elif [ "$(uname)" = "Darwin" ]; then
    log "IMPORTANT!!!: Run the following command to use baish:"
    log "source ~/.zshrc"
    log "This sets up the baish alias in your shell"
elif [ "$USE_VENV" = true ]; then
    log "==> IMPORTANT!!!: Run the following command to use baish:"
    log "==> source ~/.baish/python-venv/bin/activate"
fi

