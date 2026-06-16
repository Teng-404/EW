# Election Web — ระบบเลือกตั้งออนไลน์

เว็บไซต์เลือกตั้งออนไลน์ครบวงจร สร้างด้วย **Python (Flask) + MySQL** รองรับการยืนยันตัวตนด้วย OTP, ลงคะแนนแบบลับ-โปร่งใส, แสดงผลคะแนนแบบเรียลไทม์ และจัดการระบบผ่าน Admin Panel รองรับการใช้งานผ่าน Web Browser และอุปกรณ์เคลื่อนที่ (PWA)

---

## Tech Stack

| ส่วน | เทคโนโลยี |
|---|---|
| Backend | Python 3.10+, Flask 3.0 |
| Database | MySQL 8.0+ |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| Auth | Flask-Login + bcrypt + OTP (Email) |
| PWA | Service Worker + Web Manifest (ใช้ออฟไลน์ได้บางส่วน) |
| Export | openpyxl (Excel), reportlab (PDF + ฟอนต์ไทย) |
| Compatibility | Chrome, Firefox, Safari, Edge, Mobile (iOS/Android) |

---

## ฟีเจอร์หลัก

- **ระบบ Authentication (Admin/Staff)** — สมัคร/เข้าสู่ระบบ, session management, role-based access (`voter` / `admin`), bcrypt hash, CSRF protection
- **ยืนยันตัวตนสมาชิก (ขั้นที่ 1)** — กรอก Email → รับ OTP → ยืนยัน รองรับการเปลี่ยน Email ใหม่ ข้อมูลสมาชิกนำเข้าจาก Excel โดย admin
- **OTP ก่อนลงคะแนน (ขั้นที่ 2)** — ส่งรหัส 6 หลักทาง Email หมดอายุใน 5 นาที ใช้ได้ครั้งเดียว
- **1 OTP = 1 การลงคะแนน** — ลงคะแนนวาระถัดไปต้องขอ OTP ใหม่ ป้องกันการนำ session ไปใช้ซ้ำ
- **แยกประเภทวาระ** — รองรับ 3 ประเภท: ประธานกรรมการ / เหรัญญิก / กรรมการ แต่ละวาระกำหนดจำนวนสิทธิ์ลงคะแนน (`max_votes`) และเปิด/ซ่อนเมนูแยกกันได้
- **บัตรลงคะแนนลับ + ทะเบียนผู้มาใช้สิทธิโปร่งใส (v3)** — แยกตารางอย่างชัดเจน: `votes` เก็บเฉพาะคะแนน (ไม่มีตัวระบุผู้ลงคะแนน) / `vote_turnout` เก็บรายชื่อผู้มาใช้สิทธิ → ตรวจสอบได้ว่าใครมาลงคะแนน แต่ย้อนรอยไม่ได้ว่าใครเลือกใคร
- **กันลงคะแนนซ้ำ 2 ชั้น** — UNIQUE constraint ระดับ DB + ตรวจสอบในระดับ app
- **แสดงผลคะแนน Realtime** — เรียงตามคะแนนสูงสุด, อัปเดตทุก 10 วินาที (Chart.js), export PDF/Excel
- **ข้อมูลผู้สมัคร** — รูปภาพ (upload ไฟล์ หรือ URL), ชื่อ-นามสกุล, พรรค/กลุ่ม, นโยบาย/ประวัติ, หมายเลข (ตรวจสอบซ้ำในวาระเดียวกัน)
- **Log การใช้งาน** — บันทึก member_id, action, IP, ระบบ, เวลา; ค้นหาตามชื่อ/IP/ช่วงเวลา; export PDF/Excel
- **Admin Panel** — จัดการผู้ใช้, เปิด/ปิดระบบ, จัดการวาระ/ผู้สมัคร, นำเข้าสมาชิกจาก Excel, ดูรายชื่อผู้มาใช้สิทธิ, ออกรายงานครบชุด
- **Progressive Web App** — ติดตั้งบนมือถือได้, มีหน้า offline fallback, service worker ไม่แคชหน้า HTML ที่อ่อนไหว
- **PDF ภาษาไทย** — รองรับฟอนต์ Sarabun/TH Sarabun (ติดตั้งฟอนต์ที่ `static/fonts/` หรือ system fonts)

---

## ขั้นตอนการใช้งาน (User Flow)

### Flow A — สำหรับสมาชิก (ผู้ลงคะแนน)

#### ขั้นที่ 1 — ยืนยันตัวตน (ครั้งเดียว)

