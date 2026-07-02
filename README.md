# PiRKSP_KR

Репозиторий с курсовой работой для предмета "Проектирование и разработка клиент-серверных приложений"

Проект упакован в Docker-контейнеры. Для запуска всего стека (PostgreSQL, Backend, Frontend) выполните следующие шаги:

## 1. Подготовка окружения
Убедитесь, что существует файл `.env`. Если его нет, создайте его на основе примера:
```bash
cp .env.example .env
```

## 2. Запуск сервисов
Соберите образы и запустите контейнеры в режиме разработки:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```
Соберите образы и запустите контейнеры в режиме разработки:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 3. Доступ к приложениям
После завершения инициализации сервисы будут доступны по адресам:

Frontend: http://localhost:3000

Backend API: http://localhost:8000

Swagger: http://localhost:8000/docs

Database: localhost:5432
