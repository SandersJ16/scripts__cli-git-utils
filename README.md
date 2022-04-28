# Git commandline utilities

Utility scripts for additional git functionality.

Git has built in support for adding custom commands by adding commands named with the format `git-X` to your path, so it is easy to add these as extra git commands.
- Download script and make it executable
- Rename script to `git-X` (so `git-purge` for `git_purge.py` as an example).
- Add the script to a directory in your path (`/usr/bin` for example. Note that creating a local `bin` directory located in your home directory is usually a better solution than adding directly to system directories)
- You should now be able to call the command in any git repository with `git X`

---

### git_activity.bash
See nicely formatted display of all commits in the current repo. Display will be:
How Long ago commit was, commit ID - User who made the commit, Branch commit was made into, Commit message
ex.
```
 6 days ago 89d30078a - [Justin L Sanders] (origin/master): Remove uneeded newlines from test.sh
```

**Options**
```
-h --help       Display Usage information
-c --count NUM  Only show the last NUM commits
   --fetch      Fetch all repos from remote prior running command
   --no-color   Print without any colour
```

### git_ctag.bash
A simple uptility to run [`ctags`](http://ctags.sourceforge.net/) for the current git repo. 
This will exculde the following files and folders by default: `.git`, `node_modules`, `log`, `*.min.js`, `*.mo`, `*.po`, `*.min.css`, `*bundle.js"`

**Options**
```
-V   Also index the default excluded options
-p   Echo commands it would run instead of running them
-v   Verbose, will print output of all run commands (default is supressed)
-f   Follow symlinks, default is false. Should only be passed if symlinks reference files/folders internal to the git repo

```

---

### git_exclude.bash
Ignore a file/directory in git locally (ie. without updating .gitignore), this accomplishes this by updating the `.git/info/excludes` file. Useful for local testing or IDE/OS generated files/directories (also consider setting up a [global gitinore](https://gist.github.com/subfuzion/db7f57fff2fb6998a16c) file).

**Usage**
```bash
# Will exclude the file/directory. This command will resolve the full file path relative to the current git directory
./git_exclude.bash  ./some/file_or_directory  

# Also supports all patterns supported by .gitignore
./git_exlude.bash  "*.log"
```

---

### git_purge.py
Utility for removing all local branches that have already been merged via PR in Github. This is useful for cleaning up your local branches, particularily if you use squash commits or git flow. This requires the github command line utility be installed and configured. This tool is designed for repos that use Github pull requests for all changes.

(*NOTE:* I've only tested this with Python 3)


**Usage**
```
git-purge [-h] [--list] [--base BRANCH] [--verbose] [--quiet]
          [--interactive] [--non-interactive] [--protect BRANCH]
          [--delete-core-branches] [--recursive] [--non-recursive]
          [--recursive-limit RECURSIVE_LIMIT]
```

**Options**
```
  -h, --help            Show this help message and exit
  --list, -l            Prints all branches that would be deleted if command
                          was check_output
  --base BRANCH, -b BRANCH
                        Base reference branches local branches must have been
                          merged with (defaults: master, main, dev, develop,
                          test, stage)
  --verbose, -v         Prints all branches that are deleted (default True)
  --quiet, -q           Don't print any output
  --interactive, -i     Interactive mode. Will ask for confirmation before
                          deleting each branch
  --non-interactive     Opposite of --interactive
  --protect BRANCH, -p BRANCH
                        Specify branches that can not be deleted (see
                          --delete-core-branches for branches protected by
                          default)
  --delete-core-branches
                        Allow deletion of core branches. The following are
                          considered core branches:
                          master main dev develop test stage
  --recursive, -r       Delete branch if any branch it has been merged into
                         has been merged into one of the base branches
                         (recursively)
  --non-recursive, -n   Opposite of --recursive
  --recursive-limit RECURSIVE_LIMIT
                        Maximum number of parent branches a branch can be away
                          from for recursive delete. Maximum value of 10, this
                          is the default value
```

---

### git_rm_submodule.bash (DO NOT USE/INCOMPLETE)
Simple script to remove submodules from the current repo since git decided not to implement this command. Currently this dependes on `pcre` so it is not very portable. 

**Usage**
```
git submodule rm SUBMODULE_DIR
```
