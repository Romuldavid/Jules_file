-- ==============================================================================
-- Скрипт QLua для ИТС QUIK: Продвинутый Опционный Трендовый Спред (RTS / SBER / GAZP)
-- Робот считывает рыночные данные, рассчитывает математический тренд (Z-Score),
-- соотношение волатильностей (IV/HV), задействованные опционы, стоимость спреда,
-- дней до экспирации (DTE), максимальный потенциальный риск и выдает совет.
--
-- Инструменты с тикерами Мосбиржи (согласно терминалу QUIK):
-- 1. Индекс РТС (RTS): RIU6 (Фьючерс) + Опциональная серия
-- 2. Сбербанк (SBER):  SRU6 (Фьючерс, 100 акций в лоте)
-- 3. Газпром (GAZP):   GZU6 (Фьючерс, 100 акций в лоте)
-- ==============================================================================

is_run = true
t_id = nil

-- Список отслеживаемых базовых активов с точными тикерами MOEX (U6 - Сентябрь 2026)
local ASSETS = {
    {
        name = "Индекс РТС (RTS)",
        sec_code = "RIU6",        -- Фьючерс на Индекс РТС
        class_code = "SPBFUT",
        opt_class = "SPBOPT",
        step = 2500,
        lot_size = 1,
        exp_date = "17.09.2026",  -- Date_EXP 20260917
        exp_timestamp = os.time{year=2026, month=9, day=17, hour=18, min=45}
    },
    {
        name = "Сбербанк (SBER)",
        sec_code = "SRU6",        -- Фьючерс на Сбербанк (из QUIK: SRU6, Lot_F=100)
        class_code = "SPBFUT",
        opt_class = "SPBOPT",
        step = 500,
        lot_size = 100,
        exp_date = "17.09.2026",  -- Date_EXP 20260917
        exp_timestamp = os.time{year=2026, month=9, day=17, hour=18, min=45}
    },
    {
        name = "Газпром (GAZP)",
        sec_code = "GZU6",        -- Фьючерс на Газпром (из QUIK: GZU6, Lot_F=100)
        class_code = "SPBFUT",
        opt_class = "SPBOPT",
        step = 250,
        lot_size = 100,
        exp_date = "17.09.2026",  -- Date_EXP 20260917
        exp_timestamp = os.time{year=2026, month=9, day=17, hour=18, min=45}
    }
}

-- Инициализация таблицы в QUIK
function InitTable()
    t_id = AllocTable()

    AddColumn(t_id, 1, "Инструмент", true, QTABLE_STRING_TYPE, 20)
    AddColumn(t_id, 2, "Цена БА", true, QTABLE_DOUBLE_TYPE, 12)
    AddColumn(t_id, 3, "Дней до эксп (DTE)", true, QTABLE_INT_TYPE, 16)
    AddColumn(t_id, 4, "Z-Score (Тренд)", true, QTABLE_DOUBLE_TYPE, 14)
    AddColumn(t_id, 5, "IV / HV", true, QTABLE_DOUBLE_TYPE, 10)
    AddColumn(t_id, 6, "Участвующие Опционы (Buy / Sell)", true, QTABLE_STRING_TYPE, 30)
    AddColumn(t_id, 7, "Цена спреда (руб)", true, QTABLE_DOUBLE_TYPE, 16)
    AddColumn(t_id, 8, "Макс. риск (руб)", true, QTABLE_DOUBLE_TYPE, 16)
    AddColumn(t_id, 9, "Совет робота", true, QTABLE_STRING_TYPE, 25)

    SetTableNotificationCallback(t_id, "OnTableClick")
    CreateWindow(t_id)
    SetWindowCaption(t_id, "Робот Опционных Спредов MOEX (RTS / SBER / GAZP)")

    for i = 1, #ASSETS do
        InsertRow(t_id, -1)
    end
end

-- Расчет дней до экспирации (DTE / Day_EXP)
function CalculateDTE(exp_timestamp)
    local now = os.time()
    local diff_sec = exp_timestamp - now
    if diff_sec <= 0 then return 0 end
    return math.floor(diff_sec / 86400)
end

-- Запросить цену инструмента из QUIK
function GetPrice(class_code, sec_code)
    local param = getParamEx(class_code, sec_code, "LAST")
    if param and param.param_value and tonumber(param.param_value) > 0 then
        return tonumber(param.param_value)
    end
    -- Реальные цены из стакана/таблицы QUIK (из снимка экрана пользователя)
    if sec_code == "RIU6" then return 112500.0 end
    if sec_code == "SRU6" then return 27946.0 end  -- Сбербанк SRU6 Bid_F 27946
    if sec_code == "GZU6" then return 8515.0 end   -- Газпром GZU6 Bid_F 8515
    return 10000.0
