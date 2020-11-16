import argparse
import json
import os
import subprocess
import sys
import traceback
from pprint import pprint

import requests

from unidiff import PatchSet

COMMENT_TEXT = """The `prettier` formatter suggests these changes. To automatically format your code before committing, consider [enabling `prettier` autoformatting in your editor](https://prettier.io/docs/en/editors.html)."""

BODY_TEMPLATE = """{}

```suggestion
{}
```
"""


def get_changed_files(context, base_ref, head_ref):
    try:
        # Fetch the base and HEAD refs from origin
        command = ["git", "fetch", "origin", base_ref, head_ref]
        print("$", " ".join(command))
        output = subprocess.run(
            command, capture_output=True, cwd=context["repo_path"], check=True
        )

        # Compare base and HEAD to see what's changed between them
        command = [
            "git",
            "diff",
            "--name-only",
            f"origin/{base_ref}..origin/{head_ref}",
        ]
        print("$", " ".join(command))
        output = subprocess.run(
            command, capture_output=True, cwd=context["repo_path"], check=True
        )
    except subprocess.CalledProcessError as e:
        traceback.print_exc()
        print("\nCommand failed with this on stderr: ", e.stderr.decode())
        sys.exit(1)

    # Parse the changed file paths and return a set of them
    return set(
        path.strip()
        for path in output.stdout.decode().split("\n")
        if path.strip() != ""
    )


def get_review_comments(context):
    """
    The API call used for this function is documented here:
    https://docs.github.com/en/rest/reference/pulls#list-review-comments-on-a-pull-request
    """

    pull_request_number = context["pull_request_number"]
    repo = context["github_repository"]
    url = f"https://api.github.com/repos/{repo}/pulls/{pull_request_number}/comments"

    access_token = context["access_token"]
    headers = {
        "Accept": "application/vnd.github.comfort-fade-preview+json",
        "Authorization": f"Bearer {access_token}",
    }

    print(url, headers, sep="\n\n")
    return requests.get(url, headers=headers).json()


def get_outdated_linter_comment_urls(comments, context):
    """
    Returns a list of outdated comment URLs. In particular, returns the comment URLs
    that were created by this script. If there are replies to the comments, they will
    not be deleted.
    """

    comment_ids_with_replies = set()
    for comment in comments:
        comment_id_with_reply = comment.get("in_reply_to_id")

        if comment_id_with_reply is not None:
            comment_ids_with_replies.add(comment_id_with_reply)

    # Include comments that match the bot's template
    comments = filter(lambda comment: COMMENT_TEXT in comment["body"], comments)

    # Exclude comments that have replies
    comments = filter(
        lambda comment: comment["id"] not in comment_ids_with_replies, comments
    )

    # Return just the URLs
    return map(lambda comment: comment["url"], comments)


def delete_comment(url, context):
    """
    The API call used for this function is documented here:
    https://docs.github.com/en/rest/reference/pulls#delete-a-pending-review-for-a-pull-request
    """

    access_token = context["access_token"]
    headers = {
        "Accept": "application/vnd.github.comfort-fade-preview+json",
        "Authorization": f"Bearer {access_token}",
    }

    return requests.delete(url, headers=headers)


def suggest_changes(comment, suggestion, path, begin, end, context):
    """
    The API call used for this function is documented here:
    https://docs.github.com/en/rest/reference/pulls#create-a-review-comment-for-a-pull-request
    """

    pull_request_number = context["pull_request_number"]
    repo = context["github_repository"]
    url = f"https://api.github.com/repos/{repo}/pulls/{pull_request_number}/comments"

    post_body = {
        "body": BODY_TEMPLATE.format(comment, suggestion),
        "commit_id": context["commit_id"],
        "path": path,
        # Represents whether the last line is an addition or deletion. Since we're
        # always reformatting, they will always be additions, so we use "RIGHT"
        "side": "RIGHT",
        "line": end,
        "start_line": begin,
        "start_side": "RIGHT",
    }

    # Single line comments have slightly different requirements
    if begin == end:
        del post_body["start_line"]
        del post_body["start_side"]

    access_token = context["access_token"]
    headers = {
        "Accept": "application/vnd.github.comfort-fade-preview+json",
        "Authorization": f"Bearer {access_token}",
    }

    print("Suggesting:\n", BODY_TEMPLATE.format(comment, suggestion))
    print(url, post_body, headers, sep="\n\n")
    print()
    return requests.post(url, json=post_body, headers=headers)


