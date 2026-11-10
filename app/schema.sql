CREATE TABLE IF NOT EXISTS users(
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50)   NOT NULL UNIQUE,
    salt            VARBINARY(16) NOT NULL,
    password_hash   CHAR(64)      NOT NULL,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS books(
    id              INT AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(255) NOT NULL,
    author          VARCHAR(255) NOT NULL,
    isbn            VARCHAR(32)  NOT NULL UNIQUE,
    total_copies    INT NOT NULL CHECK (total_copies >= 0),
    available_copies INT NOT NULL CHECK (available_copies >= 0),
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP 
);

CREATE TABLE IF NOT EXISTS loans(
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    book_id         INT NOT NULL,
    borrowed_at     DATETIME  NOT NULL,
    due_date        DATETIME  NOT NULL,
    returned_at     DATETIME  NULL,
    status          ENUM('active', 'returned') NOT NULL,
    FOREIGN KEY  (user_id) REFERENCES users(id),
    FOREIGN KEY  (book_id) REFERENCES books(id),
    INDEX idx_loans_user_status (user_id, status),
    INDEX idx_loans_book_status (book_id, status)
);

CREATE TABLE IF NOT EXISTS tokens (
  token       VARCHAR(64) PRIMARY KEY,
  user_id     INT NOT NULL,
  expires_at  DATETIME NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_tokens_user (user_id)
);