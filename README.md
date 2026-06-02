# Election Web — ระบบเลือกตั้งออนไลน์

เว็บไซต์เลือกตั้งออนไลน์ครบวงจร สร้างด้วย Python (Flask) + MySQL รองรับการลงคะแนน แสดงผล และจัดการผู้สมัครในที่เดียว

---

## Tech Stack

| ส่วน | เทคโนโลยี |
|---|---|
| Backend | Python 3.10+, Flask |
| Database | MySQL 8.0+ |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| Auth | Flask-Login + bcrypt + OTP (Email) |

---

## ฟีเจอร์หลัก

- **ระบบ Authentication** — สมัคร/เข้าสู่ระบบ, session management, role-based access (voter / admin)
- **OTP ก่อนลงคะแนน** — ส่งรหัส OTP ทาง email ยืนยันตัวตนก่อน vote ทุกครั้ง, หมดอายุใน 5 นาที
- **ลงคะแนน** — 1 คน 1 สิทธิ์ต่อวาระ, ป้องกัน vote ซ้ำทั้งระดับ DB (UNIQUE constraint) และระดับ app, ชื่อ-นามสกุลเดียวกันลงทะเบียนซ้ำไม่ได้
- **แยกวาระการเลือกตั้ง** — 1 บัญชีสามารถลงคะแนนได้หลายวาระ (แต่ละวาระลงได้ครั้งเดียว)
- **แสดงผลคะแนน** — กราฟ realtime ด้วย Chart.js (polling ทุก 10 วินาทีเมื่อวาระเปิดอยู่), แยกตามวาระ, export Excel
- **ข้อมูลผู้สมัคร** — รายชื่อ, พรรค, นโยบาย, หมายเลข, export Excel
- **ข้อมูลผู้ลงคะแนน** — รายชื่อพร้อมเวลา, export Excel (admin เท่านั้น)
- **Admin Panel** — สร้าง/ลบวาระ, เปิด-ปิดการเลือกตั้ง, เพิ่ม/แก้ไข/ลบผู้สมัคร, ดู dashboard ภาพรวม

---

## โครงสร้างโปรเจกต์หลัก

```
EW/
├── app.py                  # Flask app (application factory)
├── config.py               # ตั้งค่า DB, mail, session, CSRF
├── db.py                   # MySQL connection pool (Flask g)
├── schema.sql              # DDL สร้างตาราง
├── requirements.txt
│
├── models/
│   ├── user.py             # User model (Flask-Login UserMixin)
│   ├── candidate.py        # Candidate model
│   ├── vote.py             # Vote model + OTP helper
│   └── election.py         # Election model
│
├── routes/
│   ├── auth.py             # /login, /logout, /register, /request-otp, /verify-otp
│   ├── vote.py             # /, /vote/<id>, /results/<id>, /results/<id>/json
│   ├── candidates.py       # /candidates, /candidates/<id>, /candidates/<id>/export
│   └── admin.py            # /admin/*
│
├── templates/
│   ├── base.html
│   ├── index.html          # หน้าแรก (รายการวาระ)
│   ├── vote.html           # หน้าลงคะแนน (พร้อม confirm modal)
│   ├── results.html        # หน้าผลคะแนน (Chart.js + table)
│   ├── candidates.html     # หน้าผู้สมัคร
│   ├── auth/
│   │   ├── login.html
│   │   ├── register.html
│   │   └── verify_otp.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── elections.html
│   │   ├── candidates.html
│   │   └── voters.html
│   └── errors/
│       └── 403.html
│
└── static/
    ├── css/style.css
    └── js/results.js       # Chart.js realtime (ถ้าแยกไฟล์)
```

---

## Database Schema

