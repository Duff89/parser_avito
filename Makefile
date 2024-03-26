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

logs:
	docker logs `docker ps -a | grep parser_avito-script | cut -d ' ' -f 1`

set:
	cp nginx.prod.conf /etc/nginx/sites-enabled/alt.conf
	sudo chmod 0755 ~
	sudo chmod -R a+w ~/parser_avito/result/
	sudo chmod 0700 ~/.ssh
	sudo chmod -R 0600 ~/.ssh/*
	sudo systemctl restart nginx
	sudo certbot --nginx
