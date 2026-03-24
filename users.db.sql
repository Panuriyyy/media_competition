BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "bot_users" (
	"id"	INTEGER NOT NULL,
	"vk_id"	INTEGER NOT NULL,
	"name"	VARCHAR NOT NULL,
	"institute"	VARCHAR,
	"group_num"	VARCHAR,
	"reg_date"	DATETIME,
	"is_active"	BOOLEAN,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "manual_submissions" (
	"id"	INTEGER,
	"user_vk_id"	INTEGER,
	"task_id"	INTEGER,
	"submission_url"	TEXT,
	"submission_type"	TEXT,
	"submission_date"	TIMESTAMP,
	"status"	TEXT DEFAULT 'pending',
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "sent_notifications" (
	"id"	INTEGER NOT NULL,
	"user_vk_id"	INTEGER,
	"task_id"	INTEGER NOT NULL,
	"sent_date"	DATETIME,
	PRIMARY KEY("id"),
	CONSTRAINT "unique_user_task" UNIQUE("user_vk_id","task_id"),
	FOREIGN KEY("user_vk_id") REFERENCES "bot_users"("vk_id")
);
CREATE TABLE IF NOT EXISTS "tasks" (
	"id"	INTEGER NOT NULL,
	"title"	VARCHAR NOT NULL,
	"description"	TEXT NOT NULL,
	"task_type"	VARCHAR NOT NULL,
	"auto_type"	VARCHAR,
	"file_format"	VARCHAR,
	"deadline"	DATETIME NOT NULL,
	"created_at"	DATETIME,
	"created_by"	INTEGER,
	"is_active"	BOOLEAN,
	"posts"	TEXT,
	PRIMARY KEY("id"),
	FOREIGN KEY("created_by") REFERENCES "users"("id")
);
CREATE TABLE IF NOT EXISTS "user_tasks" (
	"id"	INTEGER,
	"user_vk_id"	INTEGER,
	"task_id"	INTEGER,
	"status"	TEXT,
	"completed_date"	TIMESTAMP,
	PRIMARY KEY("id" AUTOINCREMENT),
	UNIQUE("user_vk_id","task_id")
);
CREATE TABLE IF NOT EXISTS "users" (
	"id"	INTEGER NOT NULL,
	"username"	VARCHAR NOT NULL,
	"password_hash"	VARCHAR NOT NULL,
	"full_name"	VARCHAR NOT NULL,
	"role"	VARCHAR,
	"created_at"	DATETIME,
	PRIMARY KEY("id")
);
INSERT INTO "bot_users" VALUES (2,531299,'Олеся Степанова','ГИ','','2026-03-18 13:13:24',1);
INSERT INTO "bot_users" VALUES (3,91627257,'Гермиона Айсидоровна Король','ИКНК','','2026-03-18 13:14:00',1);
INSERT INTO "bot_users" VALUES (4,382200111,'Иван','Икнк','','2026-03-22 17:40:22',1);
INSERT INTO "manual_submissions" VALUES (1,382200111,8,'https://sun9-47.vkuserphoto.ru/s/v1/ig2/LhZ64vyNkCvnCLGhrXKPb6bq-shxlCU-NPIv2F32VguYmH1sdtdfKCPx-1FmFmYeI6sbfqZTgI8y4VUyyq8sUdQz.jpg?quality=95&as=32x43,48x64,72x96,108x144,160x213,240x320,360x480,480x640,540x720,640x853,720x960,1080x1440,1280x1707,1440x1920,1920x2560&from=bu','photo','2026-03-18 11:23:35','pending');
INSERT INTO "manual_submissions" VALUES (2,382200111,8,'https://sun9-13.userapi.com/s/v1/ig2/5-1N3LZnhYm1EKZqHCpwUNpmrTnFTXGBw-aFyuKwIC8_Ntf6Ieq2B4Pa6tFv-86zHl2fCV4TUbR4KUllJeDasor0.jpg?quality=95&as=32x43,48x64,72x96,108x144,160x214,240x320,360x481,480x641,540x721,640x854,720x961,1080x1442,1280x1709,1344x1794&from=bu','photo','2026-03-18 11:54:33','pending');
INSERT INTO "tasks" VALUES (1,'Задание 1774169044967','пыыышки','auto','comments',NULL,'2026-03-24 05:43:00.000000','2026-03-22 11:44:04.991305',1,1,'["https://vk.com/wall-61195360_117476"]');
INSERT INTO "tasks" VALUES (2,'Задание 1774183201626','donats','auto','likes','Выберите формат файла','2026-03-24 12:39:00.000000','2026-03-22 15:40:01.646778',2,1,'["https://vk.com/wall-61195360_117476"]');
INSERT INTO "users" VALUES (1,'marianna','$2b$12$D6gYEJ4a3kvjNCUqxBCELOmMgGdGVFp3V5BwW2V599D6Uyqjqx5/K','Марианна Юрьевна','admin','2026-03-12 11:06:14.062583');
INSERT INTO "users" VALUES (2,'olesya','$2b$12$nZLa1vWgz5fClN4QCI3LheqdbFopeRTuavUZNR0pzijF4q3odRpSq','Олеся Игоревна','admin','2026-03-12 11:06:14.062583');
INSERT INTO "users" VALUES (3,'vera','$2b$12$e5xC9KO/hClijNfDZHHMGOzFmAzGyIG/G/jkeFYFmVUb6/3oX0/iO','Вера Владиславовна','admin','2026-03-12 11:06:14.062583');
CREATE INDEX IF NOT EXISTS "ix_bot_users_id" ON "bot_users" (
	"id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "ix_bot_users_vk_id" ON "bot_users" (
	"vk_id"
);
CREATE INDEX IF NOT EXISTS "ix_sent_notifications_id" ON "sent_notifications" (
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
