# Учебный проект CI/CD

Проект показывает полный путь изменения кода: запуск Python-приложения,
проверка тестами, сборка Docker-образа и его публикация через GitHub Actions.
На нём можно изучить работу Docker Compose, миграций базы данных и CI/CD.

## Что входит в проект

- FastAPI и Uvicorn: HTTP API и сервер приложения.
- PostgreSQL 15: база данных и таблица пользователей.
- Redis 7: счётчик обращений к главной странице.
- Alembic: управление схемой PostgreSQL через миграции.
- Pytest и pytest-cov: тестирование и измерение покрытия кода.
- Docker Compose: запуск сервисов локально.
- GitHub Actions: тестирование, сборка и публикация образа.

## Как работает приложение

При запросе `GET /` приложение подключается к PostgreSQL, получает версию
сервера и увеличивает ключ `visit_count` в Redis командой `INCR`.
Ответ содержит сообщение, версию PostgreSQL и новое значение счётчика:

```json
{
  "message": "Приложение работает!",
  "postgres_version": "PostgreSQL 15...",
  "visit_count": "1"
}
```

Каждый запрос увеличивает счётчик. Redis выполняет увеличение атомарно,
поэтому параллельные запросы получают свои значения.

Маршрут `GET /health` возвращает `{"status": "healthy"}` и проверяет работу
процесса API. Доступность PostgreSQL и Redis проверяют отдельные healthchecks
в Compose. На странице `/docs` доступен Swagger UI.

Миграция `001_initial` создаёт таблицу `users` с полями `id`, `name`,
`email` и `created_at`. Эта таблица служит примером управления схемой;
API пока не предоставляет операции с пользователями.

## Запуск через Docker Compose

Нужны Docker Desktop с Linux-контейнерами и Docker Compose.
Для запуска из Ubuntu WSL включите интеграцию Ubuntu в Docker Desktop.

В PowerShell:

```powershell
cd C:\Users\User\Desktop\Netology\Lectures\Univer\CI_CD
docker compose up -d --build --wait
```

В Ubuntu WSL:

```bash
cd /mnt/c/Users/User/Desktop/Netology/Lectures/Univer/CI_CD
docker compose up -d --build --wait
```

Compose запускает PostgreSQL и Redis и ждёт готовности сервисов.
Затем сервис `migrate` применяет миграции Alembic. После успешной миграции
Compose запускает API.

Откройте:

- [Главная страница](http://localhost:8000/)
- [Swagger UI](http://localhost:8000/docs)
- [Проверка API](http://localhost:8000/health)

Порт API доступен на `127.0.0.1`. PostgreSQL и Redis доступны внутри сети
Compose. Данные сохраняются в именованных томах `postgres_data` и `redis_data`.

## Локальные настройки

Скопируйте `.env.example` в `.env` до первого запуска:

```powershell
Copy-Item .env.example .env
```

В Ubuntu для этого используйте `cp .env.example .env`.

В файле можно задать `APP_PORT` и `POSTGRES_PASSWORD`.
Если порт 8000 занят, укажите `APP_PORT=8001` и открывайте приложение на порту 8001.
Пароль по умолчанию предназначен для локальных учебных запусков.

Значение `POSTGRES_PASSWORD` применяется при первичной инициализации БД.
Изменение переменной не меняет пароль в уже существующем томе PostgreSQL.

Приложение читает адреса подключений из `DATABASE_URL` и `REDIS_URL`.
Compose задаёт их для контейнеров автоматически.

## Python-окружение для Windows

В каталоге `.venv` установлены Python 3.11.9 и зависимости проекта.
В PyCharm выберите интерпретатор `.venv\Scripts\python.exe`.

Активация в PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Чтобы создать окружение заново через uv:

```powershell
uv venv --python 3.11.9 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

Окружение `.venv` предназначено для Windows. В Docker используется
собственный Python 3.11 из образа. Для Ubuntu WSL потребуется отдельное
Linux-окружение, если вы хотите запускать Python за пределами контейнеров.

## Тесты

Запустите тесты с настоящими PostgreSQL и Redis через Compose:

```bash
docker compose --profile test run tests
```

Тесты проверяют:

- Ответ маршрута `/health`.
- Получение версии PostgreSQL и счётчика Redis.
- Увеличение счётчика между запросами.
- Схему таблицы `users` и текущую ревизию Alembic.
- Закрытие соединения PostgreSQL при ошибке SQL.

В выводе отображается покрытие кода. Запуск тестов увеличивает счётчик
посещений в локальном Redis.

## Миграции и управление сервисами

Применить доступные миграции:

```bash
docker compose run migrate
```

Проверить текущую ревизию:

```bash
docker compose exec app alembic current
```

Посмотреть статус сервисов и логи API:

```bash
docker compose ps
docker compose logs app
```

Остановить сервисы с сохранением данных:

```bash
docker compose stop
```

## Как работает CI/CD

Workflow находится в `.github/workflows/deploy.yml`.
Он запускается при push в `main` и `develop`, при pull request в `main`
и вручную через GitHub Actions.

Задание `test` поднимает PostgreSQL и Redis, устанавливает зависимости
Python 3.11, применяет миграции и выполняет тесты. Отчёт `coverage.xml`
сохраняется как артефакт запуска.

После успешных тестов задание `build-docker` собирает образ приложения.
Если тесты завершились с ошибкой, сборка не запускается.

Задание `publish-docker` публикует образ в Docker Hub после успешных тестов
и сборки. Для его включения добавьте в настройках GitHub-репозитория:

- Переменную `ENABLE_DOCKERHUB` со значением `true`.
- Секрет `DOCKERHUB_USERNAME` с именем пользователя Docker Hub.
- Секрет `DOCKERHUB_TOKEN` с токеном доступа Docker Hub.

Публикация выполняется только при push в `main`. Образ получает теги
`<username>/myapp:latest` и `<username>/myapp:<commit SHA>`.

Этап CD в этом проекте заканчивается публикацией образа.
Для автоматического развёртывания на сервере потребуется отдельное задание.
Чтобы запустить workflow, разместите проект в своём GitHub-репозитории.

## Структура проекта

```text
CI_CD/
├── .github/workflows/deploy.yml
├── alembic/
│   ├── versions/001_initial.py
│   ├── env.py
│   └── script.py.mako
├── src/
│   ├── __init__.py
│   └── app.py
├── tests/test_app.py
├── .dockerignore
├── .env.example
├── .gitignore
├── alembic.ini
├── compose.yaml
├── Dockerfile
├── pytest.ini
├── requirements.txt
└── README.md
```

## Запуск приложения в образе

Dockerfile запускает python src/app.py. В блоке if __name__ == '__main__'
приложение запускает Uvicorn на 0.0.0.0:8000. При импорте src.app в тестах
этот блок не выполняется. Для тестового сервиса Compose подключает tests
и pytest.ini с хоста только для чтения; они не копируются в образ приложения.