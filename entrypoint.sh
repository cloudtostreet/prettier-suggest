#!/bin/bash

ACCESS_TOKEN=$1
SOURCE_PATH=$2

black --diff $SOURCE_PATH > $HOME/black.patch
python /apply_patches_as_suggestion.py --access-token $ACCESS_TOKEN $HOME/black.patch