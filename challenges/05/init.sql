CREATE TABLE users (
    uid VARCHAR(64) PRIMARY KEY,
    upw VARCHAR(128) NOT NULL
);

INSERT INTO users (uid, upw) VALUES
    ('guest', 'guest');
