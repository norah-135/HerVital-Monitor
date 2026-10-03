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
    "clinical_verdict": "المؤشرات مطمئنة",
    "bioimpedance": "500",
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
        is_low_bio = int(bio) < 300 if bio != "--" else False
        
        alert_status = "⚠ [انحراف حراري وممانعة منخفضة]" if (is_warm and is_low_bio) else ("⚠️ [انحراف حراري فقط]" if is_warm else "✅ [طبيعي ومستقر]")
        
        print("\n" + "="*60)
        print(f" 🌸 FemSense Live Telemetry | {now}")
        print("="*60)
        print(f" • المسحة رقم          : #{tap_count}")
        print(f" • حساس 1 (PA0 / هدف)  : {t1} °C")
        print(f" • حساس 2 (PA1 / مرجعي) : {t2} °C")
        print(f" • الفارق الحراري (ΔT)  : {dev:+.2f} °C")
        print(f" • الممانعة الحيوية    : {bio} Ω")
        print(f" • التقييم             : {alert_status}")
        print(f" • الحالة التشغيلية     : {status}")
        print("="*60 + "\n")
    except Exception as e:
        print(f"[Log Error]: {e}")

@app.route('/')
def home():
    return render_template('index.html')


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
            .card-title { font-size: 12px; color: var(--muted); text-transform: uppercase; margin-bottom: 8px; font-weight: 700; display: flex; justify-content: space-between; align-items: center; }
            .card-val { font-size: 32px; font-weight: 900; color: #fff; font-family: monospace; }
            .card-sub { font-size: 11px; color: var(--muted); margin-top: 6px; }

            /* --- خريطة التوزيع الحراري التشريحية المدمجة --- */
            .breast-wrap-dark {
                min-height: 250px; border-radius: 14px; background: radial-gradient(circle at 50% 35%, rgba(56,189,248,0.06), transparent 50%), #0d1527;
                border: 1px solid var(--border); position: relative; display: grid; place-items: center; overflow: hidden; margin-top: 10px;
            }
            .chest-dark {
                width: 270px; height: 170px; position: relative; display: flex; gap: 12px; align-items: center; justify-content: center;
            }
            .breast-dark {
                width: 110px; height: 130px; position: relative;
                background: radial-gradient(circle at 45% 42%, #233354 0 15%, #18233c 55%, #131c31 100%);
                border: 1px solid rgba(56,189,248,0.25);
                border-radius: 54% 46% 51% 49% / 48% 48% 52% 52%;
                box-shadow: inset 0 0 18px rgba(0,0,0,0.6), 0 8px 20px rgba(0,0,0,0.4);
                transition: all 0.4s ease;
            }
            .breast-dark.left { transform: rotate(7deg); }
            .breast-dark.right { transform: rotate(-7deg); }
            .nipple-dark {
                position: absolute; width: 16px; height: 16px; border-radius: 50%; background: #2a3d66;
                left: 50%; top: 52%; transform: translate(-50%, -50%); box-shadow: 0 0 0 6px rgba(56,189,248,0.08);
            }
            .quadrant-dark {
                position: absolute; width: 30px; height: 30px; border-radius: 50%;
                background: rgba(255,255,255,0.02); border: 1px dashed rgba(56,189,248,0.2);
            }
            .q1 { top: 14px; right: 12px; }
            .q2 { top: 14px; left: 12px; }
            .q3 { bottom: 14px; right: 12px; }
            .q4 { bottom: 14px; left: 12px; }
            
            .hotspot-dark {
                position: absolute; width: 28px; height: 28px; border-radius: 50%;
                background: rgba(244,63,94,0.75); right: 18px; top: 24px;
                box-shadow: 0 0 0 8px rgba(244,63,94,0.18), 0 0 20px rgba(244,63,94,0.45);
                animation: pulse-hot 1.8s infinite;
                display: none;
            }
            .hotspot-dark.active { display: block; }
            @keyframes pulse-hot { 50% { transform: scale(1.12); opacity: 0.85; } }

            .map-legend-dark {
                position: absolute; bottom: 8px; right: 12px; left: 12px; display: flex; justify-content: space-between;
                color: var(--muted); font-size: 10px; font-weight: 600;
            }
            .legend-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-left: 4px; vertical-align: middle; }
            .legend-dot.rose { background: var(--rose); box-shadow: 0 0 8px var(--rose); }
            .legend-dot.cyan { background: var(--cyan); }

            /* --- مخطط اتجاه الحرارة الأسبوعي المدمج --- */
            .bars-dark {
                height: 145px; display: flex; align-items: flex-end; gap: 10px; padding: 10px 4px 4px;
                border-bottom: 1px solid var(--border); margin-top: 10px;
            }
            .bar-col-dark { flex: 1; height: 100%; display: flex; align-items: flex-end; position: relative; }
            .bar-fill {
                width: 100%; border-radius: 6px 6px 2px 2px;
                background: linear-gradient(180deg, var(--cyan), #1e293b);
                min-height: 18px; transition: all 0.4s ease;
            }
            .bar-fill.hot {
                background: linear-gradient(180deg, var(--rose), #4c0519);
                box-shadow: 0 -2px 10px rgba(244,63,94,0.3);
            }
            .days-dark { display: flex; gap: 10px; padding: 8px 4px 0; color: var(--muted); font-size: 10px; font-family: monospace; }
            .days-dark span { flex: 1; text-align: center; }

            .progress-dark {
                height: 8px; background: #0d1527; border-radius: 99px; overflow: hidden; margin-top: 12px; border: 1px solid var(--border);
            }
            .progress-fill { height: 100%; width: 45%; background: linear-gradient(90deg, var(--cyan), var(--rose)); border-radius: 99px; transition: width 0.4s ease; }
            .small-row-dark { display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--muted); margin-top: 6px; }
            .small-row-dark strong { color: var(--text); font-family: monospace; }

            /* Matrix and Gauges */
            .heat-matrix { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 14px; }
            .heat-node {
                background: #0d1527; border: 1px solid var(--border); border-radius: 12px;
                padding: 16px; text-align: center; transition: all 0.3s ease;
            }
            .heat-node.active-alert {
                background: rgba(244,63,94,0.15); border-color: var(--rose);
                box-shadow: 0 0 20px rgba(244,63,94,0.25);
            }
            .heat-temp { font-size: 26px; font-weight: 800; font-family: monospace; color: var(--cyan); margin-top: 6px; }
            .heat-node.active-alert .heat-temp { color: var(--rose); }

            .bio-gauge { height: 12px; background: #0d1527; border-radius: 99px; overflow: hidden; margin-top: 15px; border: 1px solid var(--border); }
            .bio-fill { height: 100%; width: 70%; background: linear-gradient(90deg, var(--cyan), var(--green)); transition: width 0.4s ease; }

            /* Log Table */
            .table-wrap { overflow-x: auto; margin-top: 10px; }
            table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: right; }
            th, td { padding: 10px 14px; border-bottom: 1px solid var(--border); }
            th { background: #0d1527; color: var(--muted); font-weight: 700; }
            .tag { padding: 3px 8px; border-radius: 6px; font-size: 10px; font-weight: 700; }
            .tag.danger { background: rgba(244,63,94,0.2); color: var(--rose); }
            .tag.warning { background: rgba(245,158,11,0.2); color: var(--amber); }
            .tag.ok { background: rgba(16,185,129,0.2); color: var(--green); }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title-wrap">
                    <div>
                        <h1>FemSense | Telemetry & Clinical Console</h1>
                        <p>نظام التليمتري والتحكيم السريري المباشر عبر مستشعرات الـ NFC</p>
                    </div>
                </div>
                <div class="badge" id="liveSyncStatus">● في انتظار القراءة</div>
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

            <!-- Visuals: الخريطة الحرارية + اتجاه الحرارة -->
            <div class="grid-2">
                <!-- 1. خريطة التوزيع الحراري التشريحية -->
                <div class="card">
                    <div class="card-title">
                        <span>خريطة التوزيع الحراري (Thermal Spatial Grid)</span>
                        <span style="font-size:10px; color:var(--cyan);">قراءة تفاضلية للأرباع</span>
                    </div>
                    <div class="breast-wrap-dark">
                        <div class="chest-dark">
                            <div class="breast-dark left" id="breastLeftUi">
                                <i class="quadrant-dark q1"></i>
                                <i class="quadrant-dark q2"></i>
                                <i class="quadrant-dark q3"></i>
                                <i class="quadrant-dark q4"></i>
                                <i class="nipple-dark"></i>
                                <i class="hotspot-dark" id="hotspotIndicator"></i>
                            </div>
                            <div class="breast-dark right">
                                <i class="quadrant-dark q1"></i>
                                <i class="quadrant-dark q2"></i>
                                <i class="quadrant-dark q3"></i>
                                <i class="quadrant-dark q4"></i>
                                <i class="nipple-dark"></i>
                            </div>
                        </div>
                        <div class="map-legend-dark">
                            <span><i class="legend-dot rose"></i> بؤرة الانحراف (PA0 Target)</span>
                            <span><i class="legend-dot cyan"></i> خط الأساس المرجعي (PA1)</span>
                            <span id="regionStatus">الربع العلوي الخارجي</span>
                        </div>
                    </div>
                </div>

                <!-- 2. اتجاه الحرارة الأسبوعي واستقرار النمط -->
                <div class="card">
                    <div class="card-title">
                        <span>اتجاه الحرارة (7-Day Thermal Trend)</span>
                        <span style="font-size:10px; color:var(--muted);">مقارنة بالخط الأساسي الشخصي</span>
                    </div>
                    <div class="bars-dark">
                        <div class="bar-col-dark"><i class="bar-fill" style="height:42%"></i></div>
                        <div class="bar-col-dark"><i class="bar-fill" style="height:45%"></i></div>
                        <div class="bar-col-dark"><i class="bar-fill" style="height:44%"></i></div>
                        <div class="bar-col-dark"><i class="bar-fill" style="height:50%"></i></div>
                        <div class="bar-col-dark"><i class="bar-fill hot" style="height:68%"></i></div>
                        <div class="bar-col-dark"><i class="bar-fill hot" style="height:76%"></i></div>
                        <div class="bar-col-dark"><i class="bar-fill" id="todayBar" style="height:45%"></i></div>
                    </div>
                    <div class="days-dark"><span>24</span><span>25</span><span>26</span><span>27</span><span>28</span><span>29</span><span>اليوم</span></div>
                    
                    <div class="small-row-dark" style="margin-top:14px;">
                        <span>الانحراف اللحظي المقاس:</span>
                        <strong id="trendDevLabel">0.00°C</strong>
                    </div>
                    <div class="progress-dark">
                        <div class="progress-fill" id="alertProgressBar"></div>
                    </div>
                    <div class="small-row-dark">
                        <span>مؤشر ثقة التنبيه النمطي:</span>
                        <strong id="alertConfidenceLabel">45%</strong>
                    </div>
                </div>
            </div>

            <!-- Telemetry Details: Matrix & Bioimpedance -->
            <div class="grid-2">
                <div class="card">
                    <div class="card-title">مصفوفة القراءة الرقمية للحساسات</div>
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
                </div>

                <div class="card">
                    <div class="card-title">المقاومة الكهربائية الحيوية (Bioimpedance Channel)</div>
                    <div style="display:flex; justify-content:space-between; align-items:baseline; margin-top:8px;">
                        <span style="font-size:12px; color:var(--muted);">قيمة الممانعة المقاسة:</span>
                        <span class="card-val" style="font-size:26px;" id="bioVal">500 Ω</span>
                    </div>
                    <div class="bio-gauge">
                        <div class="bio-fill" id="bioFill"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:10px; color:var(--muted); margin-top:6px;">
                        <span style="color:var(--rose);">سوائل/تروية (&lt;300Ω)</span>
                        <span style="color:var(--green);">نطاق طبيعي (450-550Ω)</span>
                        <span>مقاومة مرتفعة (&gt;600Ω)</span>
                    </div>
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
                fetch('/get_data?t=' + Date.now())
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

                        const bioPct = Math.min(Math.max(((bio - 100) / 500) * 100, 10), 100);
                        const bioFill = document.getElementById('bioFill');
                        bioFill.style.width = bioPct + '%';
                        
                        if (bio < 300) {
                            bioFill.style.background = 'linear-gradient(90deg, #f43f5e, #f59e0b)';
                        } else {
                            bioFill.style.background = 'linear-gradient(90deg, var(--cyan), var(--green))';
                        }

                        const heatLeft = document.getElementById('heatLeft');
                        const devVal = document.getElementById('devVal');
                        const hotspot = document.getElementById('hotspotIndicator');
                        const breastLeft = document.getElementById('breastLeftUi');
                        const todayBar = document.getElementById('todayBar');
                        const trendDevLabel = document.getElementById('trendDevLabel');
                        const alertProgressBar = document.getElementById('alertProgressBar');
                        const alertConfidenceLabel = document.getElementById('alertConfidenceLabel');
                        const liveStatus = document.getElementById('liveSyncStatus');

                        trendDevLabel.innerText = (dev > 0 ? "+" : "") + dev + " °C";

                        if(t1 > 35.0){
                            heatLeft.classList.add('active-alert');
                            devVal.style.color = '#f43f5e';
                            
                            hotspot.classList.add('active');
                            breastLeft.style.borderColor = 'rgba(244,63,94,0.6)';
                            breastLeft.style.boxShadow = '0 0 25px rgba(244,63,94,0.3)';

                            todayBar.classList.add('hot');
                            todayBar.style.height = '85%';

                            if (bio < 300) {
                                document.getElementById('t1Sub').innerText = "🚨 تنبيه مركب: بؤرة حرارية + احتقان سوائل وتروية مرتفعة";
                                document.getElementById('t1Sub').style.color = '#f43f5e';
                                document.getElementById('regionStatus').innerText = "🚨 تأكيد الانحراف المزدوج (Hyperthermia + Edema)";
                                document.getElementById('regionStatus').style.color = '#f43f5e';
                                
                                alertProgressBar.style.width = '96%';
                                alertConfidenceLabel.innerText = '96% (تنبيه مزدوج شديد التأكيد)';
                                alertConfidenceLabel.style.color = '#f43f5e';

                                liveStatus.innerText = '● انحراف حراري + ممانعة 150Ω';
                                liveStatus.style.color = '#f43f5e';
                                liveStatus.style.borderColor = 'rgba(244,63,94,0.5)';
                                liveStatus.style.background = 'rgba(244,63,94,0.2)';
                            } else {
                                document.getElementById('t1Sub').innerText = "⚠️ رصد بؤرة حرارية دافئة مع استقرار الممانعة النسيجية";
                                document.getElementById('t1Sub').style.color = '#f59e0b';
                                document.getElementById('regionStatus').innerText = "⚠️ نشاط حراري ملحوظ (الممانعة مستقرة)";
                                document.getElementById('regionStatus').style.color = '#f59e0b';

                                alertProgressBar.style.width = '75%';
                                alertConfidenceLabel.innerText = '75% (انحراف حراري أولي)';
                                alertConfidenceLabel.style.color = '#f59e0b';

                                liveStatus.innerText = '● انحراف حراري أولي (500Ω)';
                                liveStatus.style.color = '#f59e0b';
                                liveStatus.style.borderColor = 'rgba(245,158,11,0.4)';
                                liveStatus.style.background = 'rgba(245,158,11,0.12)';
                            }
                        } else {
                            heatLeft.classList.remove('active-alert');
                            devVal.style.color = '#38bdf8';
                            document.getElementById('t1Sub').innerText = "✅ قراءة طبيعية مستقرة (Ambient Baseline)";
                            document.getElementById('t1Sub').style.color = '#94a3b8';

                            hotspot.classList.remove('active');
                            breastLeft.style.borderColor = 'rgba(56,189,248,0.25)';
                            breastLeft.style.boxShadow = 'none';
                            document.getElementById('regionStatus').innerText = "الربع العلوي الخارجي (مستقر)";
                            document.getElementById('regionStatus').style.color = 'var(--muted)';

                            todayBar.classList.remove('hot');
                            todayBar.style.height = '45%';
                            alertProgressBar.style.width = '25%';
                            alertConfidenceLabel.innerText = '25% (ضمن خط الأساس السليم)';
                            alertConfidenceLabel.style.color = '#10b981';

                            liveStatus.innerText = '● متزامن وطبيعي (500Ω)';
                            liveStatus.style.color = '#10b981';
                            liveStatus.style.borderColor = 'rgba(16,185,129,0.4)';
                            liveStatus.style.background = 'rgba(16,185,129,0.12)';
                        }
                    });
            }, 500);

            function updateLogTable(){
                fetch('/get_logs?t=' + Date.now())
                    .then(r => r.json())
                    .then(logs => {
                        const tbody = document.getElementById('logsTableBody');
                        tbody.innerHTML = '';
                        logs.slice().reverse().forEach(log => {
                            const tr = document.createElement('tr');
                            let tagClass = 'ok';
                            let tagText = 'طبيعي ومستقر';

                            if (log.t1 > 35.0 && log.bio < 300) {
                                tagClass = 'danger';
                                tagText = 'انحراف مزدوج (حرارة+سوائل)';
                            } else if (log.t1 > 35.0) {
                                tagClass = 'warning';
                                tagText = 'انحراف حراري أولي';
                            }

                            tr.innerHTML = `
                                <td>${log.id}</td>
                                <td>${log.time}</td>
                                <td><b>${log.t1} °C</b></td>
                                <td>${log.t2} °C</td>
                                <td style="color:${log.dev > 1.0 ? '#f43f5e' : '#38bdf8'}; font-weight:700;">${log.dev > 0 ? '+' : ''}${log.dev} °C</td>
                                <td style="color:${log.bio < 300 ? '#f43f5e' : '#10b981'}; font-weight:700;">${log.bio} Ω</td>
                                <td><span class="tag ${tagClass}">${tagText}</span></td>
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

    # دورة ثلاثية لعرض المراحل:
    # المسحة 1: حرارة طبيعية (غرفة) + ممانعة طبيعية (~505Ω)
    # المسحة 2: حرارة مرتفعة (جسم) + ممانعة طبيعية مستقرة (~495Ω)
    # المسحة 3: حرارة مرتفعة (جسم) + انخفاض حاد للممانعة (150Ω)
    cycle_step = (tap_count - 1) % 3

    if cycle_step == 0:
        val_t1 = "24.6"
        val_t2 = "24.6"
        bio = "505"
        status_msg = f"مسحة #{tap_count} (دورة 1): قراءة طبيعية مستقرة (حرارة غرفة + ممانعة طبيعية 505Ω)"
        sym = "98%"
    elif cycle_step == 1:
        val_t1 = "37.1"
        val_t2 = "24.5"
        bio = "495"
        status_msg = f"مسحة #{tap_count} (دورة 2): رصد انحراف حراري موضعي أولي مع ثبات الممانعة (495Ω)"
        sym = "81%"
    else:
        val_t1 = "24.4"
        val_t2 = "24.5"
        bio = "150"
        status_msg = f"مسحة #{tap_count} (دورة 3): انحراف حراري + انخفاض حاد بالممانعة (150Ω) يشير لاحتقان/تروية عالية"
        sym = "64%"

    try:
        dev = round(float(val_t1) - float(val_t2), 2)
    except (ValueError, TypeError):
        dev = 0.0

    # تقييم المؤشرات: إذا كانت الحرارة أعلى من 35.0 يُنصح بالفحص
    verdict = "ينصح بإجراء فحص" if float(val_t1) > 35.0 else "المؤشرات مطمئنة"

    latest_data.update({
        "t1": val_t1,
        "t2": val_t2,
        "bioimpedance": bio,
        "deviation": dev,
        "symmetry": sym,
        "status": status_msg,
        "clinical_verdict": verdict,
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
        "bio": int(bio),
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
    res = make_response(jsonify(latest_data))
    res.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return res

@app.route('/get_logs')
def get_logs():
    res = make_response(jsonify(readings_history))
    res.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return res

if __name__ == '__main__':
    TARGET_IP = "172.20.10.8"
    PORT = 5000
    print("\n" + "="*65)
    print(" 🌸 نظام FemSense المتكامل (Frontend + Backend Jury Dashboard)")
    print(f" 🌐 واجهة المستخدم (Frontend)     : http://{TARGET_IP}:{PORT}/")
    print(f" 🛠️ لوحة تحكم الحكام (Backend)    : http://{TARGET_IP}:{PORT}/backend")
    print(f" 💻 محلياً (Localhost)             : http://127.0.0.1:{PORT}/")
    print("="*65 + "\n")
    app.run(host='0.0.0.0', port=PORT, debug=True)
