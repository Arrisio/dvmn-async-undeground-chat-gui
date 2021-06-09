# Графический клиент для чата(minechat)
Доступно 2-клиента:
 * `main.py` - полноценный gui-клиент для общения в чате minechat(поддерживает историю сообщений)
 * `register_new_user.py` - gui-клиент для регистрации нового пользователя


## Как установить

Для работы клиентов нужен Python версии не ниже 3.8 и пакетный менеджер [poetry](https://python-poetry.org/docs/)

```bash
poetry install
```

## Как запустить

```bash
python main.py

Выполнена авторизация. Пользователь Focused Loyd
[1580201350] Connection is alive! Authorization done
[1580201350] Connection is alive! Ping message was successful
[1580201351] Connection is alive! New message in chat
[1580201353] Connection is alive! New message in chat
[1580201356] Connection is alive! New message in chat
[1580201358] Connection is alive! New message in chat
[1580201360] Connection is alive! Ping message was successful
[1580201361] Connection is alive! New message in chat
.......
```
Интерфейс чата<br>
<a href="https://ibb.co/XZnKnDy"><img src="https://i.ibb.co/PZ2P2MT/example.png" alt="example" border="0"></a>

Интерфейс регистрации<br>
<a href="https://imgbb.com/"><img src="https://i.ibb.co/XpNr4Zh/example-reg.png" alt="example-reg" border="0"></a>

## Настройки
Программа готова к использованию с настойками по умолчанию.

Указать специальные параметры настройки можно через переменные окружения или перечислив их в файле `.env` создав/отредактировав его в директории с программой.

С полным перечнем настроек можно ознакомиться в файле `settings.py` открыв его в текстовом редакторе.  