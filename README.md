Вы можете развернуть проект с помощью ansible:
1. скачайте репозиторий
2. подготовьте .env файл
3. подготовьте inventory: замените переменные желаемыми данными, а также укажите хосты и логин/пароль для пользователей
4. запустите плэйбук: ansible-playbook playbook-tg-bot.yml
Проект протестирован на ubuntu(bot+db)+ubuntu(db_repl) и debian(bot+db)+debian(db_repl). Вы можете развернуть бота и базу данных на одном хосте или на двух.
Для запуска на дебиан нужно раскомментировать некоторые строчки.
Есть несколько вариантов входа(сделайте это на всех хостах, где будет разворачиваться проект): если вы используете debian - создайте пользователя ansible (или любого другого) и добавьте его в /etc/sudoers (ansible ALL(ALL:ALL) NOPASSWD:ALL).
Если вы используете ubuntu, обычно у вашего пользователя уже есть права на sudo и вы можете указать его логин и пароль. Но вы также можете воспользоваться способом для debian и создать пользователя с добавлением в sudoers.
**Важно: для получения логов репликации RM_HOST должен содержать ip-адрес хоста, где развернута master база данных.**
На всех хостах должен быть включен ssh.
