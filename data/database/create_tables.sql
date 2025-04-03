CREATE TABLE chat (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(250) NOT NULL,
    user_id VARCHAR(250) NOT NULL,
    message VARCHAR(1000) NOT NULL,
    reaction_count INTEGER NOT NULL,
    timestamp VARCHAR(100) NOT NULL,
    date_created TIMESTAMP NOT NULL DEFAULT NOW(),
    trace_id VARCHAR(250) NOT NULL
);

CREATE TABLE donation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(250) NOT NULL,
    user_id VARCHAR(250) NOT NULL,
    amount FLOAT NOT NULL,
    currency VARCHAR(10) NOT NULL,
    message VARCHAR(1000) NOT NULL,
    timestamp VARCHAR(100) NOT NULL,
    date_created TIMESTAMP NOT NULL DEFAULT NOW(),
    trace_id VARCHAR(250) NOT NULL
);
