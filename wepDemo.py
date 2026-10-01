from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# عداد تتبع اللمسات
tap_count = 0

latest_data = {
    "t1": "--",
    "t2": "--",
    "status": "في انتظار أول مسحة NFC..."
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Battery-less NFC Monitoring</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: radial-gradient(circle at top, #1e293b, #0f172a);
            color: #f8fafc;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }
        h1 {
            font-size: 2.2rem;
            margin-bottom: 5px;
            color: #38bdf8;
        }
        .subtitle {
            color: #94a3b8;
            margin-bottom: 35px;
            font-size: 1.1rem;
        }
        .dashboard {
            display: flex;
            gap: 25px;
            width: 100%;
            max-width: 650px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .card {
            background: #1e293b;
            border: 2px solid #334155;
            border-radius: 20px;
            padding: 30px;
            flex: 1;
            min-width: 220px;
            text-align: center;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
            transition: all 0.3s ease;
        }
        .card-header {
            font-size: 1.2rem;
            color: #cbd5e1;
            margin-bottom: 15px;
        }
        .temp-display {
            font-size: 4rem;
            font-weight: 800;
            line-height: 1;
            color: #38bdf8;
            transition: color 0.3s ease;
        }
        .unit {
            font-size: 1.6rem;
            color: #64748b;
            font-weight: 400;
        }
        .status-box {
            margin-top: 35px;
            padding: 14px 35px;
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid #475569;
            border-radius: 50px;
            color: #38bdf8;
            font-size: 1rem;
        }
        .warm-alert {
            color: #f87171 !important;
            border-color: #ef4444 !important;
        }
    </style>
</head>
<body>

    <h1>مراقبة درجات الحرارة الحية</h1>
    <div class="subtitle">نظام قراءة لاسلكي ذاتي الطاقة (Energy Harvesting)</div>

    <div class="dashboard">
        <div class="card" id="card1">
            <div class="card-header">حساس 1 (PA0)</div>
            <div>
                <span class="temp-display" id="t1">--</span>
                <span class="unit">°C</span>
            </div>
        </div>

        <div class="card" id="card2">
            <div class="card-header">حساس 2 (PA1)</div>
            <div>
                <span class="temp-display" id="t2">--</span>
                <span class="unit">°C</span>
            </div>
        </div>
    </div>

    <div class="status-box" id="status">في انتظار أول مسحة...</div>

    <script>
        setInterval(() => {
            fetch('/get_data')
                .then(res => res.json())
                .then(data => {
                    const t1Elem = document.getElementById('t1');
                    const card1Elem = document.getElementById('card1');
                    
                    t1Elem.innerText = data.t1;
                    document.getElementById('t2').innerText = data.t2;
                    document.getElementById('status').innerText = data.status;

                    // تحويل لون الحساس الأول إلى الأحمر الدافئ إذا ارتفعت الحرارة فوق 35
                    if (parseFloat(data.t1) > 35.0) {
                        t1Elem.style.color = '#f87171';
                        card1Elem.style.borderColor = '#ef4444';
                    } else {
                        t1Elem.style.color = '#38bdf8';
                        card1Elem.style.borderColor = '#334155';
                    }
                });
        }, 300);
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/update', methods=['GET'])
def update():
    global latest_data, tap_count
    tap_count += 1

    # التبديل التلقائي الذكي:
    # المسحة الفردية (1, 3, 5...) -> حرارة الغرفة
    # المسحة الزوجية (2, 4, 6...) -> حرارة الجسم المرتفعة
    if tap_count % 2 != 0:
        val_t1 = "24.2"
        val_t2 = "24.5"
        latest_data["status"] = f"مسحة رقم {tap_count}: قياس حرارة الغرفة الطبيعية"
    else:
        val_t1 = "37.1"
        val_t2 = "24.5"
        latest_data["status"] = f"مسحة رقم {tap_count}: رصد ارتفاع الحرارة (حرارة الجسم)"

    latest_data["t1"] = val_t1
    latest_data["t2"] = val_t2

    print(f"\n[NFC Tap #{tap_count}] تم تحديث اللوحة بنجاح -> T1={val_t1}°C | T2={val_t2}°C")

    response = app.make_response("""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style='font-family:sans-serif; text-align:center; padding-top:50px; background:#0f172a; color:#f8fafc;'>
        <h2 style='color:#38bdf8;'>✅ تم تسجيل درجات الحرارة!</h2>
        <p style='color:#94a3b8;'>تم نقل البيانات وتحديث الشاشة بنجاح.</p>
    </body>
    </html>
    """)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/get_data')
def get_data():
    return jsonify(latest_data)

if __name__ == '__main__':
    print("\n" + "="*50)
    print(" افتحي صفحة العرض على اللابتوب: http://localhost:5000")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=False)