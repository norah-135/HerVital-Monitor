import os
import json
import urllib.request
from flask import Flask, jsonify, make_response, render_template_string

app = Flask(__name__)

INDEX_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FemSense | رصد المؤشرات الحيوية</title>
<style>
:root{
  --rose:#e05284;
  --rose-dark:#be3364;
  --rose-deep:#881337;
  --rose-soft:#fff0f5;
  --rose-surface:#fff8fb;
  --rose-border:#fed7e2;
  --ink:#2d1a24;
  --muted:#7c6571;
  --line:#f8d7e3;
  --surface:#ffffff;
  --bg:#fdf5f8;
  --green:#10b981;
  --green-soft:#ecfdf5;
  --amber:#f59e0b;
  --red:#f43f5e;
  --red-soft:#fff1f2;
  --shadow:0 14px 38px rgba(224,82,132,.08);
}
*{box-sizing:border-box;margin:0;padding:0}
body{
  min-height:100vh;
  background:radial-gradient(circle at 10% 0%,#fff 0 25%,transparent 50%),
             radial-gradient(circle at 90% 100%,#fde2ec 0 30%,transparent 60%),
             var(--bg);
  color:var(--ink);
  font-family:Tahoma,"Segoe UI",Arial,sans-serif;
  padding:24px 16px;
}
.app{
  width:min(1100px,100%);
  margin:auto;
  background:var(--surface);
  border:1px solid var(--rose-border);
  border-radius:24px;
  box-shadow:var(--shadow);
  overflow:hidden;
}
.topbar{
  padding:16px 32px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  border-bottom:1px solid var(--line);
  background:rgba(255,255,255,.96);
}
.brand{display:flex;align-items:center;gap:14px}
.brand-text h1{
  font-size:22px;
  font-weight:800;
  color:var(--rose-deep);
  letter-spacing:-0.3px;
}

.content{padding:28px}

.status-banner {
  border-radius: 16px;
  padding: 16px 20px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--green-soft);
  border: 1.5px solid #a7f3d0;
  transition: all .3s ease;
}
.status-banner-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.status-banner-icon {
  font-size: 26px;
  line-height: 1;
}
.status-banner-title {
  font-size: 15px;
  font-weight: 800;
  color: #065f46;
}
.status-banner-desc {
  font-size: 12px;
  color: #047857;
  margin-top: 3px;
}
.status-pill {
  padding: 6px 16px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 800;
  background: #10b981;
  color: #fff;
  white-space: nowrap;
}

.timeline-card{
  background:var(--rose-surface);
  border:1px solid var(--rose-border);
  border-radius:18px;
  padding:18px 22px;
  margin-bottom:24px;
}
.timeline-head{
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:14px;
  font-size:13px;
  font-weight:700;
  color:var(--rose-deep);
}
.mini-track{
  display:grid;
  grid-template-columns:repeat(auto-fit, minmax(32px, 1fr));
  gap:6px;
  overflow-x:auto;
  padding-bottom:4px;
}
.mini-day{
  height:42px;
  border:1px solid var(--rose-border);
  border-radius:10px;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  font-size:10px;
  color:var(--muted);
  background:#fff;
  transition:all .2s ease;
}
.mini-day.done{
  background:var(--rose-soft);
  border-color:#f9a8d4;
  color:var(--rose-dark);
  font-weight:700;
}
.mini-day.current{
  border-color:var(--rose);
  background:var(--rose);
  color:#fff;
  font-weight:800;
  box-shadow:0 3px 10px rgba(224,82,132,.3);
}

.recommendations-box{
  background:linear-gradient(145deg, #fff, #fff9fb);
  border:1px solid var(--rose-border);
  border-radius:18px;
  padding:20px;
  margin-bottom:24px;
}
.rec-title{
  font-size:14px;
  font-weight:800;
  margin-bottom:14px;
  display:flex;
  align-items:center;
  gap:8px;
  color:var(--rose-deep);
}
.rec-list{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.rec-item{
  background:#fff;
  border:1px solid var(--line);
  border-radius:14px;
  padding:14px;
  transition:box-shadow .2s;
}
.rec-item:hover{
  box-shadow:0 6px 18px rgba(224,82,132,.08);
}
.rec-item b{
  font-size:12px;
  display:block;
  margin-bottom:6px;
  color:var(--rose-dark);
}
.rec-item p{
  font-size:11px;
  color:var(--muted);
  line-height:1.6;
}

.report-paper{
  background:#fff;
  border:1.5px dashed #f4b6cb;
  border-radius:18px;
  padding:26px;
}
.report-head{
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
  border-bottom:1px solid var(--line);
  padding-bottom:16px;
  margin-bottom:16px;
}
.report-brand{display:flex;align-items:center;gap:12px}
.report-meta{font-size:11px;color:var(--muted);text-align:left;line-height:1.8}
.report-table{width:100%;border-collapse:collapse;margin:14px 0;font-size:11px}
.report-table th,.report-table td{border:1px solid var(--line);padding:10px 12px;text-align:right}
.report-table th{background:var(--rose-soft);color:var(--rose-deep);font-weight:700}
.report-summary{
  background:var(--rose-surface);
  border:1px solid var(--rose-border);
  border-radius:12px;
  padding:14px;
  font-size:11px;
  color:var(--rose-deep);
  line-height:1.75;
  margin-top:14px;
}

.btn{
  border:0;
  border-radius:12px;
  padding:11px 22px;
  background:linear-gradient(135deg, var(--rose), var(--rose-dark));
  color:#fff;
  font-weight:700;
  font-size:12px;
  cursor:pointer;
  transition:all .2s ease;
  box-shadow:0 4px 12px rgba(224,82,132,.25);
}
.btn:hover{
  transform:translateY(-1px);
  box-shadow:0 6px 16px rgba(224,82,132,.35);
}
.btn.outline{
  background:#fff;
  border:1px solid var(--rose-border);
  color:var(--rose-dark);
  box-shadow:none;
}
.btn.outline:hover{
  background:var(--rose-soft);
}

@media(max-width:800px){
  .rec-list{grid-template-columns:1fr}
  .report-head{flex-direction:column;gap:12px}
  .report-meta{text-align:right}
  .status-banner{flex-direction:column;align-items:flex-start;gap:12px;}
}
</style>
</head>
<body>

<div class="app">
  <header class="topbar">
    <div class="brand">
      <div class="brand-text">
        <h1>FemSense</h1>
      </div>
    </div>
  </header>

  <div class="content">

    <div class="status-banner" id="statusBanner">
      <div class="status-banner-left">
        <div class="status-banner-icon" id="bannerIcon">🌿</div>
        <div>
          <div class="status-banner-title" id="bannerTitle">المؤشرات مطمئنة</div>
          <div class="status-banner-desc" id="bannerDesc">البيانات الفسيولوجية والمؤشرات المقاسة تقع ضمن النطاق الطبيعي المستقر.</div>
        </div>
      </div>
      <div class="status-pill" id="bannerPill">مؤشرات مطمئنة</div>
    </div>

    <div class="timeline-card">
      <div class="timeline-head">
        <span>خط التتبع الزمني (متابعة 30 يوماً للفحص)</span>
      </div>
      <div class="mini-track" id="calendarTrack"></div>
    </div>

    <div class="recommendations-box">
      <div class="rec-title">💡 التوجيهات والقرارات السريرية الذكية (Clinical Decision Support)</div>
      <div class="rec-list">
        <div class="rec-item">
          <b>🎯 توقيت الفحص اليومي</b>
          <p>يُفضل تثبيت موعد القياس صباحاً بعد الاستيقاظ مباشرة لتفادي التأثيرات الناتجة عن المجهود البدني.</p>
        </div>
        <div class="rec-item" id="recAlertCard">
          <b id="recAlertTitle">📊 حالة التباين الفسيولوجي</b>
          <p id="recAlertText">الفروقات الحرارية والمؤشرات الحيوية ضمن الحدود الطبيعية المستقرة ولا تتطلب تدخلاً سريرياً.</p>
        </div>
        <div class="rec-item">
          <b>🩺 بروتوكول المتابعة الطبية</b>
          <p>عند تسجيل تباين حراري (&gt; 1.5°C) مستمر لمدة 3 أيام، يُنشئ النظام ملف إحالة إلكتروني مباشرة للطبيبة المختصة.</p>
        </div>
      </div>
    </div>

    <div class="report-paper">
      <div class="report-head">
        <div class="report-brand">
          <div>
            <h4 style="font-size:15px; color:var(--rose-deep); font-weight:800;">تقرير فحص الأنماط الحيوية الدوري</h4>
            <span style="font-size:11px; color:var(--muted);">FemSense Continuous Diagnostic</span>
          </div>
        </div>
        <div class="report-meta">
          <div>المريضة: فاطمة محمد</div>
          <div>معرف الجهاز: FS-NFC-ST25DV</div>
          <div>التاريخ: 2026-10-02</div>
        </div>
      </div>

      <table class="report-table">
        <thead>
          <tr>
            <th>المؤشر الفسيولوجي</th>
            <th>القراءة الحالية</th>
            <th>المدى المرجعي الطبيعي</th>
            <th>التقييم الفني</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>الحرارة الموضعية PA0 (يسار)</td>
            <td id="repT1">--</td>
            <td>24.0°C - 36.8°C</td>
            <td id="repStatus1">بانتظار الفحص</td>
          </tr>
          <tr>
            <td>الحرارة المرجعية PA1 (يمين)</td>
            <td id="repT2">--</td>
            <td>24.0°C - 36.8°C</td>
            <td id="repStatus2">معياري</td>
          </tr>
          <tr>
            <td>الممانعة الكهربائية الحيوية</td>
            <td id="repBio">--</td>
            <td>380 Ω - 450 Ω</td>
            <td id="repBioStatus">بانتظار الفحص</td>
          </tr>
          <tr>
            <td>التفاضل الحراري الثنائي (ΔT)</td>
            <td id="repDev">0.00°C</td>
            <td>&lt; 0.8°C</td>
            <td id="repDevStatus">متطابق</td>
          </tr>
        </tbody>
      </table>

      <div class="report-summary" id="reportSummaryBox">
        <b>ملخص التقرير السريري:</b> البيانات المسجلة عبر دارة الطاقة الذاتية متوافقة مع مؤشرات الاستقرار النسيجي. لا توجد نقاط بؤرية دافئة غير متناظرة.
      </div>

      <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:18px;">
        <button class="btn outline" onclick="window.print()">🖨 طباعة التقرير</button>
        <button class="btn" onclick="alert('تم حفظ وتصدير ملف التقرير الطبي بنجاح')">📄 تصدير بصيغة PDF</button>
      </div>
    </div>

  </div>
</div>

<script>
function renderCalendar(recordedDays) {
  const track = document.getElementById('calendarTrack');
  if(!track) return;
  track.innerHTML = '';
  for(let i = 1; i <= 30; i++){
    const isRecorded = recordedDays.includes(i);
    const isToday = (i === 15);
    const day = document.createElement('div');
    day.className = `mini-day ${isRecorded ? 'done' : ''} ${isToday && !isRecorded ? 'current' : ''}`;
    day.innerHTML = `<span>${i}</span><span>${isRecorded ? '✓' : (isToday ? '•' : '')}</span>`;
    track.appendChild(day);
  }
}
renderCalendar([1, 3, 5, 7, 10, 12, 14]);

// يستعلم من نفس السيرفر محلياً لتجاوز أي مشاكل CORS
setInterval(() => {
  fetch('/get_data?t=' + Date.now())
    .then(res => res.json())
    .then(data => {
      const banner = document.getElementById('statusBanner');
      const bannerIcon = document.getElementById('bannerIcon');
      const bannerTitle = document.getElementById('bannerTitle');
      const bannerDesc = document.getElementById('bannerDesc');
      const bannerPill = document.getElementById('bannerPill');

      const recTitle = document.getElementById('recAlertTitle');
      const recText = document.getElementById('recAlertText');
      const summaryBox = document.getElementById('reportSummaryBox');

      if (data.recorded_days) {
        renderCalendar(data.recorded_days);
      }

      if (data.t1 && data.t1 !== "--") {
        const t1 = parseFloat(data.t1);
        const t2 = parseFloat(data.t2);
        const dev = parseFloat((t1 - t2).toFixed(2));
        const devStr = (dev > 0 ? "+" : "") + dev.toFixed(2);

        document.getElementById('repT1').innerText = data.t1 + " °C";
        document.getElementById('repT2').innerText = data.t2 + " °C";
        document.getElementById('repBio').innerText = data.bioimpedance + " Ω";
        document.getElementById('repDev').innerText = devStr + " °C";

        // شرط المسحة رقم 2 (الحالة الحرجة الوحيدة)
        const isCritical = (t1 > 35.0 || dev >= 1.0 || data.clinical_verdict === "ينصح بإجراء فحص");

        if (isCritical) {
          banner.style.background = 'var(--red-soft)';
          banner.style.borderColor = '#fca5a5';
          bannerIcon.innerText = '⚠️';
          bannerTitle.innerText = 'يُنصح بإجراء فحص ومراجعة سريرية';
          bannerTitle.style.color = '#9f1239';
          bannerDesc.innerText = 'تم رصد تباين حراري غير متماثل (' + devStr + '°C)، يوصى بإجراء فحص طبي للتأكد.';
          bannerDesc.style.color = '#be123c';
          bannerPill.innerText = 'ينصح بإجراء فحص';
          bannerPill.style.background = 'var(--red)';

          recTitle.innerText = '⚠️ رصد تباين حراري غير متماثل';
          recTitle.style.color = 'var(--red)';
          recText.innerText = 'تم رصد فارق حراري بمقدار ' + devStr + '°C، يُنصح بإعادة الفحص ومتابعة المؤشرات بعد 4 ساعات.';

          document.getElementById('repStatus1').innerText = 'ارتفاع حراري دافئ';
          document.getElementById('repStatus1').style.color = 'var(--red)';
          document.getElementById('repBioStatus').innerText = 'مستقر (' + data.bioimpedance + ' Ω)';
          document.getElementById('repBioStatus').style.color = 'var(--ink)';
          document.getElementById('repDevStatus').innerText = 'انحراف ملحوظ (' + devStr + '°C)';
          document.getElementById('repDevStatus').style.color = 'var(--red)';

          summaryBox.innerHTML = '<b>تنبيه فسيولوجي:</b> المستشعر يسجل ارتفاعاً في الطاقة الحرارية مع فارق تفاضلي ملحوظ (' + devStr + '°C). نوصي باستشارة الطبيبة إذا استمر المؤشر.';
          summaryBox.style.background = 'var(--red-soft)';
          summaryBox.style.borderColor = '#fca5a5';
          summaryBox.style.color = '#9f1239';

        } else {
          banner.style.background = 'var(--green-soft)';
          banner.style.borderColor = '#a7f3d0';
          bannerIcon.innerText = '🌿';
          bannerTitle.innerText = 'المؤشرات مطمئنة';
          bannerTitle.style.color = '#065f46';
          bannerDesc.innerText = 'البيانات الفسيولوجية والمؤشرات المقاسة تقع ضمن النطاق الطبيعي المستقر.';
          bannerDesc.style.color = '#047857';
          bannerPill.innerText = 'مؤشرات مطمئنة';
          bannerPill.style.background = 'var(--green)';

          recTitle.innerText = '✅ توازن حراري وممانعة مستقرة';
          recTitle.style.color = 'var(--green)';
          recText.innerText = 'جميع المؤشرات المقاسة متطابقة مع النطاق الفسيولوجي المرجعي لدرجة حرارة الغرفة.';

          document.getElementById('repStatus1').innerText = 'معياري ومستقر';
          document.getElementById('repStatus1').style.color = 'var(--green)';
          document.getElementById('repBioStatus').innerText = 'مثالي (طبيعي)';
          document.getElementById('repBioStatus').style.color = 'var(--green)';
          document.getElementById('repDevStatus').innerText = 'طبيعي ومتماثل';
          document.getElementById('repDevStatus').style.color = 'var(--green)';

          summaryBox.innerHTML = '<b>ملخص التقرير السريري:</b> البيانات المسجلة متوافقة مع مؤشرات الاستقرار النسيجي. لا توجد نقاط بؤرية دافئة غير متناظرة.';
          summaryBox.style.background = 'var(--rose-surface)';
          summaryBox.style.borderColor = 'var(--rose-border)';
          summaryBox.style.color = 'var(--rose-deep)';
        }
      }
    })
    .catch(() => {});
}, 500);
</script>
</body>
</html>
"""

@app.route('/')
def home():
    res = make_response(render_template_string(INDEX_HTML))
    res.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return res

@app.route('/get_data')
def proxy_get_data():
    """يسحب البيانات من سيرفر الباك إند الخلفي (5000) لتجاوز حظر المتصفح CORS"""
    try:
        req = urllib.request.Request("http://127.0.0.1:5000/get_data", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=1.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                res = make_response(jsonify(data))
                res.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                return res
    except Exception:
        pass

    return jsonify({
        "t1": "--",
        "t2": "--",
        "bioimpedance": "500",
        "clinical_verdict": "المؤشرات مطمئنة",
        "recorded_days": [1, 3, 5, 7, 10, 12, 14]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)