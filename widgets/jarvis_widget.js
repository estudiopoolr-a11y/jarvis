// JARVIS Widget para Scriptable
// Muestra cuentas (disponible), Presupuesto vs Gastos por categoría y Préstamos
// Usa /api/widget/dashboard (UNA sola llamada HTTP)

const BASE_URL = "https://jarvis-h20g.onrender.com"
const USUARIO = "1536228767180136498"

// Colores tema oscuro
const COLORS = {
    bg: "#0f0f23",
    card: "#1a1a2e",
    card_loan: "#3d2818",
    text: "#ffffff",
    text_dim: "#a0a0b8",
    subtitle: "#8b8b9e",
    income: "#10b981",
    expense: "#ef4444",
    accent: "#6366f1",
    progress: "#3b82f6",
    warning: "#f59e0b",
    danger: "#ef4444",
    loan: "#fbbf24",
    success: "#10b981",
    border: "#2a2a3e"
}

async function fetchJSON(url) {
    try {
        const req = new Request(url)
        req.timeoutInterval = 10
        return await req.loadJSON()
    } catch (e) {
        console.error("Error fetching: " + url + " - " + e)
        return null
    }
}

function formatMoney(amount) {
    const num = Number(amount) || 0
    const abs = Math.abs(num)
    let formatted
    if (abs >= 1000000) {
        formatted = "$" + (abs / 1000000).toFixed(1) + "M"
    } else if (abs >= 100000) {
        formatted = "$" + (abs / 1000).toFixed(0) + "K"
    } else {
        formatted = "$" + abs.toLocaleString('es-CO')
    }
    return num < 0 ? "-" + formatted : formatted
}

async function buildWidget() {
    const w = new ListWidget()
    w.backgroundColor = new Color(COLORS.bg)
    w.setPadding(10, 10, 10, 10)

    const widgetFamily = config.widgetFamily || "medium"

    const url = BASE_URL + "/api/widget/dashboard?usuario_id=" + USUARIO
    const data = await fetchJSON(url)

    if (!data || data.error) {
        const errMsg = w.addText("⚠️ Error cargando datos")
        errMsg.font = Font.systemFont(12)
        errMsg.textColor = new Color(COLORS.danger)
        w.addSpacer(4)
        const hint = w.addText("Verifica tu conexión")
        hint.font = Font.systemFont(9)
        hint.textColor = new Color(COLORS.subtitle)
        return w
    }

    if (widgetFamily === "small") {
        renderSmallWidget(w, data)
    } else if (widgetFamily === "medium") {
        renderMediumWidget(w, data)
    } else {
        renderLargeWidget(w, data)
    }

    return w
}

// ============ TAMAÑO PEQUEÑO ============
function renderSmallWidget(w, data) {
    const header = w.addText("🤖 JARVIS")
    header.font = Font.boldSystemFont(14)
    header.textColor = new Color(COLORS.accent)
    w.addSpacer(4)

    const mesLabel = w.addText(data.mes || "")
    mesLabel.font = Font.systemFont(9)
    mesLabel.textColor = new Color(COLORS.subtitle)
    w.addSpacer(6)

    // Total Cuentas Disponible
    const balLabel = w.addText("🏦 CUENTAS (DISPONIBLE)")
    balLabel.font = Font.boldSystemFont(9)
    balLabel.textColor = new Color(COLORS.subtitle)
    w.addSpacer(2)

    const balValue = w.addText(formatMoney(data.total_balance_cuentas || 0))
    balValue.font = Font.boldSystemFont(18)
    balValue.textColor = new Color(COLORS.income)
    w.addSpacer(6)

    // Balance Mes
    const mesBalLabel = w.addText("📊 BALANCE MES")
    mesBalLabel.font = Font.boldSystemFont(9)
    mesBalLabel.textColor = new Color(COLORS.subtitle)
    w.addSpacer(2)

    const net = (data.total_ingresos || 0) - (data.total_gastos || 0)
    const netVal = w.addText(formatMoney(net))
    netVal.font = Font.boldSystemFont(16)
    netVal.textColor = net >= 0 ? new Color(COLORS.income) : new Color(COLORS.danger)
}

