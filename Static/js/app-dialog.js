/* =========================================================================
 *  app-dialog.js  —  กล่องยืนยันสไตล์แอพ (แทน confirm()/alert() ของเบราว์เซอร์)
 *  ใช้คลาส CSS เดิมของโปรเจกต์: .confirm-overlay / .confirm-modal / .btn
 *
 *  วิธีใช้แบบที่ 1 (อัตโนมัติ) — ใส่ data-confirm บนฟอร์มหรือปุ่ม submit:
 *      <form ... data-confirm="ลบวาระนี้?" data-confirm-danger> ... </form>
 *      <button type="submit" data-confirm="ปิดวาระนี้?" data-confirm-danger>ปิด</button>
 *
 *  วิธีใช้แบบที่ 2 (เรียกเอง) — สำหรับข้อความแบบไดนามิก:
 *      const ok = await appConfirm({ title:'ยืนยัน', message:'...', danger:true });
 *      if (ok) { ... }
 *      await appAlert('รหัสผ่านไม่ตรงกัน');
 * ========================================================================= */
(function () {
  'use strict';

  // เติม CSS เล็กน้อยเฉพาะส่วนที่ธีมเดิมไม่มี (ไอคอนแบบ danger + ข้อความหลายบรรทัด)
  var sup = document.createElement('style');
  sup.textContent =
    '.confirm-modal-icon.is-danger{background:var(--red-bg);}' +
    '.confirm-modal-icon.is-danger svg{stroke:var(--red);}' +
    '.confirm-modal.appdlg{text-align:center;}' +
    '.confirm-modal.appdlg .confirm-modal-icon{margin-left:auto;margin-right:auto;}' +
    '.confirm-modal.appdlg h2{text-align:center;}' +
    '.confirm-modal p.appdlg-msg{white-space:pre-line;text-align:center;}';
  document.head.appendChild(sup);

  var ICON = {
    normal: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    danger: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'
  };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c];
    });
  }

  function open(opt) {
    opt = (typeof opt === 'string') ? { message: opt } : (opt || {});
    var danger = !!opt.danger;
    var isAlert = !!opt.alert;
    var title  = opt.title  || (danger ? 'ยืนยันการดำเนินการ' : 'ยืนยัน');
    var okTxt  = opt.okText || (danger ? 'ยืนยัน' : 'ตกลง');
    var cnTxt  = opt.cancelText || 'ยกเลิก';

    return new Promise(function (resolve) {
      var ov = document.createElement('div');
      ov.className = 'confirm-overlay';
      ov.setAttribute('role', 'dialog');
      ov.setAttribute('aria-modal', 'true');
      ov.innerHTML =
        '<div class="confirm-modal appdlg">' +
          '<div class="confirm-modal-icon ' + (danger ? 'is-danger' : '') + '">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
              (danger ? ICON.danger : ICON.normal) +
            '</svg>' +
          '</div>' +
          '<h2>' + esc(title) + '</h2>' +
          '<p class="appdlg-msg">' + esc(opt.message) + '</p>' +
          '<div class="btn-row">' +
            '<button type="button" class="btn ' + (danger ? 'btn-danger' : 'btn-primary') + '" data-act="ok">' + esc(okTxt) + '</button>' +
            (isAlert ? '' : '<button type="button" class="btn btn-ghost" data-act="cancel">' + esc(cnTxt) + '</button>') +
          '</div>' +
        '</div>';

      document.body.appendChild(ov);
      // เปิดด้วยคลาส .show ของธีมเดิม (display:none -> flex + animation modalIn)
      requestAnimationFrame(function () { ov.classList.add('show'); });
      var okBtn = ov.querySelector('[data-act="ok"]');
      okBtn.focus();

      function done(result) {
        document.removeEventListener('keydown', onKey);
        ov.classList.remove('show');
        ov.remove();
        resolve(result);
      }
      function onKey(e) {
        if (e.key === 'Escape' && !isAlert) done(false);
        else if (e.key === 'Enter') done(true);
      }
      ov.addEventListener('click', function (e) {
        var act = e.target.closest('[data-act]');
        if (act) { done(act.getAttribute('data-act') === 'ok'); return; }
        if (e.target === ov && !isAlert) done(false); // คลิกพื้นหลัง = ยกเลิก
      });
      document.addEventListener('keydown', onKey);
    });
  }

  // ── API สาธารณะ ──
  window.appConfirm = open;
  window.appAlert   = function (opt) {
    return open(Object.assign({ alert: true },
      typeof opt === 'string' ? { message: opt } : opt));
  };

  // ── Auto-wire: ฟอร์ม/ปุ่ม submit ที่มี data-confirm ──
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!(form instanceof HTMLFormElement)) return;

    // หาตัวที่ถือ data-confirm: ปุ่มที่กด (e.submitter) ก่อน แล้วค่อยถึงฟอร์ม
    var btn = e.submitter || form.querySelector('[data-confirm]');
    var src = (btn && btn.hasAttribute && btn.hasAttribute('data-confirm')) ? btn
            : (form.hasAttribute('data-confirm') ? form : null);
    if (!src) return;

    if (form.dataset.confirmed === '1') { delete form.dataset.confirmed; return; }

    e.preventDefault();
    appConfirm({
      message: src.getAttribute('data-confirm'),
      danger:  src.hasAttribute('data-confirm-danger'),
      title:   src.getAttribute('data-confirm-title') || undefined,
      okText:  src.getAttribute('data-confirm-ok') || undefined
    }).then(function (ok) {
      if (ok) { form.dataset.confirmed = '1'; form.submit(); }
    });
  }, true);
})();
