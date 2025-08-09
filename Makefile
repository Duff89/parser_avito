ifeq ($(OS),Windows_NT)
	CURDIR := $(shell cd)
else
	CURDIR := $(shell pwd)
endif

IMAGE_NAME=parser_avito:latest
CONTAINER_NAME=parser_avito_container

build:
	docker build -t $(IMAGE_NAME) .

run:
	docker run --rm -v $(CURDIR):/app --name $(CONTAINER_NAME) $(IMAGE_NAME)

stop:
	docker stop $(CONTAINER_NAME) || echo "Container stopped"

