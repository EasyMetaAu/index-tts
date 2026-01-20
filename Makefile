.PHONY: help up up-cpu down down-cpu restart restart-cpu logs logs-cpu build build-cpu rebuild rebuild-cpu ps ps-cpu shell shell-cpu clean clean-cpu

help:
	@echo "IndexTTS2 Docker 命令:"
	@echo ""
	@echo "启动/停止:"
	@echo "  make up          - 启动 GPU 版本"
	@echo "  make up-cpu      - 启动 CPU 版本"
	@echo "  make down        - 停止 GPU 容器"
	@echo "  make down-cpu    - 停止 CPU 容器"
	@echo ""
	@echo "重启（不重新构建，用于代码更新后）:"
	@echo "  make restart     - 重启 GPU 容器"
	@echo "  make restart-cpu - 重启 CPU 容器"
	@echo ""
	@echo "构建:"
	@echo "  make build       - 构建 GPU 镜像"
	@echo "  make build-cpu   - 构建 CPU 镜像"
	@echo "  make rebuild     - 重新构建并启动 GPU 版本"
	@echo "  make rebuild-cpu - 重新构建并启动 CPU 版本"
	@echo ""
	@echo "调试:"
	@echo "  make logs        - 查看 GPU 日志"
	@echo "  make logs-cpu    - 查看 CPU 日志"
	@echo "  make ps          - 查看 GPU 容器状态"
	@echo "  make ps-cpu      - 查看 CPU 容器状态"
	@echo "  make shell       - 进入 GPU 容器"
	@echo "  make shell-cpu   - 进入 CPU 容器"
	@echo ""
	@echo "清理:"
	@echo "  make clean       - 清理 GPU 容器和镜像"
	@echo "  make clean-cpu   - 清理 CPU 容器和镜像"

# 启动
up:
	docker compose up -d

up-cpu:
	docker compose -f docker-compose.cpu.yml up -d

# 停止
down:
	docker compose down

down-cpu:
	docker compose -f docker-compose.cpu.yml down

# 重启（不重新构建，会重新读取配置）
restart:
	docker compose down
	docker compose up -d

restart-cpu:
	docker compose -f docker-compose.cpu.yml down
	docker compose -f docker-compose.cpu.yml up -d

# 构建
build:
	docker compose build

build-cpu:
	docker compose -f docker-compose.cpu.yml build

# 重新构建并启动
rebuild: down build up

rebuild-cpu: down-cpu build-cpu up-cpu

# 日志
logs:
	docker compose logs -f

logs-cpu:
	docker compose -f docker-compose.cpu.yml logs -f

# 状态
ps:
	docker compose ps

ps-cpu:
	docker compose -f docker-compose.cpu.yml ps

# Shell
shell:
	docker compose exec indextts /bin/bash

shell-cpu:
	docker compose -f docker-compose.cpu.yml exec indextts /bin/bash

# 清理
clean:
	docker compose down --rmi local --volumes

clean-cpu:
	docker compose -f docker-compose.cpu.yml down --rmi local --volumes
