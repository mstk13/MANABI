# RISC-V コンパイラ実験環境(すべて OSS)
#   gcc-riscv64-linux-gnu / binutils : GNU(GPL) クロスコンパイラ・objdump
#   clang / lld                      : LLVM(Apache-2.0) 別コンパイラで比較
#   qemu-user                        : QEMU(GPL) で RISC-V バイナリを実行・計測
# いずれもオープンソース。プロプライエタリなものは含まない。
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive TZ=Asia/Tokyo

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc-riscv64-linux-gnu \
        g++-riscv64-linux-gnu \
        binutils-riscv64-linux-gnu \
        libc6-dev-riscv64-cross \
        qemu-user \
        qemu-user-static \
        clang \
        lld \
        make \
        python3 \
        file \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
CMD ["bash"]
