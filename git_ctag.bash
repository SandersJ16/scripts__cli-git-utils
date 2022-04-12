#!/bin/bash

# Exclude a list of default folder and files from getting indexed
exclude_defaults=true
# If true then the ctags command will be printed instead of run
echo_ctags_command=false
# If true then error messages won't be suppressed
verbose=false
# If symlinks should be followed
follow_symlinks=false

for input in "$@"; do
  if  [[ "$input" == "-V" ]]; then
    exclude_defaults=false
  elif [[ "$input" == "-p" ]]; then
    echo_ctags_command=true
  elif [[ "$input" == "-v" ]]; then
    verbose=true
  elif [[ "$input" == "-l" ]]; then
    follow_symlinks=true
  fi
done

while [ ! -d ".git" ] && [ `pwd` != "/" ]; do
    cd ..
done
path=`pwd`
if [ "$path" == "/" ]; then
    echo "fatal: Not in a git repository (or any of the parent directories): .git"
    exit 1
fi

if [ $follow_symlinks == true ]; then
  links_command="--links=yes"
else 
  links_command="--links=no"
fi

delete_command="rm \".tags\""
ctags_command="ctags $links_command -R -o \".tags\""
if [ $exclude_defaults = true ]; then
  #list of directories and file types to exclude by default, will not be excluded if -V flag is used
  declare -a exclude_dirs=(".git" "node_modules" "log")
  declare -a exclude_files=("*.min.js" "*.mo" "*.po" "jit-yc.js" "*.min.css" "*bundle.js")

  for exclude_dir in "${exclude_dirs[@]}"; do
    ctags_command="$ctags_command --exclude=\"$exclude_dir\""
  done

  for exclude_file in "${exclude_files[@]}"; do
    ctags_command="$ctags_command --exclude=\"$exclude_file\""
  done
fi
ctags_command="$ctags_command *"


if [ $verbose == false ]; then
    delete_command="$delete_command 2>/dev/null"
    ctags_command="$ctags_command 2>/dev/null"
fi


if [ $echo_ctags_command == true ]; then
  echo "$delete_command"
  echo "$ctags_command"
else
  echo "Generating CTags in file $path/.tags"

  eval "$delete_command"
  eval "$ctags_command"

  echo "Ctags Generated"
fi