1. เปิดเว็บ → กดปุ่ม **ลงคะแนน** หรือเข้า `/verify`
2. กรอก **Email** ที่ admin ลงทะเบียนไว้ (ถ้าต้องการเปลี่ยน Email ใหม่ ใส่ที่ช่อง "Email ใหม่")
3. กดปุ่ม **ขอรหัส OTP** — ระบบส่ง OTP ไปยัง Email
4. กรอก OTP 6 หลัก → กด **ยืนยัน**

> หากระบบยืนยันตัวตนถูกระงับ (admin ปิด) จะแจ้ง "ยังไม่เปิดให้ใช้งานระบบ"

#### ขั้นที่ 2 — ลงคะแนน

1. ต้อง **เข้าสู่ระบบ (login)** ก่อน — ถ้ายังไม่มี account กดสมัครได้
2. กรอก Email (เดียวกับที่ยืนยันตัวตนไว้) → ขอ OTP → ยืนยัน
3. เลือกวาระที่ต้องการลงคะแนนจากหน้าแรก
4. เห็น **รูป + ชื่อ-สกุล + หมายเลข + นโยบาย** ของผู้สมัครทุกคน
5. เลือกได้ตามจำนวนที่ admin กำหนด (`max_votes`) → กด **ยืนยัน** → บันทึก
6. ลงคะแนนวาระต่อไปต้องขอ OTP ใหม่ (1 OTP = 1 ครั้ง)

### Flow B — สำหรับ Admin

1. `/login` → เข้าด้วยบัญชี admin (สร้างครั้งแรกผ่าน `python seed_admin.py`)
2. นำเข้าสมาชิกจาก Excel (`/admin/members/import`)
3. สร้างวาระและกำหนดผู้สมัคร (`/admin/elections`)
4. เปิดวาระ → เปิดระบบยืนยันตัวตน + ลงคะแนน (`/admin/system`)
5. ติดตามสถานการณ์ผ่าน dashboard / logs / reports
6. ปิดวาระเมื่อสิ้นสุด → export รายงาน

---

## โครงสร้างโปรเจกต์

```
election-web/
├── app.py                   # Flask application factory
├── config.py                # DB, mail, session, CSRF config
├── db.py                    # MySQL connection pool
├── schema.sql               # DDL ครบทุกตาราง
├── seed_admin.py            # สคริปต์สร้าง admin คนแรก
├── requirements.txt
│
├── models/
│   ├── user.py              # User (Flask-Login)
│   ├── member.py            # Member (จาก Excel)
│   ├── candidate.py         # Candidate
│   ├── election.py          # Election + ELECTION_TYPES
│   ├── vote.py              # Vote (ลับ) + Turnout (โปร่งใส) + OTP
│   ├── system_setting.py    # เปิด/ระงับระบบ
│   └── access_log.py        # บันทึก log
│
├── routes/
│   ├── auth.py              # /register, /login, /logout
│   ├── verify.py            # /verify, /verify/otp (ขั้นที่ 1)
│   ├── vote.py              # /vote, /vote/otp, /vote/ballot/*, /results
│   ├── candidates.py        # /candidates, /candidates/<id>
│   ├── admin.py             # /admin/* ทั้งหมด
│   ├── pwa.py               # /sw.js, /offline
│   └── export_utils.py      # Excel + PDF helper (ฟอนต์ไทย)
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── verify_identity.html
│   ├── verify_otp.html
│   ├── vote_request_otp.html
│   ├── vote_detail.html
│   ├── results.html
│   ├── candidates.html
│   ├── offline.html
│   ├── _pwa_head.html
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── users.html
│   │   ├── elections.html
│   │   ├── candidates.html
│   │   ├── voters.html        # ผู้มาใช้สิทธิ (Turnout)
│   │   ├── import_members.html
│   │   ├── system.html
│   │   ├── logs.html
│   │   └── reports.html
│   └── errors/
│       └── 403.html
│
└── static/
    ├── css/style.css
    ├── js/
    │   ├── app-dialog.js    # กล่อง confirm สไตล์แอพ
    │   └── sw.js            # Service Worker
    ├── fonts/               # วางฟอนต์ไทยที่นี่ (Sarabun-Regular.ttf ฯลฯ)
    ├── icons/               # PWA icons
    ├── manifest.webmanifest
    └── uploads/candidates/  # รูปผู้สมัครที่อัปโหลด
```

---

## Database Schema (สรุปย่อ — ดูเต็มที่ `schema.sql`)

