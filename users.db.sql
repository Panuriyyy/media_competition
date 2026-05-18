BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "check_tasks" (
	"id"	INTEGER NOT NULL,
	"submission_id"	INTEGER NOT NULL,
	"points"	INTEGER NOT NULL,
	"check_date"	DATETIME,
	PRIMARY KEY("id"),
	FOREIGN KEY("submission_id") REFERENCES "task_submissions"("id")
);
CREATE TABLE IF NOT EXISTS "format_files" (
	"id"	INTEGER NOT NULL,
	"name"	VARCHAR NOT NULL,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "notifications" (
	"id"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"title"	VARCHAR NOT NULL,
	"message"	TEXT NOT NULL,
	"is_read"	BOOLEAN,
	"created_at"	DATETIME,
	PRIMARY KEY("id"),
	FOREIGN KEY("user_id") REFERENCES "users"("id")
);
CREATE TABLE IF NOT EXISTS "participants" (
	"id_user"	INTEGER NOT NULL,
	"vk_link"	VARCHAR NOT NULL,
	"tg_link"	VARCHAR NOT NULL,
	"institute"	VARCHAR NOT NULL,
	PRIMARY KEY("id_user"),
	FOREIGN KEY("id_user") REFERENCES "users"("id")
);
CREATE TABLE IF NOT EXISTS "ratings" (
	"user_id"	INTEGER NOT NULL,
	"total_score"	FLOAT,
	"place"	INTEGER,
	"updated_at"	DATETIME,
	PRIMARY KEY("user_id"),
	FOREIGN KEY("user_id") REFERENCES "users"("id")
);
CREATE TABLE IF NOT EXISTS "task_submissions" (
	"id"	INTEGER NOT NULL,
	"task_id"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"submission_url"	VARCHAR,
	"status"	VARCHAR,
	"score"	FLOAT,
	"submitted_at"	DATETIME,
	"checked_at"	DATETIME,
	"checked_by"	INTEGER,
	PRIMARY KEY("id"),
	FOREIGN KEY("checked_by") REFERENCES "users"("id"),
	FOREIGN KEY("task_id") REFERENCES "tasks"("id"),
	FOREIGN KEY("user_id") REFERENCES "users"("id")
);
CREATE TABLE IF NOT EXISTS "tasks" (
	"id"	INTEGER NOT NULL,
	"title"	VARCHAR NOT NULL,
	"description"	TEXT NOT NULL,
	"task_type"	VARCHAR NOT NULL,
	"auto_type"	VARCHAR,
	"file_format"	VARCHAR,
	"posts"	TEXT,
	"deadline"	DATETIME NOT NULL,
	"created_by"	INTEGER,
	"is_active"	BOOLEAN,
	"created_at"	DATETIME,
	PRIMARY KEY("id"),
	FOREIGN KEY("created_by") REFERENCES "users"("id")
);
CREATE TABLE IF NOT EXISTS "users" (
	"id"	INTEGER NOT NULL,
	"username"	VARCHAR NOT NULL,
	"password_hash"	VARCHAR NOT NULL,
	"full_name"	VARCHAR NOT NULL,
	"email"	VARCHAR NOT NULL,
	"role"	VARCHAR,
	"created_at"	DATETIME,
	PRIMARY KEY("id")
);
INSERT INTO "check_tasks" VALUES (1,1,1,'2026-04-08 06:31:24.006584');
INSERT INTO "check_tasks" VALUES (2,3,3,'2026-04-08 08:48:54.804192');
INSERT INTO "check_tasks" VALUES (3,2,5,'2026-04-08 09:15:40.392475');
INSERT INTO "check_tasks" VALUES (4,3,1,'2026-04-08 12:37:45.996457');
INSERT INTO "check_tasks" VALUES (5,5,3,'2026-04-08 12:38:45.516965');
INSERT INTO "format_files" VALUES (1,'PNG, JPG');
INSERT INTO "format_files" VALUES (2,'MOV, MP3, MP4');
INSERT INTO "format_files" VALUES (3,'DOC, DOCS, PDF, TXT');
INSERT INTO "notifications" VALUES (1,2,'Добро пожаловать!','Вы успешно зарегистрировались на платформе. Желаем удачи в конкурсе!',0,'2026-04-08 06:06:15.495696');
INSERT INTO "notifications" VALUES (2,2,'Новое задание!','Появилось новое задание ''Задание 1775618623665''. Успейте выполнить до 16.04.2026 03:22',0,'2026-04-08 06:23:43.684596');
INSERT INTO "notifications" VALUES (3,3,'Добро пожаловать!','Вы успешно зарегистрировались на платформе. Желаем удачи в конкурсе!',1,'2026-04-08 06:30:38.696997');
INSERT INTO "notifications" VALUES (4,3,'Задание выполнено','Задание ''Задание 1775618623665'' успешно выполнено! Начислено 1 баллов.',1,'2026-04-08 06:31:24.014558');
INSERT INTO "notifications" VALUES (5,2,'Новое задание!','Появилось новое задание ''Задание 2''. Успейте выполнить до 15.04.2026 05:46',0,'2026-04-08 08:46:45.942826');
INSERT INTO "notifications" VALUES (6,3,'Новое задание!','Появилось новое задание ''Задание 2''. Успейте выполнить до 15.04.2026 05:46',1,'2026-04-08 08:46:45.942826');
INSERT INTO "notifications" VALUES (7,3,'Задание выполнено','Задание ''Задание 2'' успешно выполнено! Результат появится после проверки.',1,'2026-04-08 08:47:56.647153');
INSERT INTO "notifications" VALUES (8,2,'Задание выполнено','Задание ''Задание 1775618623665'' успешно выполнено! Начислено 3 баллов.',0,'2026-04-08 08:48:54.813143');
INSERT INTO "notifications" VALUES (9,3,'Результат проверки задания','Ваше задание ''Задание 2'' Начислено баллов: 5.0.',1,'2026-04-08 09:15:40.403453');
INSERT INTO "notifications" VALUES (10,3,'Результат проверки задания','Ваше задание ''Задание 2'' принято. ',1,'2026-04-08 09:15:43.902400');
INSERT INTO "notifications" VALUES (11,2,'Задание выполнено','Задание ''Задание 2'' успешно выполнено! Результат появится после проверки.',0,'2026-04-08 11:01:51.808278');
INSERT INTO "notifications" VALUES (12,2,'Новое задание!','Появилось новое задание ''Задание 3''. Успейте выполнить до 23.04.2026 06:36',0,'2026-04-08 12:36:56.325317');
INSERT INTO "notifications" VALUES (13,3,'Новое задание!','Появилось новое задание ''Задание 3''. Успейте выполнить до 23.04.2026 06:36',1,'2026-04-08 12:36:56.325317');
INSERT INTO "notifications" VALUES (14,2,'Результат проверки задания','Ваше задание ''Задание 1775618623665'' Начислено баллов: 1.0.',0,'2026-04-08 12:37:46.009418');
INSERT INTO "notifications" VALUES (15,3,'Задание выполнено','Задание ''Задание 3'' успешно выполнено! Начислено 3 баллов.',1,'2026-04-08 12:38:45.526535');
INSERT INTO "notifications" VALUES (16,4,'Добро пожаловать!','Вы успешно зарегистрировались на платформе. Желаем удачи в конкурсе!',0,'2026-04-08 12:40:17.134566');
INSERT INTO "participants" VALUES (2,'https://vk.com/ivan','https://t.me/ivan','ГИ');
INSERT INTO "participants" VALUES (3,'https://vk.com/petrkrut','https://t.me/petrkrut','ИЭ');
INSERT INTO "participants" VALUES (4,'https://vk.com/vasyakrutoy','https://t.me/vasyakrutoy','Физмех');
INSERT INTO "ratings" VALUES (2,1.0,NULL,'2026-04-08 12:37:45.983009');
INSERT INTO "ratings" VALUES (3,9.0,NULL,'2026-04-08 12:38:45.514064');
INSERT INTO "ratings" VALUES (4,0.0,NULL,'2026-04-08 12:40:17.127591');
INSERT INTO "task_submissions" VALUES (1,1,3,NULL,'completed',1.0,'2026-04-08 06:31:23.999604','2026-04-08 06:31:24.001600',NULL);
INSERT INTO "task_submissions" VALUES (2,2,3,'https://vk.com/wall382200111_5730','completed',5.0,'2026-04-08 08:47:56.631925','2026-04-08 09:15:40.363159',1);
INSERT INTO "task_submissions" VALUES (3,1,2,NULL,'completed',1.0,'2026-04-08 08:48:54.793548','2026-04-08 12:37:45.968080',1);
INSERT INTO "task_submissions" VALUES (4,2,2,'https://vk.com/wall382200111_5730','not_checked',0.0,'2026-04-08 11:01:51.761956',NULL,NULL);
INSERT INTO "task_submissions" VALUES (5,3,3,NULL,'completed',3.0,'2026-04-08 12:38:45.507730','2026-04-08 12:38:45.512978',NULL);
INSERT INTO "tasks" VALUES (1,'Задание 1775618623665','Необходимо пролайкать посты','auto','comments',NULL,'["https://vk.com/wall382200111_5737"]','2026-04-15 21:22:00.000000',1,1,'2026-04-08 06:23:43.672626');
INSERT INTO "tasks" VALUES (2,'Задание 2','Красиво сфоткать котов','manual',NULL,'PNG, JPG',NULL,'2026-04-15 05:46:00.000000',1,1,'2026-04-08 08:46:45.925791');
INSERT INTO "tasks" VALUES (3,'Задание 3','Всем хорошего дня','auto','comments',NULL,'["https://vk.com/wall-111"]','2026-04-23 00:36:00.000000',1,1,'2026-04-08 12:36:56.306800');
INSERT INTO "users" VALUES (1,'admin','$2b$12$Lrs77TDRzEunfnzGllksk.m8Bd8rI35dH99W15Og/Kx5ZTsUhxgtG','Администратор','admin@example.com','admin','2026-04-08 06:02:18.001121');
INSERT INTO "users" VALUES (2,'ivan123','$2b$12$zmwlBYuDImmoOz.dCP4Nf.tWVs3mWK.6bw7E0xFaB3G1ZAMEArHVW','Иванов Иван Иванович','ivan123@mail.ru','user','2026-04-08 06:06:15.477005');
INSERT INTO "users" VALUES (3,'petrkrut','$2b$12$c3OHzRX0TUPj0XNLzXGtWOUnj6NHwP5Y.9npISp8Z3mqo/W6FET2.','Петя Васечкин','petrkrut@mail.ru','user','2026-04-08 06:30:38.686023');
INSERT INTO "users" VALUES (4,'vasya123','$2b$12$7nm09kQb7SAgErU/ztj40.AHK/Rt6VFBDx6ydq5lEmcZOqVLTEqxq','Иванов Иван Иванович','vasyakrutoy@mail.ru','user','2026-04-08 12:40:17.117838');
CREATE INDEX IF NOT EXISTS "ix_check_tasks_id" ON "check_tasks" (
	"id"
);
CREATE INDEX IF NOT EXISTS "ix_format_files_id" ON "format_files" (
	"id"
);
CREATE INDEX IF NOT EXISTS "ix_notifications_id" ON "notifications" (
	"id"
);
CREATE INDEX IF NOT EXISTS "ix_task_submissions_id" ON "task_submissions" (
	"id"
);
CREATE INDEX IF NOT EXISTS "ix_tasks_id" ON "tasks" (
	"id"
);
CREATE INDEX IF NOT EXISTS "ix_users_id" ON "users" (
	"id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "ix_users_username" ON "users" (
	"username"
);
COMMIT;
