# Dockerfile

# Use the official Ubuntu 24.04 base image
FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# Set the default shell for the container
SHELL ["/bin/bash", "-c"]

# Clang version should always match what is used in CI
ENV DEBIAN_FRONTEND=noninteractive \
    CLANG_VERSION=20

# note it's not necessary to create a non-root user, devcontainer will do it for you
# https://code.visualstudio.com/remote/advancedcontainers/add-nonroot-user#_creating-a-nonroot-user

# Install necessary packages for C++ development and other tools
RUN apt update && \
    apt install --no-install-recommends -y \
        build-essential cmake curl gdb git ninja-build pkg-config pre-commit \
        python3-minimal python3-pip python3-venv wget zip \
    && wget -O /etc/apt/trusted.gpg.d/apt.llvm.org.asc https://apt.llvm.org/llvm-snapshot.gpg.key \
    && echo "deb https://apt.llvm.org/noble/ llvm-toolchain-noble-${CLANG_VERSION} main" >> /etc/apt/sources.list.d/llvm.list \
    && apt update && apt install --no-install-recommends -y "clang-${CLANG_VERSION}" \
    && update-alternatives --install /usr/bin/clang clang "/usr/bin/clang-${CLANG_VERSION}" 100 \
    && update-alternatives --install /usr/bin/clang++ clang++ "/usr/bin/clang++-${CLANG_VERSION}" 100 \
    && apt autoremove -y && apt clean -y && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /workspace
USER vscode
