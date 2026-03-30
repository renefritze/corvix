<!-- markdownlint-disable MD041 -->

```{highlight} shell

```

<!-- markdownlint-enable MD041 -->

# Installation

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)

## From source (recommended for development)

The sources for corvix can be downloaded from the [github repo]

You can either clone the public repository:

```{code-block} console

git clone https://github.com/renefritze/corvix.git

```

Or download the [tarball]:

```{code-block} console

curl -OJL https://github.com/renefritze/corvix/tarball/main

```

Once you have a copy of the source, you can install it with:

```{code-block} console

uv sync

```

Run commands inside the project environment with:

```{code-block} console

uv run corvix --help

```

[github repo]: https://github.com/renefritze/corvix
[tarball]: https://github.com/renefritze/corvix/tarball/main
