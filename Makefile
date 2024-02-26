dev:
	docker compose -p parser_avito up --build

run:
	docker compose -f compose.prod.yml -p parser_avito up --build -d

stop:
	docker compose -f compose.prod.yml -p parser_avito stop

check:
	docker ps --filter name="^parser_avito" --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

connect:
	docker exec -it `docker ps -a | grep parser_avito-script | cut -d ' ' -f 1` bash
