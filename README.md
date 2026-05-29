# Election Website — ระบบเลือกตั้งออนไลน์

เว็บไซต์เลือกตั้งออนไลน์ครบวงจร สร้างด้วย Python (Flask) + MySQL รองรับการลงคะแนน แสดงผล และจัดการผู้สมัครในที่เดียว

---

## Tech Stack

| ส่วน | เทคโนโลยี |
|---|---|
| Backend | Python 3.10+, Flask |
| Database | MySQL 8.0+ |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| Auth | Flask-Login + bcrypt |

---

## ฟีเจอร์หลัก

- **ระบบ Authentication** — สมัคร/เข้าสู่ระบบ, ส่ง OTP ให้กับผู้เข้าระบบก่อนลงคะแนน, session management
- **ลงคะแนน** — 1 คน 1 สิทธิ์, ป้องกัน vote ซ้ำ (คนชื่อ-สกุลเดียวกันในระบบ vote ซ้ำไม่ได้), แยกวาระการลงคะแนนกันชัดเจน (ทำให้บัญชีใช้งานเลือกตั้งได้หลายครั้ง ไม่ใช่การลงเลือกตั้งเพียงรอบเดียว)
- **แสดงผลคะแนน** — กราฟ realtime ด้วย Chart.js , แยกกันหลาย ๆ วาระได้, สามารถบันทึกออกมาเป็น Excel ได้
- **ข้อมูลผู้สมัคร (แยกตามวาระ)** — รายชื่อ, พรรค, นโยบาย, สามารถบันทึกออกมาเป็น Excel ได้
- **ข้อมูลผู้ลงคะแนน (แยกตามวาระ)** — รายชื่อ, สามารถบันทึกออกมาเป็น Excel ได้
- **Admin Panel** — เพิ่ม/แก้ไข/ลบผู้สมัคร, เปิด-ปิดการเลือกตั้ง

---

## โครงสร้างโปรเจกต์หลัก

```
election-web/
├── app.py                  # Flask app หลัก
├── config.py               # ตั้งค่า DB และ secret key
├── requirements.txt
│
├── models/
│   ├── user.py             # User model
│   ├── candidate.py        # Candidate model
│   ├── vote.py             # Vote model
│   └── election.py         # Election model
│
├── routes/
│   ├── auth.py             # /login, /logout, /register
│   ├── vote.py             # /vote, /results
│   ├── candidates.py       # /candidates
│   └── admin.py            # /admin/*
│
├── templates/
│   ├── base.html
│   ├── index.html          # หน้าแรก
│   ├── vote.html           # หน้าลงคะแนน
│   ├── results.html        # หน้าผลคะแนน
│   ├── candidates.html     # หน้าผู้สมัคร
│   └── admin/
│       └── dashboard.html
│
└── static/
    ├── css/style.css
    └── js/results.js       # Chart.js realtime
```

---

## Database Schema

```sql
-- ผู้ใช้งาน
CREATE TABLE users (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50)  UNIQUE NOT NULL,
    email    VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,          -- bcrypt hash
    voted    BOOLEAN DEFAULT FALSE,
    role     ENUM('voter','admin') DEFAULT 'voter',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- การเลือกตั้ง
CREATE TABLE elections (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    title      VARCHAR(200) NOT NULL,
    status     ENUM('pending','open','closed') DEFAULT 'pending',
    start_time DATETIME,
    end_time   DATETIME
);

-- ผู้สมัคร
CREATE TABLE candidates (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT NOT NULL,
    name        VARCHAR(100) NOT NULL,
    party       VARCHAR(100),
    bio         TEXT,
    FOREIGN KEY (election_id) REFERENCES elections(id)
);

-- คะแนนเสียง
CREATE TABLE votes (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL UNIQUE,        -- UNIQUE = 1 คน 1 สิทธิ์
    candidate_id INT NOT NULL,
    election_id  INT NOT NULL,
    voted_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)      REFERENCES users(id),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
    FOREIGN KEY (election_id)  REFERENCES elections(id)
);
```

---

## API Routes

| Method | Path | คำอธิบาย | Auth |
|---|---|---|---|
| GET | `/` | หน้าแรก | — |
| GET/POST | `/login` | เข้าสู่ระบบ | — |
| GET/POST | `/register` | สมัครสมาชิก | — |
| GET | `/logout` | ออกจากระบบ | ✅ |
| GET | `/candidates` | รายชื่อผู้สมัคร | — |
| GET/POST | `/vote` | หน้าลงคะแนน | ✅ voter |
| GET | `/results` | ผลคะแนน (JSON) | — |
| GET | `/admin` | Admin dashboard | ✅ admin |
| POST | `/admin/candidate` | เพิ่มผู้สมัคร | ✅ admin |
| PUT | `/admin/election/status` | เปิด-ปิดเลือกตั้ง | ✅ admin |

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
cp .env.example .env
# แก้ไข DB_HOST, DB_USER, DB_PASSWORD, SECRET_KEY

# 4. รัน
flask run
# เปิด http://localhost:5000
```

---

## Security ที่ต้องทำ

- [x] bcrypt hash รหัสผ่าน
- [x] UNIQUE constraint ป้องกัน vote ซ้ำ (ระดับ DB)
- [x] ตรวจสอบ `voted = TRUE` ก่อน vote (ระดับ app)
- [x] Flask-Login จัดการ session
- [x] Role-based access (voter / admin)
- [ ] CSRF protection (Flask-WTF)
- [ ] Rate limiting (Flask-Limiter)
- [ ] HTTPS บน production

---

## Requirements

```
Flask==3.0.0
Flask-Login==0.6.3
Flask-WTF==1.2.1
mysql-connector-python==8.3.0
bcrypt==4.1.2
python-dotenv==1.0.0
```