# Система онлайн-заказа пропусков — Backend API

## Быстрый старт (5 шагов)

### 1. Установить зависимости
```
pip install -r requirements.txt
```

### 2. Создать базу данных
```
python manage.py makemigrations api
python manage.py migrate
```

### 3. Создать администратора
```
python manage.py createsuperuser
```
Введи email, ФИО и пароль.

### 4. Запустить сервер
```
python manage.py runserver
```
API будет доступен по адресу: http://127.0.0.1:8000/api/

### 5. Открыть админку
http://127.0.0.1:8000/admin/

---

## Структура проекта

```
passystem/
├── manage.py
├── requirements.txt
├── passystem/
│   ├── settings.py     — настройки Django
│   ├── urls.py         — главный роутер
│   └── wsgi.py
└── api/
    ├── models.py       — модели БД (User, PassRequest, Pass, VisitLog, ...)
    ├── serializers.py  — сериализаторы DRF
    ├── views.py        — view-обработчики
    ├── urls.py         — маршруты API
    ├── permissions.py  — права доступа по ролям
    └── admin.py        — регистрация в админке
```

---

## Тестирование в Postman

### Шаг 1 — Регистрация гостя
POST http://127.0.0.1:8000/api/auth/register/
Body (JSON):
{
  "full_name": "Иванов Иван",
  "email": "guest@test.ru",
  "phone": "+79001234567",
  "password": "Test1234!",
  "password_confirm": "Test1234!"
}

### Шаг 2 — Вход и получение токена
POST http://127.0.0.1:8000/api/auth/login/
Body (JSON):
{
  "email": "guest@test.ru",
  "password": "Test1234!"
}
Скопируй "access" токен из ответа.

### Шаг 3 — Авторизованный запрос
В Postman: Headers → Authorization: Bearer <твой_токен>

### Шаг 4 — Запрос без токена (должен вернуть 401)
GET http://127.0.0.1:8000/api/requests/
(без заголовка Authorization)

---

## Роли пользователей

| Роль     | Что может                                      |
|----------|------------------------------------------------|
| guest    | Подавать заявки, смотреть свои пропуска        |
| employee | Одобрять/отклонять входящие заявки             |
| guard    | Проверять QR-коды, создавать записи журнала    |
| admin    | Всё + управление пользователями и настройками  |

Создать сотрудника/охранника можно через /admin/ (Django-админка).