| ตาราง | หน้าที่ | จุดสำคัญ |
|---|---|---|
| `users` | บัญชี admin/voter (ใช้ login) | bcrypt hash, UNIQUE username/email/full_name |
| `members` | สมาชิกที่นำเข้าจาก Excel | `verified` flag, `email_new` รองรับเปลี่ยน Email |
| `elections` | วาระเลือกตั้ง | `type` (president/treasurer/committee), `max_votes`, `is_visible`, `status` |
| `candidates` | ผู้สมัคร | `party`, `bio`, `photo_url`, UNIQUE (election_id, number) |
| **`votes`** | **บัตรลงคะแนน (ลับ)** | **ไม่มีตัวระบุผู้ลงคะแนน — เก็บแค่ candidate_id + election_id** |
| **`vote_turnout`** | **ทะเบียนผู้มาใช้สิทธิ (โปร่งใส)** | **member_id จริง, UNIQUE (member_id, election_id) กันลงคะแนนซ้ำ** |
| `otps` | OTP | purpose: `verify` / `vote`, หมดอายุ 5 นาที |
| `access_logs` | Log การใช้งาน | member_id, action, IP, system_type, เวลา |
| `system_settings` | เปิด/ระงับระบบ | `verify_enabled`, `vote_enabled` |

> **หลักการความลับ-โปร่งใส (v3):** แยก "ผลคะแนน" กับ "การมาใช้สิทธิ" ออกจากกัน — `votes` ตอบได้ว่า "ผู้สมัครคนไหนได้กี่คะแนน" แต่ตอบไม่ได้ว่า "ใครเลือกใคร"; `vote_turnout` ตอบได้ว่า "ใครมาลงคะแนนแล้วบ้าง" แต่ไม่เก็บว่าเลือกใคร เมื่อต้องตรวจสอบความถูกต้องของการเลือกตั้งจะใช้ทั้งสองตารางแยกกัน

---

## API Routes

### Public

| Method | Path | คำอธิบาย |
|---|---|---|
| GET | `/` | หน้าแรก (เมนูวาระทั้งหมด) |
| GET | `/candidates` | ผู้สมัครทุกวาระ |
| GET | `/candidates/<id>` | ผู้สมัครของวาระเดียว |
| GET | `/results` | ผลคะแนนเรียลไทม์ทุกวาระ |
| GET | `/results/json` | JSON สำหรับ Chart.js |

### Authentication

| Method | Path | คำอธิบาย |
|---|---|---|
| GET/POST | `/register` | สมัครสมาชิก (สำหรับ admin/staff) |
| GET/POST | `/login` | เข้าสู่ระบบ |
| GET | `/logout` | ออกจากระบบ |

### Verify Identity (ขั้นที่ 1)

| Method | Path | คำอธิบาย |
|---|---|---|
| GET/POST | `/verify` | กรอก Email ขอ OTP |
| GET/POST | `/verify/otp` | กรอก OTP ยืนยัน |

### Vote (ขั้นที่ 2)

| Method | Path | คำอธิบาย | Auth |
|---|---|---|---|
| GET/POST | `/vote` | ขอ OTP ลงคะแนน | login |
| GET/POST | `/vote/otp` | กรอก OTP | login |
| GET | `/vote/ballot/<election_id>` | หน้าผู้สมัคร | login + OTP |
| POST | `/vote/ballot/<election_id>/submit` | บันทึกคะแนน | login + OTP |

### Admin

