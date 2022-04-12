#!/bin/bash

# Takes exactly one argment, throw exception otherwise (may update to do multiple later)
if [ -z "$1" ]; then
    echo "No argument supplied"
    exit 1
fi

exclude_string="$1"

# If we are given a file or a directory, then add that specfic file/directory
# to the exclude otherwise, add the input string's raw value to the exclude file
is_dir=false
if  [[ -d "$exclude_string" ]]; then
    is_dir=true
fi

add_path=false
if [[ -f "$exclude_string" ]] || [ "$is_dir" = true ]; then
    cd "$(dirname "$exclude_string")"
    exclude_string=`basename $exclude_string`
    add_path=true
fi

# Find where the root of the git repo (exits if not in a git repo
while [ ! -d ".git" ] && [ `pwd` != "/" ]; do
    if [ "$add_path" = true ]; then
        exclude_string="${PWD##*/}/$exclude_string"
    fi
    cd ..
done
path=`pwd`
if [ "$path" == "/" ]; then
    echo "fatal: Not in a git repository (or any of the parent directories): .git"
    exit 1
fi

# If it was a file or directory prepend a forward slash making it exactly that file/directory
if [ "$add_path" = true ]; then
    exclude_string="/$exclude_string"
fi

# If it was a directory append a forward slash if it doesn't have one indicating it's a directory
if [ "$is_dir" = true ] && [[ ! "$exclude_string" == */ ]]; then
    exclude_string="$exclude_string/"
fi

# Check if the exclude value is already excluded, if not add it ot the exclude file
if grep -Fxq "$exclude_string" "$path/.git/info/exclude"; then
    echo "$exclude_string is already excluded"
    exit 2
else
    echo "$exclude_string" >> "$path/.git/info/exclude"
fi
