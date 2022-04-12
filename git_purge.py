#!/usr/bin/env python

from json import loads as parse_json
from subprocess import check_output, check_call, DEVNULL
from os import getcwd, listdir, chdir
from argparse import ArgumentParser
from collections import namedtuple

from signal import SIGINT


def parse_arguments():
    def postive_integer(value):
        i_value = int(value)
        if i_value < 0:
            raise argparse.ArgumentTypeError("%s is invalid, must be a postive int value" % value)
        return i_value

    default_base_branches = ["master", "main", "dev", "develop", "test", "stage"]
    core_base_branches = default_base_branches

    parser = ArgumentParser(description="Remove local branches merged via PR in github")
    parser.add_argument('--list', '-l', action="store_true", default=False,
                        help="prints all branches that would be deleted if command was check_output")
    parser.add_argument('--base', '-b', metavar='BRANCH', action="append", dest="base_branches",
                        help=f"base reference branches local branches must have been merged with (defaults: {', '.join(default_base_branches)})")
    # Verbose
    parser.add_argument('--verbose', '-v', action="store_true", default=True,
                        help="prints all branches that are deleted (default True)")
    parser.add_argument('--quiet', '-q', dest='verbose', action="store_false",
                        help="don't print any output")
    # Interactive
    parser.add_argument('--interactive', '-i', action="store_true", default=False,
                        help="interactive mode. Will ask for confirmation before deleting each branch")
    parser.add_argument('--non-interactive', dest='interactive', action="store_false",
                        help="opposite of --interactive")
    # Protect
    parser.add_argument('--protect', '-p', metavar="BRANCH", action="append", dest='protected', default=[],
                        help="specify branches that can not be deleted (see --delete-core-branches for branches protected by default)")
    parser.add_argument('--delete-core-branches', action="store_true", default=False,
                        help=f"allow deletion of core branches. The following are considered core branches: {''.join(core_base_branches)}")
    # Recursive
    parser.add_argument('--recursive', '-r', action="store_true", default=False,
                        help="delete branch if any branch it has been merged into has been merged into one of the base branches (recursively)")
    parser.add_argument('--non-recursive', '-n', dest='recursive', action="store_false",
                        help="opposite of --recursive")
    parser.add_argument('--recursive-limit', type=postive_integer, default=0,
                        help="maximum number of parent branches a branch can be away from for recursive delete (set 0 for unlimited, this is the default)")

    arguments = parser.parse_args()
    arguments.default_base_branches = default_base_branches
    if not arguments.base_branches:
        arguments.base_branches = default_base_branches

    if not arguments.delete_core_branches:
        arguments.protected += core_base_branches

    return arguments

def is_git_directory():
    while ".git" not in listdir() and getcwd() != '/':
        chdir("..")
    return getcwd() != '/'

def get_local_branches():
    all_branch_output = check_output(["git", "for-each-ref", "--format='%(refname:short)'", "refs/heads"]).decode("utf-8")
    return [branch for branch in [b.strip("'") for b in all_branch_output.split("\n")] if branch]

def get_current_branch():
    return check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode("utf-8").strip()

def delete_branch(branch, verbose=True):
    stdout = None if verbose else DEVNULL
    check_call(["git", "branch", "-D", branch], stdout=stdout)

def call_gh_command(branches):
    github_search_command = "is:merged"
    for branch in branches:
        github_search_command += " head:" + branch
    gh_command = ['gh', 'pr', 'list', f"--search={github_search_command}", '--json=baseRefName,headRefName', f'-L{len(branches)}']
    return check_output(gh_command).decode('utf-8')

def get_pr_merged_branches(branches):
    remote_merged_branches_json = call_gh_command(branches)
    merged_branches = {}
    for remote_merged_branch in parse_json(remote_merged_branches_json):
        head = remote_merged_branch["headRefName"]
        base = remote_merged_branch["baseRefName"]
        if head in branches:
            if head not in merged_branches:
                merged_branches[head] = []
            merged_branches[head].append(base)
    return merged_branches


def list_branches(branches):
    for head, bases in branches.items():
        print(f"{head} (merged into: {', '.join(bases)})")


def get_branches_to_delete(merged_branches, base_branches, recursive=False, recursive_limit=0):
    branches_to_delete = {}
    if recursive:
        dp, _ = _get_branches_to_delete_recursive(merged_branches, base_branches, max_depth=recursive_limit)
        print(dp)
        x = []
        for branch, (depth, sub_merged) in dp.items():
            if branch in merged_branches and depth != None and (recursive_limit == 0 or dp[branch][0] <= recursive_limit):
                branches_to_delete[branch] = dp[branch][1]

    else:
        for head, bases in merged_branches.items():
            merged_bases = set(bases) & set(base_branches)
            if merged_bases:
                branches_to_delete[head] = merged_bases

    return branches_to_delete


def _get_branches_to_delete_recursive(merged_branches, base_branches, should_delete_branch={}, already_seen=[], depth=1, max_depth=0):
    for head, bases in merged_branches.items():
        if head in should_delete_branch:
            continue
        else:
            already_seen.append(head)

            merged_bases = set(bases) & set(base_branches)
            if merged_bases:
                should_delete_branch[head] = 1, merged_bases
            else:
                for parent_branch in bases:
                    if parent_branch in should_delete_branch:
                        if should_delete_branch[parent_branch]:
                            should_delete_branch[head] = should_delete_branch[parent_branch][0] + 1, should_delete_branch[parent_branch][1]

                    elif max_depth == 0 or depth <= max_depth:
                        parent_branches_to_check = set(bases) - set(already_seen)
                        if parent_branches_to_check:
                            parent_merged_branches = get_pr_merged_branches(set(bases) - set(already_seen))
                            should_delete_branch, already_seen = _get_branches_to_delete_recursive(parent_merged_branches, base_branches, should_delete_branch, already_seen, depth + 1, max_depth)
                            if parent_branch in should_delete_branch:
                                should_delete_branch[head] = should_delete_branch[parent_branch][0] + 1, should_delete_branch[parent_branch][1]
                                break

                if not head in should_delete_branch:
                    should_delete_branch[head] = None, []

    return should_delete_branch, already_seen


def delete_branches(branches, interactive, verbose):
    current_branch = get_current_branch()

    for head, bases in branches.items():
        if head == current_branch:
            if verbose:
                print("Skipping currently checked out branch: " + head)
            continue

        if interactive:
            print(f"Delete branch {head} (merged into: {', '.join(bases)})?")
            should_delete = input('y/n?: ')
            while (should_delete not in ['y', 'n']):
                should_delete = input("Please enter 'y' or 'n': ")
            if should_delete == 'n':
                continue

        delete_branch(head, verbose)


if __name__ == "__main__":
    try:
        arguments = parse_arguments()

        if not is_git_directory():
            print("fatal: Not in a git repository (or any of the parent directories): .git")
            exit(1)

        local_branches = get_local_branches()
        merged_branches = get_pr_merged_branches(local_branches)

        # Exclude all protected branches
        [merged_branches.pop(key, None) for key in arguments.protected]

        # Get branches that should be deleted
        branches_to_delete = {}
        for head, bases in merged_branches.items():
            merged_bases = set(bases) & set(arguments.base_branches)
            if merged_bases:
                branches_to_delete[head] = merged_bases

        if (arguments.list):
            list_branches(branches_to_delete)
        else:
            delete_branches(branches_to_delete, interactive=arguments.interactive, verbose=arguments.verbose)

    except KeyboardInterrupt:
        exit(SIGINT)