| Method | Path | คำอธิบาย |
|---|---|---|
| GET | `/admin/` | Dashboard |
| GET | `/admin/users` | จัดการผู้ใช้งาน |
| POST | `/admin/users/create` | เพิ่ม user (รองรับ role) |
| POST | `/admin/users/<id>/edit` | เปลี่ยนรหัสผ่าน |
| POST | `/admin/users/<id>/delete` | ลบ user |
| POST | `/admin/users/<id>/role` | เปลี่ยน role |
| POST | `/admin/users/<id>/toggle-active` | เปิด/ระงับบัญชี |
| GET | `/admin/elections` | จัดการวาระ |
| POST | `/admin/elections/create` | สร้างวาระ |
| POST | `/admin/elections/<id>/status` | เปลี่ยนสถานะ |
| POST | `/admin/elections/<id>/settings` | แก้ไขการตั้งค่า |
| POST | `/admin/elections/<id>/delete` | ลบวาระ |
| GET | `/admin/elections/<id>/candidates` | จัดการผู้สมัคร |
| POST | `/admin/elections/<id>/candidates/add` | เพิ่มผู้สมัคร (upload รูป) |
| POST | `/admin/candidates/<id>/edit` | แก้ไขผู้สมัคร |
| POST | `/admin/candidates/<id>/delete` | ลบผู้สมัคร |
| GET | `/admin/elections/<id>/voters` | รายชื่อผู้มาใช้สิทธิ |
| GET | `/admin/elections/<id>/voters/export` | export ผู้มาใช้สิทธิ (Excel/PDF) |
| GET | `/admin/elections/<id>/results/export` | export ผลคะแนนวาระเดียว |
| GET/POST | `/admin/members/import` | นำเข้าสมาชิกจาก Excel |
| GET/POST | `/admin/system` | เปิด/ระงับระบบ |
| GET | `/admin/logs` | ดู Log |
| GET | `/admin/logs/export` | export Log (Excel/PDF) |
| GET | `/admin/reports` | ภาพรวมรายงาน |
| GET | `/admin/reports/verified/export` | export สมาชิกที่ยืนยันแล้ว |
| GET | `/admin/reports/email-changed/export` | export สมาชิกที่เปลี่ยน Email |
| GET | `/admin/reports/votes/export` | export ผู้มาใช้สิทธิทุกวาระ |
| GET | `/admin/reports/summary/export` | export จำนวนผู้มาลงคะแนน |
| GET | `/admin/reports/results/export` | export ผลคะแนนรวมทุกวาระ |
| POST | `/admin/reset` | รีเซ็ตข้อมูล (พิมพ์ RESET ยืนยัน) |

### PWA

| Method | Path | คำอธิบาย |
|---|---|---|
| GET | `/sw.js` | Service Worker |
| GET | `/offline` | หน้าออฟไลน์ fallback |

---

## ติดตั้งและรัน

### 1. Clone และติดตั้ง dependencies

```bash
git clone https://github.com/Teng-404/EW.git
cd election-web
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. ตั้งค่า database

```bash
mysql -u root -p < schema.sql
```

### 3. ตั้งค่า environment variables

สร้างไฟล์ `.env` ที่ root:

```env
SECRET_KEY=change-this-in-production
DB_HOST=localhost
DB_PORT=3307
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=election_db

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=you@gmail.com
MAIL_PASSWORD=your-app-password

FLASK_ENV=development
```

### 4. สร้าง admin คนแรก

```bash
python seed_admin.py
# จะถามชื่อ-สกุล / username / email / รหัสผ่าน
# สร้าง user ที่ role='admin' ให้อัตโนมัติ
```

### 5. (Optional) ติดตั้งฟอนต์ไทยสำหรับ PDF

```bash
# ตัวเลือก 1: วางไฟล์ Sarabun-Regular.ttf ที่ static/fonts/
mkdir -p static/fonts
# ดาวน์โหลดจาก https://fonts.google.com/specimen/Sarabun

# ตัวเลือก 2: ติดตั้งจาก system (Ubuntu/Debian)
sudo apt install fonts-tlwg-sarabun
```

> ถ้าไม่ติดตั้งฟอนต์ไทย PDF จะใช้ Helvetica และตัวอักษรไทยจะหาย (Excel ไม่กระทบ)

### 6. รัน

```bash
flask run
# หรือ
python app.py
```

เปิด `http://localhost:5000`

---

## Environment Variables

