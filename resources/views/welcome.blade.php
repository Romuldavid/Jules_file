<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mufta40.ru - Laravel 11</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 40px;
            max-width: 600px;
            width: 100%;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            text-align: center;
        }
        .badge {
            display: inline-block;
            background: #ff2d20;
            color: white;
            font-size: 14px;
            font-weight: 600;
            padding: 6px 16px;
            border-radius: 20px;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        h1 {
            font-size: 24px;
            font-weight: 700;
            line-height: 1.4;
            margin-bottom: 24px;
            color: #ffffff;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-top: 24px;
            text-align: left;
        }
        .info-item {
            background: rgba(15, 23, 42, 0.6);
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .info-label {
            font-size: 12px;
            color: #94a3b8;
            margin-bottom: 4px;
        }
        .info-value {
            font-size: 14px;
            font-weight: 600;
            color: #38bdf8;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">Laravel 11</div>
        <h1>{{ $message }}</h1>

        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">Домен</div>
                <div class="info-value">mufta40.ru</div>
            </div>
            <div class="info-item">
                <div class="info-label">PHP Версия</div>
                <div class="info-value">{{ PHP_VERSION }}</div>
            </div>
            <div class="info-item">
                <div class="info-label">СУБД</div>
                <div class="info-value">MySQL 5.7.44</div>
            </div>
            <div class="info-item">
                <div class="info-label">Хостинг</div>
                <div class="info-value">REG.RU / OpenServer</div>
            </div>
        </div>
    </div>
</body>
</html>
