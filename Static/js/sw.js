/* ============================================================
   Election Web — Service Worker
   ------------------------------------------------------------
   นโยบายแคช (ออกแบบเพื่อความปลอดภัยของระบบเลือกตั้ง):

   • แคชเฉพาะ "static shell" เท่านั้น: CSS, ไอคอน, หน้า offline
   • ไม่แคชหน้า HTML ใด ๆ เลย — เพราะหน้าเหล่านั้นมีข้อมูลที่
     เปลี่ยนตลอด/อ่อนไหว (CSRF token, สถานะ OTP, หน้า admin,
     ผลคะแนนเรียลไทม์) การแคชไว้จะทำให้เห็นข้อมูลเก่าหรือรั่วได้
   • ไม่แตะ request ที่ไม่ใช่ GET (POST ลงคะแนน/ยืนยัน OTP ฯลฯ)
   • navigation = network-first เสมอ ถ้าออฟไลน์ค่อย fallback
     ไปหน้า offline กลาง ๆ
   เวอร์ชันแคช: เปลี่ยนเลขเมื่อแก้ไฟล์ static เพื่อ bust cache
   ============================================================ */

const CACHE_VERSION = "ew-static-v1";

// static shell ที่ปลอดภัยต่อการแคช (ไม่มีข้อมูลผู้ใช้)
const PRECACHE_URLS = [
  "/offline",
  "/static/css/style.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/apple-touch-icon.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) =>
      // addAll จะ fail ทั้งชุดถ้ามีไฟล์ใดโหลดไม่ได้ จึงใช้ทีละไฟล์แบบ tolerant
      Promise.allSettled(PRECACHE_URLS.map((u) => cache.add(u)))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // 1) ไม่แตะอะไรที่ไม่ใช่ GET (POST/PUT/DELETE — ลงคะแนน, ยืนยัน OTP, admin actions)
  if (req.method !== "GET") return;

  // 2) ข้ามคำขอข้ามโดเมน (Google Fonts, CDN) ปล่อยให้ browser cache จัดการเอง
  if (url.origin !== self.location.origin) return;

  // 3) static assets ที่ปลอดภัย → cache-first (เร็วและประหยัดเน็ต)
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((res) => {
          if (res && res.status === 200 && res.type === "basic") {
            const copy = res.clone();
            caches.open(CACHE_VERSION).then((c) => c.put(req, copy));
          }
          return res;
        });
      })
    );
    return;
  }

  // 4) การเปิดหน้า (navigation) → network-first เสมอ, ออฟไลน์ค่อย fallback
  //    *** ไม่แคชผลลัพธ์ HTML ใด ๆ ***
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).catch(() =>
        caches.match("/offline").then((r) => r || new Response(
          "ออฟไลน์ — กรุณาเชื่อมต่ออินเทอร์เน็ตเพื่อใช้งานระบบเลือกตั้ง",
          { headers: { "Content-Type": "text/plain; charset=utf-8" }, status: 503 }
        ))
      )
    );
    return;
  }

  // 5) อย่างอื่น (เช่น fetch /results/json) → network-only ไม่แคช
  //    ผลคะแนนต้องสด ห้ามเสิร์ฟของเก่า
});