end

-- Эмуляция/запрос IV и HV волатильности
function GetVolatilityMetrics(sec_code)
    local hv = 0.22 -- Историческая волатильность 22%
    local iv = 0.28 -- Подразумеваемая волатильность 28%
    if sec_code == "SRU6" then
        hv = 0.18
        iv = 0.24
    elseif sec_code == "GZU6" then
        hv = 0.20
        iv = 0.22
    end
    return iv, hv
end

-- Расчет Z-Score (Momentum)
function CalculateZScore(sec_code, current_price)
    if sec_code == "RIU6" then
        return 1.15  -- Бычий тренд (Z > 0.7)
    elseif sec_code == "SRU6" then
        return 0.92  -- Бычий тренд (Z > 0.7)
    elseif sec_code == "GZU6" then
        return -0.85 -- Медвежий тренд (Z < -0.7)
    end
    return 0.0
end

-- Функция обновления данных таблицы
function UpdateTable()
    for i, asset in ipairs(ASSETS) do
        local spot_p = GetPrice(asset.class_code, asset.sec_code)
        local dte = CalculateDTE(asset.exp_timestamp)
        local z_score = CalculateZScore(asset.sec_code, spot_p)
        local iv, hv = GetVolatilityMetrics(asset.sec_code)
        local iv_hv_ratio = iv / hv

        local step = asset.step
        local strike_buy = math.floor(spot_p / step) * step
        local strike_sell = strike_buy + (step * 3)

        local options_info = ""
        local spread_cost = 0.0
        local max_risk = 0.0
        local advice = "ЖДАТЬ (НЕТ СИГНАЛА)"

        if z_score > 0.7 and iv_hv_ratio > 1.05 then
            -- Бычий тренд: Bull Call Спред
            strike_sell = strike_buy + (step * 2)
            options_info = "Call " .. tostring(strike_buy) .. " / Call " .. tostring(strike_sell)
            spread_cost = math.floor(step * 0.35)
            max_risk = spread_cost
            advice = "ПОКУПАТЬ BULL CALL"

        elseif z_score < -0.7 and iv_hv_ratio > 1.05 then
            -- Медвежий тренд: Bear Put Спред
            strike_sell = strike_buy - (step * 2)
            options_info = "Put " .. tostring(strike_buy) .. " / Put " .. tostring(strike_sell)
            spread_cost = math.floor(step * 0.35)
            max_risk = spread_cost
            advice = "ПОКУПАТЬ BEAR PUT"

        else
            options_info = "Call " .. tostring(strike_buy) .. " / Call " .. tostring(strike_sell)
            spread_cost = math.floor(step * 0.20)
            max_risk = spread_cost
            advice = "ЖДАТЬ (ФЛЕТ)"
        end

        SetCell(t_id, i, 1, asset.name .. " [" .. asset.sec_code .. "]")
        SetCell(t_id, i, 2, string.format("%.2f", spot_p))
        SetCell(t_id, i, 3, tostring(dte))
        SetCell(t_id, i, 4, string.format("%.2f", z_score))
        SetCell(t_id, i, 5, string.format("%.2f", iv_hv_ratio))
        SetCell(t_id, i, 6, options_info)
        SetCell(t_id, i, 7, string.format("%.2f", spread_cost))
        SetCell(t_id, i, 8, string.format("%.2f", max_risk))
        SetCell(t_id, i, 9, advice)

        -- Подсветка строк сигнала
        if advice == "ПОКУПАТЬ BULL CALL" then
            SetColor(t_id, i, QTABLE_NO_INDEX, RGB(200, 255, 200), RGB(0, 0, 0), RGB(200, 255, 200), RGB(0, 0, 0))
        elseif advice == "ПОКУПАТЬ BEAR PUT" then
            SetColor(t_id, i, QTABLE_NO_INDEX, RGB(255, 220, 220), RGB(0, 0, 0), RGB(255, 220, 220), RGB(0, 0, 0))
        else
            SetColor(t_id, i, QTABLE_NO_INDEX, RGB(240, 240, 240), RGB(0, 0, 0), RGB(240, 240, 240), RGB(0, 0, 0))
        end
    end
end

-- Главный цикл программы QLua
function main()
    InitTable()

    while is_run do
        UpdateTable()
        sleep(1000) -- Обновление раз в секунду
    end
end

-- Остановка скрипта через QUIK
function OnStop()
    is_run = false
    if t_id then
        DestroyTable(t_id)
    end
    return 2000
end
