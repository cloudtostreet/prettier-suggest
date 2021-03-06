#!/bin/bash

ACCESS_TOKEN=$1
SOURCE_PATH=$2

# Enter the repo
cd $(dirname $SOURCE_PATH)

# Format the files within SOURCE_PATH that have changed in the pull request
prettier --write $SOURCE_PATH

# Export the changes as a patch file
git diff > $HOME/prettier.patch

# Revert the changes
git checkout -- .

# Apply the changes as comments on the PR
python3 /apply_patches_as_suggestion.py --access-token $ACCESS_TOKEN $HOME/prettier.patch