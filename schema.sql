-- ============================================================
-- Election Web — Database Schema  (README v2)
-- MySQL 8.0+  |  charset: utf8mb4
-- ============================================================

CREATE DATABASE IF NOT EXISTS election_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE election_db;

-- ── ผู้ใช้งาน (Admin) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id         INT          AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL,
    email      VARCHAR(100) NOT NULL,
    password   VARCHAR(255) NOT NULL,
    full_name  VARCHAR(100) NOT NULL,
    role       ENUM('voter','admin') NOT NULL DEFAULT 'voter',
    is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email    (email),
    UNIQUE KEY uq_users_fullname (full_name)
);

-- ── สมาชิก (นำเข้าจาก Excel โดย admin) ─────────────────────
CREATE TABLE IF NOT EXISTS members (
    id         INT          AUTO_INCREMENT PRIMARY KEY,
    full_name  VARCHAR(100) NOT NULL,
    email      VARCHAR(100),
    email_new  VARCHAR(100),
    verified   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_members_email (email)
);

-- ── การเลือกตั้ง (แยกตามประเภท) ────────────────────────────
CREATE TABLE IF NOT EXISTS elections (
    id          INT          AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    type        ENUM('president','treasurer','committee') NOT NULL,
    max_votes   INT          NOT NULL DEFAULT 1,
    is_visible  BOOLEAN      NOT NULL DEFAULT TRUE,
    status      ENUM('pending','open','closed') NOT NULL DEFAULT 'pending',
    start_time  DATETIME,
    end_time    DATETIME,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INT,

    INDEX idx_elections_status (status),
    INDEX idx_elections_type   (type),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ── ผู้สมัคร ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
    id          INT          AUTO_INCREMENT PRIMARY KEY,
    election_id INT          NOT NULL,
    name        VARCHAR(100) NOT NULL,
    photo_url   VARCHAR(255),
    number      INT          NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_candidates_election_number (election_id, number),
    INDEX idx_candidates_election (election_id),
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
);

-- ── คะแนนเสียง (เข้ารหัสผู้เลือก) ──────────────────────────
CREATE TABLE IF NOT EXISTS votes (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    member_id_hash  VARCHAR(255) NOT NULL,
    candidate_id    INT          NOT NULL,
    election_id     INT          NOT NULL,
    voted_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_votes_member_election (member_id_hash, election_id),
    INDEX idx_votes_election  (election_id),
    INDEX idx_votes_candidate (candidate_id),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (election_id)  REFERENCES elections(id)  ON DELETE CASCADE
);

-- ── OTP ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS otps (
    id         INT          AUTO_INCREMENT PRIMARY KEY,
    member_id  INT          NOT NULL,
    code       VARCHAR(6)   NOT NULL,
    purpose    ENUM('verify','vote') NOT NULL DEFAULT 'vote',
    used       BOOLEAN      NOT NULL DEFAULT FALSE,
    expires_at DATETIME     NOT NULL,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_otps_member  (member_id),
    INDEX idx_otps_expires (expires_at),
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

-- ── Log การใช้งาน ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS access_logs (
    id          INT          AUTO_INCREMENT PRIMARY KEY,
    member_id   INT,
    action      VARCHAR(100) NOT NULL,
    ip_address  VARCHAR(45)  NOT NULL,
    system_type VARCHAR(50),
    logged_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_logs_member (member_id),
    INDEX idx_logs_action (action),
    INDEX idx_logs_logged (logged_at),
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE SET NULL
);

-- ── System settings (เปิด/ระงับแต่ละระบบ) ───────────────────
CREATE TABLE IF NOT EXISTS system_settings (
    id          INT          AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(50)  NOT NULL UNIQUE,
    value       VARCHAR(255) NOT NULL DEFAULT '1',
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT IGNORE INTO system_settings (setting_key, value) VALUES
    ('verify_enabled', '1'),
    ('vote_enabled',   '1');