| ตัวแปร | ค่าตัวอย่าง | คำอธิบาย |
|---|---|---|
| `SECRET_KEY` | `random-string` | Flask session secret (สุ่มใหม่ใน production) |
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3307` | MySQL port |
| `DB_USER` | `root` | MySQL user |
| `DB_PASSWORD` | `password` | MySQL password |
| `DB_NAME` | `election_db` | ชื่อฐานข้อมูล |
| `MAIL_SERVER` | `smtp.gmail.com` | SMTP server สำหรับส่ง OTP |
| `MAIL_PORT` | `587` | SMTP port |
| `MAIL_USE_TLS` | `true` | เปิด TLS |
| `MAIL_USERNAME` | `you@gmail.com` | Email ผู้ส่ง OTP |
| `MAIL_PASSWORD` | `app-password` | App password (สำหรับ Gmail) |
| `FLASK_ENV` | `development` | `development` / `production` |

> **โหมด development:** ถ้าไม่ตั้ง `MAIL_USERNAME` ระบบจะ **print OTP ใน terminal** แทนการส่งจริง — สะดวกสำหรับการพัฒนา/ทดสอบ

---

## Security

- [x] bcrypt hash รหัสผ่าน (cost factor default)
- [x] ยืนยันตัวตนสมาชิกด้วย Email + OTP
- [x] OTP หมดอายุใน 5 นาที, ใช้ได้ครั้งเดียว, สร้างใหม่ → invalidate ของเก่า
- [x] **บัตรลงคะแนนเป็นความลับ** — ไม่เก็บตัวระบุผู้ลงคะแนนในตาราง `votes` เลย ตรวจสอบย้อนกลับไม่ได้
- [x] **ทะเบียนผู้มาใช้สิทธิโปร่งใส** — เก็บใน `vote_turnout` แยกตาราง สำหรับตรวจสอบและกันการลงคะแนนซ้ำ
- [x] **1 OTP = 1 การลงคะแนน** — ใช้ flag `vote_authorized` ใน session ลบทันทีหลังลงคะแนน
- [x] UNIQUE constraint ป้องกัน vote ซ้ำระดับ DB (`vote_turnout`)
- [x] บันทึก Log ทุกการเข้าใช้งาน (member_id, action, IP, ระบบ, เวลา)
- [x] ระบบเปิด/ระงับแยกกันระหว่าง verify และ vote
- [x] Upsert สมาชิกแบบปลอดภัย — สมาชิกที่ verified แล้วจะไม่ถูกแตะตอน import
- [x] Flask-Login + CSRF protection (Flask-WTF)
- [x] `SESSION_COOKIE_HTTPONLY=True` + `SESSION_COOKIE_SAMESITE=Lax`
- [x] Service Worker ไม่แคชหน้า HTML ที่มีข้อมูลอ่อนไหว (CSRF, OTP, admin)
- [ ] Rate limiting (Flask-Limiter) — *แนะนำให้เพิ่มก่อน production*
- [ ] HTTPS บน production (`SESSION_COOKIE_SECURE=True` เปิดอัตโนมัติเมื่อ `FLASK_ENV=production`)

---

## รายงานที่ระบบออกได้

| รายงาน | Format | เนื้อหา |
|---|---|---|
| สมาชิกที่ยืนยันตัวตนผ่านระบบ | PDF, Excel | ลำดับ, ชื่อ-สกุล, Email เดิม, Email ใหม่ |
| สมาชิกที่เปลี่ยน Email | PDF, Excel | เฉพาะคนที่มี `email_new` |
| รายชื่อผู้มาใช้สิทธิ (turnout) | PDF, Excel | วาระ, ชื่อ-สกุล, เวลาที่ลงคะแนน |
| สรุปจำนวนผู้มาลงคะแนน | PDF, Excel | วาระ, ประเภท, สถานะ, จำนวน |
| สรุปผลคะแนนรวมทุกวาระ | PDF, Excel | วาระ, หมายเลข, ชื่อ, คะแนน, % |
| Log การใช้งานระบบ | PDF, Excel | กรองตามชื่อ/IP/ช่วงเวลา/ระบบ |

> รายงาน PDF ใช้ฟอนต์ไทย (Sarabun) แนวนอน A4 เมื่อคอลัมน์ ≥ 5

---

## คำสั่งจัดการระบบ

```bash
# สร้าง admin คนแรก (รันครั้งเดียว)
python seed_admin.py

# รีเซ็ตข้อมูลผลเลือกตั้งทั้งหมด (จาก UI)
# /admin → Danger Zone → พิมพ์ "RESET"

# ส่ง MAIL_USERNAME ว่างไว้ → OTP จะ print ใน terminal (dev mode)
```

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

---

## Changelog

### v3 (current)
- **เปลี่ยน design ของ vote storage** — แยก `votes` (ลับ) กับ `vote_turnout` (โปร่งใส)
- ลบ `member_id_hash` ออกจากตาราง `votes` — บัตรลงคะแนนไม่ผูกกับผู้ลงคะแนนอีกต่อไป
- เพิ่มหน้า `/admin/elections/<id>/voters` — ดูรายชื่อผู้มาใช้สิทธิ
- เปลี่ยน OTP เป็น 1 ครั้งต่อ 1 การลงคะแนน (`vote_authorized` flag)
- เพิ่ม `seed_admin.py` สำหรับสร้าง admin คนแรก
- เพิ่ม PWA support + Service Worker
- รองรับ PDF ภาษาไทย (Sarabun)
- แก้ไข logic bug ใน admin (create_user, voters route, logs template)

### v2
- เพิ่มประเภทวาระ (president/treasurer/committee)
- เพิ่ม `max_votes` รองรับเลือกหลายคนต่อวาระ
- เพิ่ม `is_visible` ซ่อน/แสดงเมนู
- รองรับการอัปโหลดรูปผู้สมัคร

### v1
- ระบบ verify ด้วย OTP
- ลงคะแนนพื้นฐาน
- Admin panel
