# Election Web — ระบบเลือกตั้งออนไลน์

เว็บไซต์เลือกตั้งออนไลน์ครบวงจร สร้างด้วย Python (Flask) + MySQL รองรับการยืนยันตัวตน, ลงคะแนน, แสดงผล และจัดการผู้สมัครในที่เดียว รองรับ Concurrent Users และใช้งานผ่าน Web Browser หรืออุปกรณ์เคลื่อนที่ได้

---

## Tech Stack

| ส่วน | เทคโนโลยี |
|---|---|
| Backend | Python 3.10+, Flask |
| Database | MySQL 8.0+ (Open Source) |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| Auth | Flask-Login + bcrypt + OTP (Email) |
| Compatibility | Chrome, IE 8+, Mobile (Smartphone/Tablet) |

---

## ฟีเจอร์หลัก

- **ระบบ Authentication** — สมัคร/เข้าสู่ระบบ, session management, role-based access (voter / admin)
- **ยืนยันตัวตนสมาชิก** — กรอก Email เพื่อรับ OTP ก่อนลงคะแนน (ข้อมูลสมาชิกสามารถนำเข้าจาก Excel โดย admin)
- **OTP ก่อนลงคะแนน** — ส่งรหัส OTP ทาง Email ยืนยันตัวตนก่อน vote ทุกครั้ง, หมดอายุใน 5 นาที
- **แยกประเภทวาระ** — รองรับ 3 ประเภท: ประธานกรรมการ / เหรัญญิก / คณะกรรมการ แต่ละประเภทกำหนดจำนวนสิทธิ์ลงคะแนนได้แยกกัน
- **ลงคะแนน** — 1 คน 1 สิทธิ์ต่อวาระ, ป้องกัน vote ซ้ำทั้งระดับ DB และระดับ app, เข้ารหัสข้อมูลผู้เลือกไว้ในระบบ
- **แสดงผลคะแนน Realtime** — เรียงตามคะแนนสูงสุด, อัปเดตอัตโนมัติ (Chart.js), export PDF/Excel
- **ข้อมูลผู้สมัคร** — รูปภาพ, ชื่อ-นามสกุล, หมายเลข (ตรวจสอบซ้ำ), export Excel
- **Log การใช้งาน** — บันทึกเลขสมาชิก, วันที่, เวลา, IP, ระบบที่เข้าใช้งาน; ค้นหาตามชื่อ/IP/ช่วงเวลา; export PDF/Excel
- **Admin Panel** — จัดการผู้ใช้, เปิด/ปิดระบบ, กำหนดผู้สมัคร, นำเข้าสมาชิกจาก Excel, ออกรายงานครบชุด

---

## ขั้นตอนการใช้งาน (User Flow)

### ขั้นที่ 1 — ยืนยันตัวตนเพื่อขอเลือกตั้งออนไลน์

1. กรอก **Email** เพื่อขอ OTP
2. กดปุ่ม **ขอรหัส OTP** — ระบบส่ง OTP ไปยัง Email ที่ลงทะเบียนไว้
3. กรอก OTP ที่ได้รับแล้วกด **ยืนยัน**

> หากระบบถูกระงับการใช้งาน เมื่อกดขอ OTP จะแจ้ง "ยังไม่เปิดให้ใช้งานระบบ"

### ขั้นที่ 2 — ลงคะแนนเลือกตั้งออนไลน์

1. กรอก Email เพื่อขอ OTP (ใช้ Email เดียวกับขั้นที่ 1)
2. กดขอ OTP → กรอก OTP → ยืนยัน
3. เข้าสู่หน้าหลัก มีเมนูด้านซ้ายตามที่ Admin เปิดไว้:
   - เลือกตั้งประธานกรรมการ
   - เลือกตั้งเหรัญญิก
   - เลือกตั้งกรรมการ
4. แต่ละเมนูแสดง **รูปภาพ, ชื่อ-สกุล, หมายเลขผู้สมัคร** พร้อมปุ่มเลือก
5. สมาชิกเลือกได้ตามจำนวนที่ Admin กำหนด → บันทึกแล้ว **ไม่สามารถแก้ไขได้**

---

## โครงสร้างโปรเจกต์หลัก

