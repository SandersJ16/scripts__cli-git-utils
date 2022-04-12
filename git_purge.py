#!/usr/bin/env python

from json import loads as parse_json
from subprocess import check_output, check_call, DEVNULL
from os import getcwd, listdir, chdir
from argparse import ArgumentParser
from collections import namedtuple
from signal import SIGINT


RECURSION_LIMIT = 10

def parse_arguments():
    def recursion_integer(value):
        i_value = int(value)
        if i_value < 1 or i_value > RECURSION_LIMIT:
            raise argparse.ArgumentTypeError("%s is invalid, must be a postive int value (Maximum %i)" % value, RECURSION_LIMIT)
        return i_value

    default_base_merge_branches = ["master", "main", "dev", "develop", "test", "stage"]
    core_base_branches = default_base_merge_branches

    parser = ArgumentParser(description="Remove local branches merged via PR in github")
    parser.add_argument('--list', '-l', action="store_true", default=False,
                        help="prints all branches that would be deleted if command was check_output")
    parser.add_argument('--base', '-b', metavar='BRANCH', action="append", dest="base_merge_branches",
                        help=f"base reference branches local branches must have been merged with (defaults: {', '.join(default_base_merge_branches)})")
    # Verbose
    parser.add_argument('--verbose', '-v', action="store_true", default=False,
                        help="prints all branches that are deleted (default True)")
    parser.add_argument('--quiet', '-q', action="store_true", default=False,
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
    parser.add_argument('--recursive-limit', type=recursion_integer, default=RECURSION_LIMIT,
                        help=f"maximum number of parent branches a branch can be away from for recursive delete. Maximum value of {RECURSION_LIMIT}, this is the default value")

    arguments = parser.parse_args()
    arguments.default_base_merge_branches = default_base_merge_branches
    if not arguments.base_merge_branches:
        arguments.base_merge_branches = default_base_merge_branches

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

def delete_branch(branch, quiet=False):
    stdout = DEVNULL if quiet else None
    check_call(["git", "branch", "-D", branch], stdout=stdout)

def call_gh_command(branches):
    """
    Invoke gh (github CLI tool) command for fetching all allready merged PRs where the branches received were the head branches

    Args:
        branches: A list of branches to check

    Returns:
        JSON list of all the passed in branches merge via PR. JSON list will contain JSON
        objects containing the baseRefName and headRefName of the branches involved in the PR.
    """
    github_search_command = "is:merged"
    for branch in branches:
        github_search_command += " head:" + branch
    gh_command = ['gh', 'pr', 'list', f"--search={github_search_command}", '--json=baseRefName,headRefName', f'-L{len(branches)}']
    return check_output(gh_command).decode('utf-8')

def branches_merged_via_github_pr(branches, verbose=False):
    """
    Get the branches that have been merged via PR in Github

    Args:
        branches: A list of branches to check

    Returns:
        Dictionary with key for all branches that have been merged with a
        value of a list of all the branches that branch was merged into via PR
    """
    if verbose:
        print("Checking Github for merged PRs for %i branches" % len(branches))

    remote_merged_branches_json = call_gh_command(branches)
    pr_merged_branches = {}
    remote_merged_branches = parse_json(remote_merged_branches_json)

    if verbose:
        print("Found %i merged PRs" % len(remote_merged_branches))

    for remote_merged_branch in remote_merged_branches:
        head = remote_merged_branch["headRefName"]
        base = remote_merged_branch["baseRefName"]
        if head in branches:
            if head not in pr_merged_branches:
                pr_merged_branches[head] = []
            pr_merged_branches[head].append(base)

    return pr_merged_branches


def list_branches(branches, verbose=False):
    for head, bases in branches.items():
        output = head
        if verbose:
            output += f" (merged into: {', '.join(bases)})"
        print(output)


def get_branches_to_delete(merged_head_branches, base_merge_branches, recursive=False, recursive_limit=0):
    if recursive:
        return get_branches_to_delete_recursive(merged_head_branches, base_merge_branches, recursive_limit)
    else:
        return get_branches_to_delete_non_recursive(merged_head_branches, base_merge_branches)

def get_branches_to_delete_non_recursive(merged_head_branches, base_merge_branches):
    """
    Filter `merged_head_branches` to branches that should be deleted because
    they have directly been merged into a branch in `base_merge_branches`

    Args:
        merged_head_branches:   A dictionary with keys of git branches and values of a
                                    list of all branches the key branch has been merged into
        base_merge_branches:    A list of branches to check if `merged_head_branches` have
                                    been merged into

    Return:
        A dictionary with keys of git branches in `merged_head_branches` that have been merged
        into at least one of the branches in `base_merge_branches` and values of a list of all
        the branches in `base_merge_branches` the key branch has been merged into.
    """
    branches_to_delete = {}
    for head, bases in merged_head_branches.items():
        merged_bases = set(bases) & set(base_merge_branches)
        if merged_bases:
            branches_to_delete[head] = merged_bases

    return branches_to_delete


def get_branches_to_delete_recursive(merged_head_branches, base_merge_branches, recursive_limit):
    """
    Filter `merged_head_branches` to branches that should be deleted because they have
    been merged into a branch in `base_merge_branches` or have other branches they have
    been merged into who have been merged into `base_merge_branches` recursively

    Args:
        merged_head_branches:   A dictionary with keys of git branches and values of a
                                    list of all branches the key branch has been merged into
        base_merge_branches:    A list of branches to check if `merged_head_branches` have
                                    been merged into
        recrusive_limit:        The maximum recursion allowed to check if branch has been
                                    merged into one of `base_merge_branches`

    Return:
        A dictionary with keys of git branches in `merged_head_branches` that have been merged
        into at least one of the branches in `base_merge_branches` and values of a list of all
        the branches in `base_merge_branches` the key branch has been merged into.
    """

    branches_to_delete = {}
    should_delete, _ = _get_branches_to_delete_recursive(merged_head_branches, base_merge_branches)
    for branch, (depth, sub_merged) in should_delete.items():
        if branch in merged_head_branches and depth != None and should_delete[branch][0] <= recursive_limit:
            branches_to_delete[branch] = should_delete[branch][1]

    return branches_to_delete

def _get_branches_to_delete_recursive(merged_head_branches, base_merge_branches, should_delete_branch={}, already_seen=[], depth=1):
    """
    A Recursive function for checking if branches in `merged_head_branches` have been merged into one of `base_merge_branches`.
    This function will function with circular merges

    Args:
        merged_head_branches:   A dictionary with keys of git branches and values of a
                                    list of all branches the key branch has been merged into
        base_merge_branches:    A list of branches to check if `merged_head_branches` have
                                    been merged into
        should_delete_branch:   The current calculated return value of the parent recursion (see return value)
        already_seen:           A list of all branches we have already seen at least once in this recursion
                                    (needed to prevent circular merge paths from infinitely recursing)
        depth  :                The current recursion depth we're at

    Returns:
        A dictionary with keys of git branches and values of a tuple containing:
            (
            The number of merges away a branch is from being merged
                into a `base_merge_branches` (or None if it has not been),

            A list of all the branches in `base_merge_branches` the key branch
                or any of the branches it has been merged into have been merged into.
            )
    """
    for head, bases in merged_head_branches.items():
        if head in should_delete_branch:
            continue
        else:
            already_seen.append(head)
            merged_bases = set(bases) & set(base_merge_branches)
            if merged_bases:
                should_delete_branch[head] = 1, merged_bases
            else:
                for merge_ancestor_branch in bases:
                    # If we have already seen this ancestor branch
                    if merge_ancestor_branch in should_delete_branch:
                        if should_delete_branch[merge_ancestor_branch]:
                            should_delete_branch[head] = should_delete_branch[merge_ancestor_branch][0] + 1, should_delete_branch[merge_ancestor_branch][1]

                    elif depth <= RECURSION_LIMIT:
                        if set(bases) - set(already_seen):
                            parent_merged_branches = branches_merged_via_github_pr(set(bases) - set(already_seen))
                            should_delete_branch, already_seen = _get_branches_to_delete_recursive(parent_merged_branches, base_merge_branches, should_delete_branch, already_seen, depth + 1)
                            if merge_ancestor_branch in should_delete_branch:
                                should_delete_branch[head] = should_delete_branch[merge_ancestor_branch][0] + 1, should_delete_branch[merge_ancestor_branch][1]
                                break

                if not head in should_delete_branch:
                    should_delete_branch[head] = None, []

    return should_delete_branch, already_seen


def delete_branches(branches, interactive, quiet=False):
    current_branch = get_current_branch()

    for head, bases in branches.items():
        if head == current_branch:
            if not quiet:
                print("Skipping currently checked out branch: " + head)
            continue

        if interactive:
            print(f"Delete branch {head} (merged into: {', '.join(bases)})?")
            should_delete = input('y/n?: ')
            while (should_delete not in ['y', 'n']):
                should_delete = input("Please enter 'y' or 'n': ")
            if should_delete == 'n':
                continue

        delete_branch(head, quiet)


if __name__ == "__main__":
    try:
        arguments = parse_arguments()

        if not is_git_directory():
            print("fatal: Not in a git repository (or any of the parent directories): .git")
            exit(1)

        local_branches = get_local_branches()
        pr_merged_branches = branches_merged_via_github_pr(local_branches, arguments.verbose)

        # Exclude all protected branches
        [pr_merged_branches.pop(key, None) for key in arguments.protected]

        # Get branches that should be deleted
        branches_to_delete = get_branches_to_delete(pr_merged_branches, arguments.base_merge_branches, arguments.recursive, arguments.recursive_limit)

        if (arguments.list):
            list_branches(branches_to_delete, verbose=arguments.verbose)
        else:
            delete_branches(branches_to_delete, interactive=arguments.interactive, quiet=arguments.quiet)

    except KeyboardInterrupt:
        exit(SIGINT)
