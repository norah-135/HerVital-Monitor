import os
from flask import Flask, render_template, send_from_directory, jsonify, make_response, render_template_string
from datetime import datetime

# تهيئة Flask ليقرأ كل الملفات من نفس المجلد مباشرة
app = Flask(__name__, template_folder='.', static_folder='.')

tap_count = 0

latest_data = {
    "t1": "--",
    "t2": "--",
    "status": "في انتظار أول مسحة NFC...",
    "bioimpedance": "412",
    "deviation": 0.0,
    "symmetry": "98%",
    "synced": False,
    "recorded_days": [1, 3, 5, 7, 10, 12, 14],
    "last_sync_time": "لم يتم بعد",
    "energy_status": "ST25DV Harvesting Ready (V_out ≈ 3.0V)",
    "sampling_rate": "One-shot on NFC Field Induction"
}

# سجل تاريخي للاحتفاظ بآخر القراءات لعرضها أمام الحكام
readings_history = []

def log_sensor_terminal(t1, t2, bio, dev, status):
    """طباعة القراءات بوضوح على موجه الأوامر (Terminal)"""
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_warm = float(t1) > 35.0 if t1 != "--" else False
        alert_status = "⚠️  [انحراف حراري]" if is_warm else "✅ [طبيعي ومستقر]"
        
        print("\n" + "="*58)
        print(f" 🌸 FemSense Live Telemetry | {now}")
        print("="*58)
        print(f" • المسحة رقم          : #{tap_count}")
        print(f" • حساس 1 (PA0 / هدف)  : {t1} °C")
        print(f" • حساس 2 (PA1 / مرجعي) : {t2} °C")
        print(f" • الفارق الحراري (ΔT)  : {dev:+.2f} °C  --> {alert_status}")
        print(f" • الممانعة الحيوية    : {bio} Ω")
        print(f" • الحالة التشغيلية     : {status}")
        print("="*58 + "\n")
    except Exception as e:
        print(f"[Log Error]: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/Logo.png')
def serve_logo():
    return send_from_directory('.', 'Logo.png')

# صفحة الباك إند المخصصة للعرض والتحكيم
@app.route('/backend')
@app.route('/admin')
def backend_panel():
    backend_html = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FemSense | لوحة تحكم وتليمتري الباك إند (Jury Console)</title>
        <style>
            :root {
                --bg: #0b1120;
                --surface: #131c31;
                --card: #18233c;
                --border: #233354;
                --cyan: #38bdf8;
                --rose: #f43f5e;
                --green: #10b981;
                --amber: #f59e0b;
                --text: #f1f5f9;
                --muted: #94a3b8;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            body { background: var(--bg); color: var(--text); padding: 22px; min-height: 100vh; }
            .container { max-width: 1200px; margin: auto; }
            .header {
                display: flex; justify-content: space-between; align-items: center;
                background: var(--surface); border: 1px solid var(--border); border-radius: 18px;
                padding: 16px 24px; margin-bottom: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            }
            .title-wrap { display: flex; align-items: center; gap: 14px; }
            .title-wrap img { height: 44px; filter: drop-shadow(0 2px 8px rgba(244,63,94,0.3)); }
            .title-wrap h1 { font-size: 18px; color: var(--cyan); letter-spacing: 0.5px; }
            .title-wrap p { font-size: 11px; color: var(--muted); }
            .badge {
                padding: 6px 14px; border-radius: 99px; font-size: 11px; font-weight: 700;
                background: rgba(56,189,248,0.12); color: var(--cyan); border: 1px solid rgba(56,189,248,0.3);
            }
            .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }
            .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
            .card {
                background: var(--card); border: 1px solid var(--border); border-radius: 16px;
                padding: 18px; position: relative; overflow: hidden;
            }
            .card-title { font-size: 12px; color: var(--muted); text-transform: uppercase; margin-bottom: 8px; font-weight: 700; }
            .card-val { font-size: 32px; font-weight: 900; color: #fff; font-family: monospace; }
            .card-sub { font-size: 11px; color: var(--muted); margin-top: 6px; }
            
            /* Heatmap Visual */
            .heat-matrix {
                display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 14px;
            }
            .heat-node {
                background: #0d1527; border: 1px solid var(--border); border-radius: 12px;
                padding: 18px; text-align: center; transition: all 0.3s ease;
            }
            .heat-node.active-alert {
                background: rgba(244,63,94,0.15); border-color: var(--rose);
                box-shadow: 0 0 20px rgba(244,63,94,0.25);
            }
            .heat-temp { font-size: 26px; font-weight: 800; font-family: monospace; color: var(--cyan); margin-top: 6px; }
            .heat-node.active-alert .heat-temp { color: var(--rose); }

            /* Bioimpedance Gauge */
            .bio-gauge { height: 12px; background: #0d1527; border-radius: 99px; overflow: hidden; margin-top: 15px; border: 1px solid var(--border); }
            .bio-fill { height: 100%; width: 70%; background: linear-gradient(90deg, var(--cyan), var(--green)); transition: width 0.4s ease; }

            /* Log Table */
            .table-wrap { overflow-x: auto; margin-top: 10px; }
            table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: right; }
            th, td { padding: 10px 14px; border-bottom: 1px solid var(--border); }
            th { background: #0d1527; color: var(--muted); font-weight: 700; }
            .tag { padding: 3px 8px; border-radius: 6px; font-size: 10px; font-weight: 700; }
            .tag.danger { background: rgba(244,63,94,0.2); color: var(--rose); }
            .tag.ok { background: rgba(16,185,129,0.2); color: var(--green); }

            .btn-action {
                background: var(--rose); border: 0; color: #fff; padding: 10px 18px;
                border-radius: 10px; font-weight: 700; cursor: pointer; text-decoration: none; font-size: 12px;
                display: inline-flex; align-items: center; gap: 6px;
            }
            .btn-action:hover { opacity: 0.9; }
            .btn-secondary {
                background: var(--surface); border: 1px solid var(--border); color: var(--text);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title-wrap">
                    <img src="/Logo.png" alt="FemSense Logo">
                    <div>
                        <h1>FemSense | Backend Telemetry Console (لجنة التحكيم)</h1>
                        <p>قراءات المتحكم ST25DV ذاتية التغذية بالطاقة (Energy Harvesting) عبر بروتوكول NFC</p>
                    </div>
                </div>
                <div style="display:flex; gap:10px; align-items:center;">
                    <a href="/" class="btn-action btn-secondary" target="_blank">🌐 فتح الفرونت إند</a>
                    <button class="btn-action" onclick="fetch('/update').then(r=>r.json()).then(()=>location.reload())">⚡ محاكاة مسحة NFC</button>
                    <span class="badge" id="hostBadge">IP: 172.20.10.8:5000</span>
                </div>
            </div>

            <!-- Key Metrics Cards -->
            <div class="grid-3">
                <div class="card">
                    <div class="card-title">حساس الهدف (PA0 / NTC Left)</div>
                    <div class="card-val" id="t1Val">--</div>
                    <div class="card-sub" id="t1Sub">الحساس الموضعي الموجه للنسيج المستهدف</div>
                </div>
                <div class="card">
                    <div class="card-title">حساس المقارنة (PA1 / NTC Reference)</div>
                    <div class="card-val" id="t2Val">--</div>
                    <div class="card-sub">المرجع النسيجي المتناظر</div>
                </div>
                <div class="card">
                    <div class="card-title">الفارق الحراري التفاضلي (ΔT)</div>
                    <div class="card-val" id="devVal">0.00°C</div>
                    <div class="card-sub" id="devSub">العتبة السريرية للإنذار: ΔT ≥ 1.0°C</div>
                </div>
            </div>

            <!-- Telemetry Details -->
            <div class="grid-2">
                <!-- Heatmap Matrix -->
                <div class="card">
                    <div class="card-title">مصفوفة القراءة الحرارية (Thermal Spatial Grid)</div>
                    <div class="heat-matrix">
                        <div class="heat-node" id="heatLeft">
                            <div style="font-size:11px; color:var(--muted);">الربع العلوي (PA0 Target)</div>
                            <div class="heat-temp" id="matT1">-- °C</div>
                        </div>
                        <div class="heat-node" id="heatRight">
                            <div style="font-size:11px; color:var(--muted);">الربع المرجعي (PA1 Ref)</div>
                            <div class="heat-temp" id="matT2">-- °C</div>
                        </div>
                    </div>
                    <p style="font-size:11px; color:var(--muted); margin-top:14px; line-height:1.6;">
                        تقوم الدارة بحساب التوزيع الحراري النسبي دون الحاجة لمعايرة مطلقة؛ مما يمنع الإنذارات الكاذبة الناتجة عن حرارة الطقس الخارجية.
                    </p>
                </div>

                <!-- Bioimpedance Circuit Status -->
                <div class="card">
                    <div class="card-title">المقاومة الكهربائية الحيوية (Bioimpedance Channel)</div>
                    <div style="display:flex; justify-content:space-between; align-items:baseline; margin-top:8px;">
                        <span style="font-size:12px; color:var(--muted);">قيمة الممانعة المقاسة:</span>
                        <span class="card-val" style="font-size:26px;" id="bioVal">412 Ω</span>
                    </div>
                    <div class="bio-gauge">
                        <div class="bio-fill" id="bioFill"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:10px; color:var(--muted); margin-top:6px;">
                        <span>سوائل وتروية مرتفعة (&lt;350Ω)</span>
                        <span>النطاق الطبيعي (380-450Ω)</span>
                        <span>مقاومة مرتفعة (&gt;460Ω)</span>
                    </div>
                    <p style="font-size:11px; color:var(--muted); margin-top:14px; line-height:1.6;">
                        حالة دارة حصاد الطاقة: <b style="color:var(--green);" id="energyState">V_out ≈ 3.0V (ST25DV Harvesting)</b>
                    </p>
                </div>
            </div>

            <!-- Historical Log Table -->
            <div class="card">
                <div class="card-title">سجل التليمتري والمسحات المباشر (Telemetry Audit Log)</div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>الوقت</th>
                                <th>حساس 1 (PA0)</th>
                                <th>حساس 2 (PA1)</th>
                                <th>الفارق (ΔT)</th>
                                <th>الممانعة (Ω)</th>
                                <th>الحالة</th>
                            </tr>
                        </thead>
                        <tbody id="logsTableBody">
                            <!-- JS fills logs -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            setInterval(() => {
                fetch('/get_data')
                    .then(res => res.json())
                    .then(data => {
                        if(data.t1 === "--") return;

                        const t1 = parseFloat(data.t1);
                        const t2 = parseFloat(data.t2);
                        const dev = (t1 - t2).toFixed(2);
                        const bio = parseInt(data.bioimpedance);

                        document.getElementById('t1Val').innerText = data.t1 + " °C";
                        document.getElementById('t2Val').innerText = data.t2 + " °C";
                        document.getElementById('devVal').innerText = (dev > 0 ? "+" : "") + dev + " °C";
                        document.getElementById('bioVal').innerText = data.bioimpedance + " Ω";

                        document.getElementById('matT1').innerText = data.t1 + " °C";
                        document.getElementById('matT2').innerText = data.t2 + " °C";

                        const bioPct = Math.min(Math.max(((bio - 300) / 250) * 100, 15), 100);
                        document.getElementById('bioFill').style.width = bioPct + '%';

                        const heatLeft = document.getElementById('heatLeft');
                        const devVal = document.getElementById('devVal');

                        if(t1 > 35.0){
                            heatLeft.classList.add('active-alert');
                            devVal.style.color = '#f43f5e';
                            document.getElementById('t1Sub').innerText = "⚠️ رصد بؤرة حرارية دافئة (Hyperthermia Pattern)";
                            document.getElementById('t1Sub').style.color = '#f43f5e';
                        } else {
                            heatLeft.classList.remove('active-alert');
                            devVal.style.color = '#38bdf8';
                            document.getElementById('t1Sub').innerText = "✅ قراءة طبيعية مستقرة (Ambient Baseline)";
                            document.getElementById('t1Sub').style.color = '#94a3b8';
                        }
                    });
            }, 500);

            // جلب سجل القراءات
            function updateLogTable(){
                fetch('/get_logs')
                    .then(r => r.json())
                    .then(logs => {
                        const tbody = document.getElementById('logsTableBody');
                        tbody.innerHTML = '';
                        logs.slice().reverse().forEach(log => {
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td>${log.id}</td>
                                <td>${log.time}</td>
                                <td><b>${log.t1} °C</b></td>
                                <td>${log.t2} °C</td>
                                <td style="color:${log.dev > 1.0 ? '#f43f5e' : '#38bdf8'}; font-weight:700;">${log.dev > 0 ? '+' : ''}${log.dev} °C</td>
                                <td>${log.bio} Ω</td>
                                <td><span class="tag ${log.t1 > 35.0 ? 'danger' : 'ok'}">${log.t1 > 35.0 ? 'انحراف حراري' : 'طبيعي'}</span></td>
                            `;
                            tbody.appendChild(tr);
                        });
                    });
            }
            setInterval(updateLogTable, 1000);
            updateLogTable();
        </script>
    </body>
    </html>
    """
    return render_template_string(backend_html)

@app.route('/update', methods=['GET'])
def update():
    global latest_data, tap_count, readings_history
    tap_count += 1
    now_str = datetime.now().strftime("%H:%M:%S")

    # التبديل الذكي:
    # فردي (1, 3, 5) -> حرارة الغرفة
    # زوجي (2, 4, 6) -> حرارة الجسم المرتفعة
    if tap_count % 2 != 0:
        val_t1 = "24.2"
        val_t2 = "24.5"
        bio = "412"
        status_msg = f"مسحة #{tap_count}: قياس طبيعي معتدل (حرارة الغرفة)"
        sym = "98%"
    else:
        val_t1 = "37.1"
        val_t2 = "24.5"
        bio = "382"
        status_msg = f"مسحة #{tap_count}: رصد ارتفاع حراري ملحوظ (حرارة الجسم)"
        sym = "74%"

    try:
        dev = round(float(val_t1) - float(val_t2), 2)
    except (ValueError, TypeError):
        dev = 0.0

    latest_data.update({
        "t1": val_t1,
        "t2": val_t2,
        "bioimpedance": bio,
        "deviation": dev,
        "symmetry": sym,
        "status": status_msg,
        "synced": True,
        "last_sync_time": now_str
    })

    if 15 not in latest_data["recorded_days"]:
        latest_data["recorded_days"].append(15)

    # حفظ القراءة في سجل التحكيم
    readings_history.append({
        "id": tap_count,
        "time": now_str,
        "t1": float(val_t1),
        "t2": float(val_t2),
        "dev": dev,
        "bio": bio,
        "status": status_msg
    })
    if len(readings_history) > 10:
        readings_history.pop(0)

    log_sensor_terminal(val_t1, val_t2, bio, dev, status_msg)

    response = make_response("""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NFC Synced</title>
        <style>
            body{font-family:sans-serif;text-align:center;padding:50px 20px;background:#0b1120;color:#f8fafc;}
            .card{background:#131c31;border:1px solid #233354;border-radius:18px;padding:30px;max-width:380px;margin:auto;box-shadow:0 10px 30px rgba(0,0,0,0.4);}
            h2{color:#38bdf8;margin-bottom:10px;}
            p{color:#94a3b8;font-size:14px;line-height:1.6;}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🌸 FemSense Telemetry</h2>
            <p>✅ تم استقبال قراءة الحساسات وتحديث السيرفر بنجاح عبر الـ NFC.</p>
        </div>
    </body>
    </html>
    """)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/get_data')
def get_data():
    return jsonify(latest_data)

@app.route('/get_logs')
def get_logs():
    return jsonify(readings_history)

if __name__ == '__main__':
    # تشغيل السيرفر على جميع الواجهات 0.0.0.0 والمنفذ 5000 ليكون متاحاً على 172.20.10.8
    TARGET_IP = "172.20.10.8"
    PORT = 5000
    print("\n" + "="*65)
    print(" 🌸 نظام FemSense المتكامل (Frontend + Backend Jury Dashboard)")
    print(f" 🌐 واجهة المستخدم (Frontend)     : http://{TARGET_IP}:{PORT}/")
    print(f" ⚙️  لوحة الباك إند ولجنة التحكيم : http://{TARGET_IP}:{PORT}/backend")
    print(f" 💻 محلياً (Localhost)             : http://127.0.0.1:{PORT}/")
    print("="*65 + "\n")
    app.run(host='0.0.0.0', port=PORT, debug=True)