-- Создание таблицы "phone"
CREATE TABLE phone (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20)
);

-- Вставка данных в таблицу "phone"
INSERT INTO phone (phone_number) VALUES ('81234567890');

-- Создание таблицы "email"
CREATE TABLE email (
    id SERIAL PRIMARY KEY,
    email_address VARCHAR(100)
);

-- Вставка данных в таблицу "email"
INSERT INTO email (email_address) VALUES ('test1@example.com');

create user repl_user with replication encrypted password '12345';
select pg_create_physical_replication_slot('replication_slot');