```sql
-- ผู้ใช้งาน
CREATE TABLE users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL,
    email      VARCHAR(100) NOT NULL,
    password   VARCHAR(255) NOT NULL,          -- bcrypt hash
    full_name  VARCHAR(100) NOT NULL,          -- ใช้ตรวจสอบ vote ซ้ำข้ามบัญชี
    role       ENUM('voter','admin') NOT NULL DEFAULT 'voter',
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email    (email),
    UNIQUE KEY uq_users_fullname (full_name)   -- ป้องกัน vote ซ้ำระดับ DB
);

-- การเลือกตั้ง
CREATE TABLE elections (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    status      ENUM('pending','open','closed') NOT NULL DEFAULT 'pending',
    start_time  DATETIME,
    end_time    DATETIME,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ผู้สมัคร
CREATE TABLE candidates (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT NOT NULL,
    name        VARCHAR(100) NOT NULL,
    party       VARCHAR(100),
    bio         TEXT,
    photo_url   VARCHAR(255),
    number      INT,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
);

-- คะแนนเสียง
CREATE TABLE votes (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    candidate_id INT NOT NULL,
    election_id  INT NOT NULL,
    voted_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_votes_user_election (user_id, election_id),  -- 1 คน 1 สิทธิ์ ต่อ 1 วาระ
    FOREIGN KEY (user_id)      REFERENCES users(id)      ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (election_id)  REFERENCES elections(id)  ON DELETE CASCADE
);

-- OTP สำหรับยืนยันก่อน vote
CREATE TABLE otps (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    code       VARCHAR(6) NOT NULL,
    purpose    ENUM('vote','login') NOT NULL DEFAULT 'vote',
    used       BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

---

## API Routes

| Method | Path | คำอธิบาย | Auth |
|---|---|---|---|
| GET | `/` | หน้าแรก (รายการวาระ) | — |
| GET/POST | `/login` | เข้าสู่ระบบ | — |
| GET/POST | `/register` | สมัครสมาชิก | — |
| GET | `/logout` | ออกจากระบบ | ✅ |
| GET | `/request-otp/<election_id>` | สร้าง OTP และส่ง email | ✅ voter |
| GET/POST | `/verify-otp` | ยืนยัน OTP | ✅ voter |
| GET | `/candidates` | รายชื่อผู้สมัครทุกวาระ | — |
| GET | `/candidates/<election_id>` | ผู้สมัครของวาระใดวาระหนึ่ง | — |
| GET | `/candidates/<election_id>/export` | export Excel ผู้สมัคร | ✅ |
| GET/POST | `/vote/<election_id>` | หน้าลงคะแนน | ✅ voter + OTP |
| GET | `/results/<election_id>` | หน้าผลคะแนน | — |
| GET | `/results/<election_id>/json` | ผลคะแนน JSON (Chart.js) | — |
| GET | `/admin/` | Admin dashboard | ✅ admin |
| GET | `/admin/elections` | จัดการวาระ | ✅ admin |
| POST | `/admin/elections/create` | สร้างวาระใหม่ | ✅ admin |
| POST | `/admin/elections/<id>/status` | เปิด/ปิดวาระ | ✅ admin |
| POST | `/admin/elections/<id>/delete` | ลบวาระ | ✅ admin |
| GET | `/admin/elections/<id>/candidates` | รายการผู้สมัครในวาระ | ✅ admin |
| POST | `/admin/elections/<id>/candidates/add` | เพิ่มผู้สมัคร | ✅ admin |
| POST | `/admin/candidates/<id>/edit` | แก้ไขผู้สมัคร | ✅ admin |
| POST | `/admin/candidates/<id>/delete` | ลบผู้สมัคร | ✅ admin |
| GET | `/admin/elections/<id>/voters` | รายชื่อผู้ลงคะแนน | ✅ admin |
| GET | `/admin/elections/<id>/voters/export` | export Excel ผู้ลงคะแนน | ✅ admin |
| GET | `/admin/elections/<id>/results/export` | export Excel ผลคะแนน | ✅ admin |

---

## ติดตั้งและรัน

```bash
# 1. Clone และติดตั้ง dependencies
git clone https://github.com/Teng-404/EW.git
cd election-web
pip install -r requirements.txt

# 2. ตั้งค่า database
mysql -u root -p < schema.sql

# 3. ตั้งค่า environment variables
cp env.example .env
# แก้ไข DB_HOST, DB_USER, DB_PASSWORD, SECRET_KEY, MAIL_USERNAME, MAIL_PASSWORD

# 4. รัน
flask run
# เปิด http://localhost:5000
```

---

## Environment Variables

| ตัวแปร | ค่าตัวอย่าง | คำอธิบาย |
|---|---|---|
| `SECRET_KEY` | `your-secret-key` | Flask session secret |
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | `root` | MySQL user |
| `DB_PASSWORD` | `password` | MySQL password |
| `DB_NAME` | `election_db` | ชื่อฐานข้อมูล |
| `MAIL_SERVER` | `smtp.gmail.com` | SMTP server สำหรับส่ง OTP |
| `MAIL_PORT` | `587` | SMTP port |
| `MAIL_USE_TLS` | `true` | เปิด TLS |
| `MAIL_USERNAME` | `you@gmail.com` | อีเมลผู้ส่ง |
| `MAIL_PASSWORD` | `app-password` | App password ของ Gmail |
| `FLASK_ENV` | `development` | เลือก config (development/production) |

> **หมายเหตุ:** หากไม่ตั้งค่า `MAIL_USERNAME` ในโหมด development รหัส OTP จะถูก print ใน terminal แทน

---

## Security

- [x] bcrypt hash รหัสผ่าน
- [x] UNIQUE constraint ป้องกัน vote ซ้ำ (ระดับ DB) — ทั้ง `(user_id, election_id)` และ `full_name`
- [x] ตรวจสอบ `has_voted()` ก่อน vote (ระดับ app)
- [x] OTP ยืนยันตัวตนก่อนลงคะแนน (หมดอายุ 5 นาที, ใช้ได้ครั้งเดียว)
- [x] Flask-Login จัดการ session
- [x] Role-based access (voter / admin) ด้วย decorator `@admin_required`
- [x] CSRF protection (Flask-WTF) — เปิดใช้งานแล้ว
- [x] `SESSION_COOKIE_HTTPONLY` และ `SESSION_COOKIE_SAMESITE`
- [ ] Rate limiting (Flask-Limiter)
- [ ] HTTPS บน production (`SESSION_COOKIE_SECURE = True` ใน ProductionConfig)

---

## Requirements

```
Flask==3.0.0
Flask-Login==0.6.3
Flask-WTF==1.2.1
mysql-connector-python==8.3.0
bcrypt==4.1.2
python-dotenv==1.0.0
openpyxl==3.1.2
```