// ============ TAMAÑO MEDIANO ============
function renderMediumWidget(w, data) {
    // Header
    const headerRow = w.addStack()
    headerRow.layoutHorizontally()

    const title = headerRow.addText("🤖 JARVIS — " + (data.mes || ""))
    title.font = Font.boldSystemFont(13)
    title.textColor = new Color(COLORS.accent)

    headerRow.addSpacer()

    const net = (data.total_ingresos || 0) - (data.total_gastos || 0)
    const netTxt = headerRow.addText("Neto: " + formatMoney(net))
    netTxt.font = Font.boldSystemFont(10)
    netTxt.textColor = net >= 0 ? new Color(COLORS.income) : new Color(COLORS.danger)

    w.addSpacer(6)

    // SECCIÓN 1: Cuentas y disponible
    const cuentas = data.cuentas || []
    if (cuentas.length > 0) {
        const cLabel = w.addText("🏦 DISPONIBLE EN CUENTAS")
        cLabel.font = Font.boldSystemFont(9)
        cLabel.textColor = new Color(COLORS.subtitle)
        w.addSpacer(2)

        const cRow = w.addStack()
        cRow.layoutHorizontally()

        cuentas.slice(0, 3).forEach((acc, idx) => {
            if (idx > 0) cRow.addSpacer(8)
            const stack = cRow.addStack()
            stack.layoutVertically()
            stack.backgroundColor = new Color(COLORS.card)
            stack.cornerRadius = 6
            stack.setPadding(4, 6, 4, 6)

            const name = stack.addText(acc.nombre)
            name.font = Font.systemFont(8)
            name.textColor = new Color(COLORS.text_dim)
            name.lineLimit = 1

            const amt = stack.addText(formatMoney(acc.disponible))
            amt.font = Font.boldSystemFont(11)
            amt.textColor = new Color(COLORS.income)
        })

        w.addSpacer(6)
    }

    // SECCIÓN 2: Presupuesto vs Gastos (VS por categoría)
    const presupuestos = data.presupuestos || []
    if (presupuestos.length > 0) {
        const pLabel = w.addText("📋 PRESUPUESTO VS GASTOS (CATEGORÍA)")
        pLabel.font = Font.boldSystemFont(9)
        pLabel.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        presupuestos.slice(0, 3).forEach(p => {
            const row = w.addStack()
            row.layoutHorizontally()

            const cat = row.addText(p.categoria)
            cat.font = Font.systemFont(10)
            cat.textColor = p.excedido ? new Color(COLORS.danger) : new Color(COLORS.text)
            cat.lineLimit = 1

            row.addSpacer()

            // Mostrar Gastado vs Límite
            const vsTxt = row.addText(formatMoney(p.gastado) + " / " + formatMoney(p.limite))
            vsTxt.font = Font.boldSystemFont(10)
            vsTxt.textColor = p.excedido ? new Color(COLORS.danger) : new Color(COLORS.text_dim)

            w.addSpacer(2)
        })
    }
}

// ============ TAMAÑO GRANDE ============
function renderLargeWidget(w, data) {
    renderMediumWidget(w, data)
    w.addSpacer(8)

    // Ingresos y Gastos detallados por categoría
    const ingGastos = data.ingresos_gastos || {}
    const keys = Object.keys(ingGastos)
    if (keys.length > 0) {
        const igLabel = w.addText("📊 INGRESOS Y GASTOS POR CATEGORÍA")
        igLabel.font = Font.boldSystemFont(9)
        igLabel.textColor = new Color(COLORS.subtitle)
        w.addSpacer(4)

        keys.slice(0, 4).forEach(cat => {
            const info = ingGastos[cat]
            const row = w.addStack()
            row.layoutHorizontally()

            const cName = row.addText(cat)
            cName.font = Font.systemFont(10)
            cName.textColor = new Color(COLORS.text)

            row.addSpacer()

            let textDetail = ""
            if (info.ingreso > 0) textDetail += "+" + formatMoney(info.ingreso) + " "
            if (info.gasto > 0) textDetail += "-" + formatMoney(info.gasto)

            const dTxt = row.addText(textDetail)
            dTxt.font = Font.boldSystemFont(10)
            dTxt.textColor = info.ingreso > 0 && info.gasto === 0 ? new Color(COLORS.income) : new Color(COLORS.expense)

            w.addSpacer(2)
        })
    }
}

const widget = await buildWidget()
if (config.runsInWidget) {
    Script.setWidget(widget)
} else {
    widget.presentMedium()
}
Script.complete()
