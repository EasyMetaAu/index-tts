.PHONY: help up up-cpu down restart restart-cpu logs build build-cpu ps shell clean

help:
	@echo "IndexTTS2 Docker 命令:"
	@echo "  make up          - 启动 GPU 版本"
	@echo "  make up-cpu      - 启动 CPU 版本"
	@echo "  make down        - 停止容器"
	@echo "  make restart     - 重启 GPU 版本"
	@echo "  make restart-cpu - 重启 CPU 版本"
	@echo "  make logs        - 查看日志"
	@echo "  make build       - 构建 GPU 镜像"
	@echo "  make build-cpu   - 构建 CPU 镜像"
	@echo "  make ps          - 查看容器状态"
	@echo "  make shell       - 进入容器 shell"
	@echo "  make clean       - 清理容器和镜像"

up:
	docker compose up -d

up-cpu:
	docker compose -f docker-compose.cpu.yml up -d

down:
	docker compose down

restart:
	docker compose restart

restart-cpu:
	docker compose -f docker-compose.cpu.yml restart

logs:
	docker compose logs -f

build:
	docker compose build

build-cpu:
	docker compose -f docker-compose.cpu.yml build

ps:
	docker compose ps

shell:
	docker compose exec indextts /bin/bash

clean:
	docker compose down --rmi local --volumes
