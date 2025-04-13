# 📘 Students & Groups API

RESTful API на FastAPI для управления студентами и иерархией академических групп.

---

## 🚀 Технологии

| Компонент         | Назначение                                               |
|-------------------|-----------------------------------------------------------|
| **FastAPI**       | Веб-фреймворк для REST API                               |
| **SQLAlchemy**    | ORM для взаимодействия с PostgreSQL                      |
| **Pydantic v2**   | Валидация и сериализация моделей                         |
| **PostgreSQL**    | Хранение данных                                          |
| **Docker**        | Контейнеризация                                          |
| **docker-compose**| Управление сервисами (FastAPI + PostgreSQL)             |

---

## 📦 Функциональность

### `/students`
| Метод | Путь               | Описание                             |
|-------|--------------------|--------------------------------------|
| POST  | `/students`        | Добавить студента                    |
| GET   | `/students`        | Список всех студентов или поиск     |
| GET   | `/students/{id}`   | Получить студента по ID             |
| PUT   | `/students/{id}`   | Обновить информацию о студенте      |
| DELETE| `/students/{id}`   | Удалить студента по ID              |

### `/groups`
| Метод | Путь                | Описание                                          |
|-------|---------------------|---------------------------------------------------|
| POST  | `/groups`           | Добавить группу с опциональным родителем         |
| GET   | `/groups`           | Возвращает дерево групп или плоский список по `query` |
| GET   | `/groups/{id}`      | Получить одну группу по ID                       |
| PUT   | `/groups/{id}`      | Обновить группу (название, родитель)             |
| DELETE| `/groups/{id}`      | Удалить группу, если у неё нет подгрупп          |

---

## 📁 Структура кода

- `main.py`: точка входа и логика API, SQLAlchemy модели `Student`, `Group`, Pydantic-схемы `StudentCreate`, `GroupOut`, `GroupFlatOut`
- `Dockerfile`: сборка образа приложения
- `docker-compose.yml`: сервисы FastAPI и PostgreSQL

---

## 🧠 Особенности реализации

- ✅ Единый endpoint `GET /groups` возвращает либо дерево, либо плоский результат по `query`
- ✅ Защита от удаления группы с подгруппами (`409 Conflict`)
- ✅ Проверка: нельзя назначить родителем саму себя
- ✅ Все связи и типы строго проверяются (например, `parent_id` → `int | null`)

---

## 🐳 Запуск с Docker

1. Клонировать репозиторий:
```bash
git clone https://github.com/s70c3/students-groups-api.git
cd students-groups-api
```

2. Собрать и запустить:
```bash
docker-compose up --build
```

3. Открыть Swagger-документацию:
[http://localhost:8000/docs](http://localhost:8000/docs)

---

## ⚙️ Переменные окружения

```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/postgres
```
(используется по умолчанию, можно переопределить в `docker-compose.yml`)

---

## 📌 Пример запроса

### Добавить группу:
```json
POST /groups
{
  "name": "Root"
}
```

### Добавить подгруппу:
```json
POST /groups
{
  "name": "Child",
  "parent_id": 1
}
```

### Получить дерево:
```http
GET /groups
```

---

## 📄 Лицензия
MIT License
