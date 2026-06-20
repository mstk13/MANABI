# RISC-V コンパイラ実験(コンテナ内実行)。docker と docker compose だけで動く。
#   make build     イメージをビルド(初回)
#   make compare   コンパイラ/ISA拡張で命令数がどう変わるか実測・比較
#   make run       sumloop を -O0/-O2 でビルドし qemu で実行時間を比較
#   make shell     コンテナ内シェル(自由に riscv64-linux-gnu-gcc などを試す)
export HOST_UID := $(shell id -u)
export HOST_GID := $(shell id -g)
RUN := docker compose run --rm riscv

.DEFAULT_GOAL := help
.PHONY: help build compare run shell versions
help:
	@echo "make build / compare / run / shell / versions"
	@echo "  compare: 分岐 vs Zicond, popcount vs Zbb, -O0 vs -O2 の命令数を比較"
	@echo "  run    : -O0 と -O2 の実行時間を QEMU で比較"
build:
	docker compose build
versions:
	$(RUN) bash -lc 'riscv64-linux-gnu-gcc --version | head -1; clang --version | head -1; qemu-riscv64 --version | head -1'
compare:
	$(RUN) python3 compare.py
run:
	$(RUN) bash -lc '\
	  for O in O0 O2; do \
	    riscv64-linux-gnu-gcc -$$O -march=rv64gc -static examples/driver.c examples/sumloop.c -o /tmp/s_$$O ; \
	    printf "[-%s] " $$O ; \
	    /usr/bin/time -f "real %es" qemu-riscv64 /tmp/s_$$O >/dev/null ; \
	  done'
shell:
	$(RUN) bash
