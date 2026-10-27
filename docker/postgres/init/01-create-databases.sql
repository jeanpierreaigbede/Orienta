-- Runs once, when the postgres volume is created.
-- "orienta" (created by POSTGRES_DB) is used by the main and chatbot-without-encryption branches.
-- "orienta_encrypted" is used by the chatbot-with-encryption branch, so both can be compared side by side.
CREATE DATABASE orienta_encrypted;
