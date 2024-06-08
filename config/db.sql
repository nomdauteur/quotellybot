-- bot_db.quotelybot_users definition

CREATE TABLE `quotelybot_users` (
  `id` bigint(20) NOT NULL,
  `name` varchar(1000) DEFAULT NULL,
  `last_visited` datetime(6) DEFAULT NULL,
  `alias` varchar(1000) DEFAULT NULL,
  `job_id` varchar(1000) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ;

-- bot_db.routelebot_quotes definition

CREATE TABLE `routelebot_quotes` (
  `id` bigint(20) NOT NULL,
  `lang` varchar(10) DEFAULT NULL,
  `added_dttm` datetime(6) DEFAULT NULL,
  `phrase` text DEFAULT NULL,
  `source_name` text DEFAULT NULL,
  `source_author` varchar(1000) DEFAULT NULL,
  PRIMARY KEY (`id`)
) 