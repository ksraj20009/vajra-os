# ~/.bashrc — Vajra OS default user bashrc

# History settings
HISTCONTROL=ignoreboth
HISTSIZE=1000
HISTFILESIZE=2000
HISTTIMEFORMAT="%F %T "

# Shell options
shopt -s checkwinsize
shopt -s histappend
shopt -s cdspell

# Aliases
alias ls='ls --color=auto'
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias grep='grep --color=auto'
alias ..='cd ..'
alias ...='cd ../..'

# Vajra-specific aliases
alias vajra-mode='vajra-mode'
alias vajra-help='vajra-help'
alias buddhi='python3 /opt/vajra/ai/buddhi.py'
alias update='sudo apt update && sudo apt upgrade'
alias install='sudo apt install'

# Safety aliases (beginner mode)
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

# Prompt
if [ "$color_prompt" = yes ]; then
    PS1='\[\e[1;33m\]vajra\[\e[0m\]@\[\e[1;33m\]\h\[\e[0m\]:\[\e[1;32m\]\w\[\e[0m\]$ '
else
    PS1='vajra@\h:\w$ '
fi

# Load Vajra environment
export VAJRA_VERSION="1.0"
export BUDDHI_HOME="/opt/vajra/ai"
export PATH="$PATH:/opt/vajra/bin"

# Buddhi AI quick command
if [ -f /opt/vajra/ai/buddhi.py ]; then
    buddhi() {
        python3 /opt/vajra/ai/buddhi.py "$@"
    }
fi

# Welcome
if [ -f /etc/motd ]; then
    cat /etc/motd
fi
