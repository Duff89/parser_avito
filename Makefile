ifeq ($(OS),Windows_NT)
	CURDIR := $(shell cd)
	NULL_OUT := NUL
	TRUE := rem
else
	CURDIR := $(shell pwd)
	NULL_OUT := /dev/null
	TRUE := true
endif

IMAGE_NAME = parser_avito:latest
CONTAINER_NAME = parser_avito_container

.PHONY: build run restart stop logs shell clean rebuild

# 🏗️ Сборка Docker-образа
build:
	docker build -t $(IMAGE_NAME) .

# ▶️ Запуск контейнера в фоне
run:
	docker run -d \
		--name $(CONTAINER_NAME) \
		-v $(CURDIR):/app \
		$(IMAGE_NAME)

# 🔄 Перезапуск контейнера (если уже запущен)
restart: stop run

# 🧱 Полная пересборка: stop → build → run
rebuild: stop build run

# 🧹 Остановка и удаление контейнера
stop:
	@docker stop $(CONTAINER_NAME) >$(NULL_OUT) 2>&1 || $(TRUE)
	@docker rm $(CONTAINER_NAME) >$(NULL_OUT) 2>&1 || $(TRUE)
	@echo Container stopped and removed.

# 📜 Просмотр логов контейнера
logs:
	docker logs -f $(CONTAINER_NAME)

# 🐚 Подключение внутрь контейнера
shell:
	docker exec -it $(CONTAINER_NAME) bash

# 🧽 Полная очистка (контейнер + образ)
clean: stop
	@docker rmi $(IMAGE_NAME) >$(NULL_OUT) 2>&1 || $(TRUE)
	@echo Image removed.
