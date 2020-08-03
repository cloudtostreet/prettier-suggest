# prettier-suggest

GitHub action that suggests edits from the Prettier autoformatter

# Installing

Create and commit `.github/workflows/prettier-suggest.yml` in your repo.

```yml
name: Run Prettier on Pull Request

on:
  pull_request:

jobs:
  prettier-suggest:
    runs-on: ubuntu-latest
    steps:
      # Check out the repository
      - uses: actions/checkout@v2

      # Run the action that comments with suggestions
      - uses: cloudtostreet/prettier-suggest@v1
        with:
          # The access token is needed to be able to make comments
          access-token: ${{ secrets.GITHUB_TOKEN }}

          # The directory to run the formatter on. "." for everything.
          path: "."
```
