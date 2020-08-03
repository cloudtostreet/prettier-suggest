#!/bin/bash

ACCESS_TOKEN=$1
SOURCE_PATH=$2

cd $(dirname $SOURCE_PATH)
prettier $SOURCE_PATH --write
git diff > prettier.patch
python3 /apply_patches_as_suggestion.py --access-token $ACCESS_TOKEN $HOME/prettier.patch