# black-suggest

GitHub action that suggests edits from the black autoformatter for Python

# Installing

Create and commit `.github/workflows/black-suggest.yml` in your repo.

```yml
name: Run Black on Pull Request

on:
  pull_request:

jobs:
  black-suggest:
    runs-on: ubuntu-latest
    steps:
      # Check out the repository
      - uses: actions/checkout@v2

      # Run the action that comments with suggestions
      - uses: cloudtostreet/black-suggest@v1
        with:
          # The access token is needed to be able to make comments
          access-token: ${{ secrets.GITHUB_TOKEN }}

          # The directory to run the formatter on. "." for everything.
          path: "."
```