```
election-web/
├── app.py                  # Flask app (application factory)
├── config.py               # ตั้งค่า DB, mail, session, CSRF
├── db.py                   # MySQL connection pool (Flask g)
├── schema.sql              # DDL สร้างตาราง
├── requirements.txt
│
├── models/
│   ├── user.py             # User model (Flask-Login UserMixin)
│   ├── member.py           # Member model (ข้อมูลสมาชิกสหกรณ์ที่นำเข้าจาก Excel)
│   ├── candidate.py        # Candidate model
│   ├── vote.py             # Vote model + OTP helper
│   └── election.py         # Election model
│
├── routes/
│   ├── auth.py             # /verify-identity, /request-otp, /verify-otp
│   ├── vote.py             # /vote, /vote/<type>, /results/<type>
│   ├── candidates.py       # /candidates/<type>, /candidates/<type>/export
│   └── admin.py            # /admin/*
│
├── templates/
│   ├── base.html
│   ├── index.html              # หน้าแรก
│   ├── verify_identity.html    # ยืนยันตัวตน (ขั้นที่ 1)
│   ├── verify_otp.html         # กรอก OTP
│   ├── vote.html               # เมนูลงคะแนน (ซ้าย)
│   ├── vote_detail.html        # รายชื่อผู้สมัคร + เลือก
│   ├── results.html            # ผลคะแนน Realtime
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── users.html
│   │   ├── elections.html      # กำหนดวาระ + สิทธิ์จำนวนเลือก
│   │   ├── candidates.html     # เพิ่ม/แก้ไข/ลบผู้สมัคร
│   │   ├── import_members.html # นำเข้า Excel สมาชิก
│   │   ├── logs.html           # Log การใช้งาน
│   │   └── reports.html        # รายงาน PDF/Excel
│   └── errors/
│       └── 403.html
│
└── static/
    ├── css/style.css
    └── js/results.js       # Chart.js realtime
```

---

## Database Schema

```sql
-- ผู้ใช้งาน (Admin)
CREATE TABLE users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL,
    email      VARCHAR(100) NOT NULL,
    password   VARCHAR(255) NOT NULL,          -- bcrypt hash
    full_name  VARCHAR(100) NOT NULL,
    role       ENUM('voter','admin') NOT NULL DEFAULT 'voter',
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email    (email),
    UNIQUE KEY uq_users_fullname (full_name)
);

-- สมาชิก (นำเข้าจาก Excel)
CREATE TABLE members (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(100),               -- Email (ใช้รับ OTP)
    email_new       VARCHAR(100),               -- Email ใหม่หากเปลี่ยนแปลง (ขั้นยืนยันตัวตน)
    verified        BOOLEAN NOT NULL DEFAULT FALSE,  -- ผ่านขั้นยืนยันตัวตนแล้ว
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- การเลือกตั้ง (แยกตามประเภท)
CREATE TABLE elections (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    type            ENUM('president','treasurer','committee') NOT NULL,  -- ประธาน/เหรัญญิก/กรรมการ
    max_votes       INT NOT NULL DEFAULT 1,    -- จำนวนสิทธิ์ที่เลือกได้
    is_visible      BOOLEAN NOT NULL DEFAULT TRUE,  -- แสดงเมนูหรือไม่
    status          ENUM('pending','open','closed') NOT NULL DEFAULT 'pending',
    start_time      DATETIME,
    end_time        DATETIME,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      INT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ผู้สมัคร
CREATE TABLE candidates (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT NOT NULL,
    name        VARCHAR(100) NOT NULL,
    photo_url   VARCHAR(255),
    number      INT NOT NULL,                  -- ป้อนเอง (ตรวจสอบซ้ำภายใน election)
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_candidates_election_number (election_id, number),  -- เลขผู้สมัครซ้ำไม่ได้ในวาระเดียวกัน
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
);

-- คะแนนเสียง (เข้ารหัสผู้เลือก)
CREATE TABLE votes (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    member_id_hash  VARCHAR(255) NOT NULL,     -- เข้ารหัสเลขสมาชิก
    candidate_id    INT NOT NULL,
    election_id     INT NOT NULL,
    voted_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_votes_member_election (member_id_hash, election_id),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (election_id)  REFERENCES elections(id)  ON DELETE CASCADE
);

-- OTP
CREATE TABLE otps (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    member_id  INT         NOT NULL,
    code       VARCHAR(6)  NOT NULL,
    purpose    ENUM('verify','vote') NOT NULL DEFAULT 'vote',
    used       BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

-- Log การใช้งาน
CREATE TABLE access_logs (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    member_id   INT,                           -- FK สมาชิก (ถ้ามี)
    action      VARCHAR(100) NOT NULL,         -- ประเภทคำสั่ง
    ip_address  VARCHAR(45)  NOT NULL,
    system_type VARCHAR(50),                   -- ระบบที่เข้าใช้งาน
    logged_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE SET NULL
);
```

---

## API Routes

