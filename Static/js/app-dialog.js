/* =========================================================================
 *  app-dialog.js  —  กล่อง popup สไตล์แอพ (แทน confirm()/alert() ของเบราว์เซอร์)
 *  วิธีใช้:  <script src="/static/js/app-dialog.js"></script>
 *  จากนั้นเรียก:
 *      const ok = await appConfirm({ message: 'ปิดวาระนี้?' });
 *      if (ok) { ... }
 *
 *      await appAlert({ message: 'บันทึกเรียบร้อย' });
 * ========================================================================= */
(function () {
  'use strict';

  // ---- ฉีด CSS เข้าไปครั้งเดียว (ปรับสีตรงนี้ให้ตรงธีมได้) -------------------
  const PALETTE = {
    navy:      '#16213e',   // สีหัวเว็บ / ปุ่มหลัก
    navyDark:  '#0f1830',
    blue:      '#2563eb',   // ปุ่มยืนยันปกติ
    danger:    '#dc2626',   // ปุ่มยืนยันแบบลบ/ปิด (destructive)
    text:      '#1f2937',
    subtext:   '#6b7280',
    border:    '#e5e7eb',
    overlay:   'rgba(15, 23, 42, .55)',
  };

  const css = `
  .appdlg-overlay{
    position:fixed; inset:0; z-index:99999;
    display:flex; align-items:center; justify-content:center;
    background:${PALETTE.overlay};
    opacity:0; transition:opacity .15s ease;
    font-family:inherit;
  }
  .appdlg-overlay.is-open{ opacity:1; }
  .appdlg{
    width:min(420px, calc(100vw - 40px));
    background:#fff; border-radius:16px;
    box-shadow:0 20px 60px rgba(0,0,0,.35);
    overflow:hidden;
    transform:translateY(8px) scale(.97);
    transition:transform .18s cubic-bezier(.2,.8,.2,1);
  }
  .appdlg-overlay.is-open .appdlg{ transform:translateY(0) scale(1); }
  .appdlg-head{
    background:${PALETTE.navy}; color:#fff;
    padding:16px 22px; font-size:15px; font-weight:600;
    display:flex; align-items:center; gap:10px;
  }
  .appdlg-head .appdlg-icon{
    width:22px; height:22px; flex:0 0 22px;
    display:flex; align-items:center; justify-content:center;
  }
  .appdlg-body{ padding:22px; }
  .appdlg-message{
    color:${PALETTE.text}; font-size:16px; line-height:1.5; margin:0;
    white-space:pre-line;
  }
  .appdlg-foot{
    display:flex; justify-content:flex-end; gap:10px;
    padding:0 22px 20px;
  }
  .appdlg-btn{
    border:0; cursor:pointer; border-radius:10px;
    padding:10px 20px; font-size:14px; font-weight:600;
    font-family:inherit; transition:filter .12s ease, background .12s ease;
  }
  .appdlg-btn:focus-visible{ outline:3px solid rgba(37,99,235,.4); outline-offset:2px; }
  .appdlg-btn-cancel{ background:#f3f4f6; color:${PALETTE.text}; }
  .appdlg-btn-cancel:hover{ background:#e5e7eb; }
  .appdlg-btn-ok{ background:${PALETTE.blue}; color:#fff; }
  .appdlg-btn-ok:hover{ filter:brightness(1.07); }
  .appdlg-btn-ok.is-danger{ background:${PALETTE.danger}; }
  `;

  const styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // ---- ตัวสร้างกล่อง ---------------------------------------------------------
  /**
   * @param {Object}  opt
   * @param {string}  opt.message      ข้อความหลัก
   * @param {string} [opt.title]       หัวกล่อง (ดีฟอลต์ = ชื่อแอพ)
   * @param {string} [opt.okText]      ข้อความปุ่มยืนยัน
   * @param {string} [opt.cancelText]  ข้อความปุ่มยกเลิก
   * @param {boolean}[opt.danger]      true = ปุ่มยืนยันเป็นสีแดง (สำหรับลบ/ปิด)
   * @param {boolean}[opt.alert]       true = แสดงปุ่มเดียว (โหมด alert)
   * @returns {Promise<boolean>}       resolve(true) เมื่อกดยืนยัน, false เมื่อยกเลิก
   */
  function open(opt) {
    opt = opt || {};
    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'appdlg-overlay';
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-modal', 'true');

      const title  = opt.title  || 'Election Web';
      const okTxt  = opt.okText || (opt.danger ? 'ยืนยัน' : 'ตกลง');
      const cnTxt  = opt.cancelText || 'ยกเลิก';

      overlay.innerHTML = `
        <div class="appdlg">
          <div class="appdlg-head">
            <span class="appdlg-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" stroke-width="2.2"
                   stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
              </svg>
            </span>
            <span>${escapeHtml(title)}</span>
          </div>
          <div class="appdlg-body">
            <p class="appdlg-message">${escapeHtml(opt.message || '')}</p>
          </div>
          <div class="appdlg-foot">
            ${opt.alert ? '' : `<button type="button" class="appdlg-btn appdlg-btn-cancel" data-act="cancel">${escapeHtml(cnTxt)}</button>`}
            <button type="button" class="appdlg-btn appdlg-btn-ok ${opt.danger ? 'is-danger' : ''}" data-act="ok">${escapeHtml(okTxt)}</button>
          </div>
        </div>`;

      document.body.appendChild(overlay);
      requestAnimationFrame(() => overlay.classList.add('is-open'));

      const okBtn = overlay.querySelector('[data-act="ok"]');
      okBtn.focus();

      function close(result) {
        overlay.classList.remove('is-open');
        document.removeEventListener('keydown', onKey);
        setTimeout(() => { overlay.remove(); resolve(result); }, 160);
      }
      function onKey(e) {
        if (e.key === 'Escape' && !opt.alert) close(false);
        if (e.key === 'Enter') close(true);
      }

      overlay.addEventListener('click', (e) => {
        const act = e.target.closest('[data-act]')?.dataset.act;
        if (act === 'ok') close(true);
        else if (act === 'cancel') close(false);
        else if (e.target === overlay && !opt.alert) close(false); // คลิกพื้นหลัง = ยกเลิก
      });
      document.addEventListener('keydown', onKey);
    });
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  // ---- API สาธารณะ ----------------------------------------------------------
  window.appConfirm = (opt) =>
    open(typeof opt === 'string' ? { message: opt } : opt);

  window.appAlert = (opt) =>
    open(Object.assign({ alert: true },
      typeof opt === 'string' ? { message: opt } : opt));
})();