def parse_suggestions_from_hunk(hunk):
    # Make a list of groups of lines where each line in each group has the same
    # type (either added, removed, or context)
    group_type = None
    groups = []
    added_group_indexes = []
    for line in hunk:
        if line.line_type == group_type:
            groups[-1].append(line)
        else:
            group_type = line.line_type
            groups.append([line])

            # If adding a new group of type 'added', record its index
            if line.line_type == "+":
                added_group_indexes.append(len(groups) - 1)

    suggestions = []
    for added_group_index in added_group_indexes:
        if added_group_index == 0:
            raise Exception("Can't process hunk without leading context: " + str(hunk))

        added_group = groups[added_group_index]

        predecessor_group = groups[added_group_index - 1]
        predecessor_group_type = predecessor_group[0].line_type

        # If the predecessor group is a removed group, use its start and end
        # lines as the ones to comment over
        if predecessor_group_type == "-":
            source_start = predecessor_group[0].source_line_no
            source_end = predecessor_group[-1].source_line_no
            suggestion_lines = added_group
        elif predecessor_group_type == " ":
            # If the predecessor group is context (i.e., unchanged lines),
            # just comment over the last line in that group
            source_start = predecessor_group[-1].source_line_no
            source_end = predecessor_group[-1].source_line_no

            # Make sure to include the line we're commenting on in the
            # suggestion so it doesn't get deleted
            suggestion_lines = [predecessor_group[-1], *added_group]
        else:
            raise Exception(
                f"Invariant violated. Consecutive '+' groups at indices "
                f"{added_group_index - 1}, {added_group_index}:\n"
                f"{''.join(line.value for line in predecessor_group)}\n"
                f"{''.join(line.value for line in added_group)}"
            )

        # Join all lines and remove trailing newline
        suggestion = "".join(line.value for line in suggestion_lines)[:-1]
        suggestions.append((source_start, source_end, suggestion))

    return suggestions


def suggest_all_changes(diff_path, context, changed_files=[]):
    patch_set = PatchSet.from_filename(diff_path)

    suggestions = []
    for patched_file in patch_set.modified_files:
        path = os.path.relpath(patched_file.path, context["repo_path"])

        if path not in changed_files:
            continue

        for hunk in patched_file:
            suggestions.extend(
                (path, *partial_suggestion)
                for partial_suggestion in parse_suggestions_from_hunk(hunk)
            )

    print(f"Making {len(suggestions)} on the pull request")

    last_path = None
    for path, begin, end, suggestion in suggestions:
        if last_path != path:
            print(f"Making suggestions on {path}")
            last_path = path

        response = suggest_changes(COMMENT_TEXT, suggestion, path, begin, end, context)

        print("Got response", response)
        pprint(response.__dict__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply a diff.")
    parser.add_argument(
        "--access-token",
        help="The GitHub access token. In a GitHub workflow, pass {{secrets.GITHUB_TOKEN}}",
        required=True,
    )
    parser.add_argument("path", help="Path to a unified diff to apply to the review")

    args = parser.parse_args()

    with open(os.environ["GITHUB_EVENT_PATH"], "r") as github_event_file:
        github_event = json.load(github_event_file)

    print("Reading GitHub event file: ")
    pprint(github_event)

    context = {
        "access_token": args.access_token,
        "github_repository": os.environ["GITHUB_REPOSITORY"],
        "pull_request_number": github_event["pull_request"]["number"],
        "commit_id": github_event["pull_request"]["head"]["sha"],
        "repo_path": os.environ["GITHUB_WORKSPACE"],
    }

    print("Getting old suggestions...")
    comments = get_review_comments(context)
    outdated_comment_urls = get_outdated_linter_comment_urls(comments, context)

    print("Deleting old suggestions...")
    for comment_url in outdated_comment_urls:
        delete_comment(comment_url, context)

    print("Getting changed files...")
    changed_files = get_changed_files(
        context,
        github_event["pull_request"]["base"]["ref"],
        github_event["pull_request"]["head"]["ref"],
    )
    pprint(changed_files)

    print("Making suggestions on pull request...")
    suggest_all_changes(args.path, context, changed_files)
