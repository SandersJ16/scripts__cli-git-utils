#!/bin/bash

origin_path=$(dirname $0)

while [ ! -d ".git" ] && [ `pwd` != "/" ]; do
    cd ..
done
path=`pwd`
if [ "$path" == "/" ]; then
    echo "fatal: Not in a git repository (or any of the parent directories): .git"
    exit 1
fi

tmp_file=".git-submodule-rm.tmp"
submodule="$1"

if  [ -d "$submodule" ]; then
    url=$(awk -f "$origin_path/submodule_remover.awk" -v submodule_name="$submodule" .gitmodules)
    git submodule deinit "$submodule" -f
    awk -f "$origin_path/submodule_remover.awk" -v submodule_name="$submodule" .gitmodules > "$tmp_file" && mv "$tmp_file" gitmodule.tmp

    url="https://github.com/Laradock/laradock.git"
    line='\s+\w+ ?= ?.*'
    component='[\w+(?: ".*?")?\]\n(?:$line\n?)+'
    pcregrep -M '($component)?\[submodule "(.*?)"\](?:$line\n)*(\s+url ?= ?)'

else
    url=$(awk -f "$origin_path/submodule_remover.awk" -v submodule_name="$submodule" .gitmodules)
fi

#git submodule deinit "$submodule" -f
awk -f "$origin_path/submodule_remover.awk" -v submodule_name="$submodule" .gitmodules > "$tmp_file" && mv "$tmp_file" gitmodule.tmp
awk -f "$origin_path/submodule_remover.awk" -v submodule_name="$submodule" .git/config > "$tmp_file" &&  mv "$tmp_file"  config.tmp