| Method | Path | คำอธิบาย | Auth |
|---|---|---|---|
| GET/POST | `/verify` | ยืนยันตัวตนสมาชิก (ขั้นที่ 1) | — |
| POST | `/verify/request-otp` | ขอ OTP สำหรับยืนยันตัวตน | — |
| GET/POST | `/verify/otp` | กรอก OTP ยืนยันตัวตน | — |
| GET/POST | `/vote` | เข้าสู่ระบบเลือกตั้ง (ขั้นที่ 2) | — |
| POST | `/vote/request-otp` | ขอ OTP สำหรับลงคะแนน | — |
| GET/POST | `/vote/otp` | กรอก OTP ลงคะแนน | — |
| GET | `/vote/ballot` | หน้าหลักลงคะแนน (เมนูซ้าย) | ✅ OTP |
| GET | `/vote/ballot/<type>` | รายชื่อผู้สมัครตามประเภท | ✅ OTP |
| POST | `/vote/ballot/<type>/submit` | บันทึกคะแนน | ✅ OTP |
| GET | `/results` | ผลคะแนน Realtime (ทุกประเภท) | — |
| GET | `/results/json` | ผลคะแนน JSON (Chart.js) | — |
| GET | `/admin/` | Admin dashboard | ✅ admin |
| GET | `/admin/users` | จัดการผู้ใช้งาน | ✅ admin |
| POST | `/admin/users/create` | เพิ่มผู้ใช้งาน | ✅ admin |
| POST | `/admin/users/<id>/edit` | แก้ไข/เปลี่ยนรหัสผ่าน | ✅ admin |
| POST | `/admin/users/<id>/delete` | ลบผู้ใช้งาน | ✅ admin |
| GET | `/admin/elections` | จัดการวาระ (กำหนด is_visible, max_votes) | ✅ admin |
| POST | `/admin/elections/<id>/status` | เปิด/ปิดวาระ | ✅ admin |
| GET | `/admin/elections/<id>/candidates` | รายการผู้สมัครในวาระ | ✅ admin |
| POST | `/admin/elections/<id>/candidates/add` | เพิ่มผู้สมัคร | ✅ admin |
| POST | `/admin/candidates/<id>/edit` | แก้ไขผู้สมัคร | ✅ admin |
| POST | `/admin/candidates/<id>/delete` | ลบผู้สมัคร | ✅ admin |
| GET/POST | `/admin/members/import` | นำเข้า Excel สมาชิก (ลบข้อมูลเก่าก่อน) | ✅ admin |
| GET | `/admin/system` | กำหนดการเข้าใช้งาน (เปิด/ระงับแต่ละระบบ) | ✅ admin |
| GET | `/admin/logs` | ดู Log การใช้งาน | ✅ admin |
| GET | `/admin/logs/export` | export Log เป็น PDF/Excel | ✅ admin |
| GET | `/admin/reports` | รายงานทั้งหมด | ✅ admin |
| GET | `/admin/reports/verified/export` | export สมาชิกที่ยืนยันตัวตนแล้ว | ✅ admin |
| GET | `/admin/reports/email-changed/export` | export สมาชิกที่เปลี่ยน Email | ✅ admin |
| GET | `/admin/reports/votes/export` | export ผลการลงคะแนน (เข้ารหัส) | ✅ admin |
| GET | `/admin/reports/summary/export` | export สรุปจำนวนผู้มาลงคะแนน | ✅ admin |
| GET | `/admin/reports/results/export` | export สรุปผลคะแนน | ✅ admin |
| POST | `/admin/reset` | ลบข้อมูลผลเลือกตั้งและการยืนยันตัวตนทั้งหมด | ✅ admin |

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
| `MAIL_USERNAME` | `you@gmail.com` | Email ผู้ส่ง |
| `MAIL_PASSWORD` | `app-password` | App password ของ Gmail |
| `FLASK_ENV` | `development` | เลือก config (development/production) |

> **หมายเหตุ:** ในโหมด development หากไม่ตั้งค่า `MAIL_USERNAME` รหัส OTP จะถูก print ใน terminal แทน

---

## Security

- [x] bcrypt hash รหัสผ่าน (admin)
- [x] ยืนยันตัวตนสมาชิกด้วย Email (ข้อมูลนำเข้าจาก Excel โดย admin)
- [x] OTP ทาง Email ยืนยันก่อนลงคะแนน (หมดอายุ 5 นาที, ใช้ได้ครั้งเดียว)
- [x] เข้ารหัสข้อมูลผู้เลือกใน `votes` (ไม่เปิดเผยว่าใครเลือกใคร แม้แต่ในรายงาน)
- [x] UNIQUE constraint ป้องกัน vote ซ้ำระดับ DB
- [x] บันทึก Log ทุกการเข้าใช้งาน (IP, เวลา, ระบบ)
- [x] ระบบเปิด/ระงับแยกกันระหว่าง "ยืนยันตัวตน" และ "ลงคะแนน"
- [x] นำเข้าข้อมูลสมาชิกใหม่จะลบข้อมูลเก่าทั้งหมดก่อน (ป้องกัน stale data)
- [x] Flask-Login + CSRF protection (Flask-WTF)
- [x] `SESSION_COOKIE_HTTPONLY` และ `SESSION_COOKIE_SAMESITE`
- [ ] Rate limiting (Flask-Limiter)
- [ ] HTTPS บน production (`SESSION_COOKIE_SECURE = True`)

---

## รายงานที่ระบบออกได้

| รายงาน | Format |
|---|---|
| สมาชิกที่ยืนยันตัวตนผ่านระบบออนไลน์ | PDF, Excel |
| สมาชิกที่เปลี่ยน Email ผ่านระบบ | PDF, Excel |
| ผลการลงคะแนนรายบุคคล (เข้ารหัสสมาชิก) | PDF, Excel |
| สรุปจำนวนผู้มาลงคะแนน | PDF, Excel |
| สรุปผลคะแนนรวม | PDF, Excel |
| Log การใช้งานระบบ (กรองตามเงื่อนไข) | PDF, Excel |

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
reportlab==4.1.0
```
