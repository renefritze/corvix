<!-- markdownlint-disable MD041 -->

```{highlight} shell

```

<!-- markdownlint-enable MD041 -->

# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs at <https://github.com/renefritze/corvix/issues>.

If you are reporting a bug, please include:

- Your operating system name and version.
- Any details about your local setup that might be helpful in troubleshooting.
- Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

### Write Documentation

corvix could always use more documentation, whether as part of the
official corvix docs, in docstrings, or even on the web in blog posts,
articles, and such.

### Submit Feedback

The best way to send feedback is to file an issue at <https://github.com/renefritze/corvix/issues>.

If you are proposing a feature:

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- Remember that this is a volunteer-driven project, and that contributions are welcome :)

## Get Started

Ready to contribute? Here's how to set up {}`corvix` for local development.

1. Fork the {}`corvix` repo on GitHub.

2. Clone your fork locally:

   ```bash
   git clone https://github.com/renefritze/corvix
   ```

3. Install dependencies with `uv`:

   ```bash
   cd corvix/
   uv sync
   ```

4. Prepare local runtime config and Docker secrets for end-to-end testing:

   ```bash
   cp config/corvix.example.yaml config/corvix.yaml
   cp secrets/github_token.txt.example secrets/github_token.txt
   cp secrets/postgres_password.txt.example secrets/postgres_password.txt
   cp secrets/database_url.txt.example secrets/database_url.txt
   ```

5. Create a branch for local development:

   ```bash
   git checkout -b name-of-your-bugfix-or-feature
   ```

   Now you can make your changes locally.

6. Make sure you have pre-commit installed and activated:

   ```bash
   pre-commit install
   pre-commit run --all-files
   ```

7. Commit your changes and push your branch to GitHub:

   ```bash
   git add .
   git commit -m "Your detailed description of your changes."
   git push origin name-of-your-bugfix-or-feature
   ```

8. Submit a pull request through the GitHub website.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.md.
3. The pull request should work for multiple Python versions.

## Tips

To run a subset of tests:

```bash
uv run pytest tests/test_corvix.py
```

To run the local stack for manual verification:

```bash
docker compose up --build
```

## Deploying

TBD
