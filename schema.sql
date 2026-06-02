-- ============================================================
-- Election Web — Database Schema
-- MySQL 8.0+  |  charset: utf8mb4
-- ============================================================

CREATE DATABASE IF NOT EXISTS election_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE election_db;

-- ── ผู้ใช้งาน ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id         INT          AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL,
    email      VARCHAR(100) NOT NULL,
    password   VARCHAR(255) NOT NULL,          -- bcrypt hash
    full_name  VARCHAR(100) NOT NULL,          -- ใช้ตรวจสอบ vote ซ้ำข้ามบัญชี
    role       ENUM('voter','admin') NOT NULL DEFAULT 'voter',
    is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_users_username  (username),
    UNIQUE KEY uq_users_email     (email),
    UNIQUE KEY uq_users_fullname  (full_name)  -- ป้องกัน vote ซ้ำระดับ DB
);

-- ── การเลือกตั้ง ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS elections (
    id          INT          AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    status      ENUM('pending','open','closed') NOT NULL DEFAULT 'pending',
    start_time  DATETIME,
    end_time    DATETIME,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INT,                           -- admin user_id

    INDEX idx_elections_status (status),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ── ผู้สมัคร ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
    id          INT          AUTO_INCREMENT PRIMARY KEY,
    election_id INT          NOT NULL,
    name        VARCHAR(100) NOT NULL,
    party       VARCHAR(100),
    bio         TEXT,
    photo_url   VARCHAR(255),
    number      INT,                           -- หมายเลขผู้สมัคร
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_candidates_election (election_id),
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
);

-- ── คะแนนเสียง ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS votes (
    id           INT      AUTO_INCREMENT PRIMARY KEY,
    user_id      INT      NOT NULL,
    candidate_id INT      NOT NULL,
    election_id  INT      NOT NULL,
    voted_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 1 คน 1 สิทธิ์ ต่อ 1 วาระ (ต่างจาก README ที่ UNIQUE แค่ user_id)
    UNIQUE KEY uq_votes_user_election (user_id, election_id),

    INDEX idx_votes_election    (election_id),
    INDEX idx_votes_candidate   (candidate_id),

    FOREIGN KEY (user_id)      REFERENCES users(id)      ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (election_id)  REFERENCES elections(id)  ON DELETE CASCADE
);

-- ── OTP (สำหรับยืนยันก่อน vote) ────────────────────────────
CREATE TABLE IF NOT EXISTS otps (
    id         INT          AUTO_INCREMENT PRIMARY KEY,
    user_id    INT          NOT NULL,
    code       VARCHAR(6)   NOT NULL,
    purpose    ENUM('vote','login') NOT NULL DEFAULT 'vote',
    used       BOOLEAN      NOT NULL DEFAULT FALSE,
    expires_at DATETIME     NOT NULL,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_otps_user    (user_id),
    INDEX idx_otps_expires (expires_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
