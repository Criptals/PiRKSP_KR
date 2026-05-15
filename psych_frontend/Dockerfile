FROM nginx:1.25-alpine

# копируем статику
COPY . /usr/share/nginx/html

# копируем конфиг nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
