// ==========================================
// 🤖 JARVIS Widget para Scriptable (iOS)
// ==========================================
// Endpoint actualizado para colecciones raíz de Firestore

const BASE_URL = "https://jarvis-two-pi-13.vercel.app"

// ID de usuario opcional (por si tu backend requiere filtrar en /accounts)
const USER_ID = "default_user"

// Colores tema oscuro
const COLORS = {
    bg: "#0f0f23",
    card: "#1a1a2e",
    text: "#ffffff",
    text_dim: "#a0a0b8",
    subtitle: "#8b8b9e",
    income: "#10b981",
    expense: "#ef4444",
    accent: "#6366f1",
    danger: "#ef4444",
    border: "#2a2a3e"
}

async function fetchJSON(url) {
    try {
        const req = new Request(url)
        req.timeout = 15
        req.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        const response = await req.loadJSON()
        return response
    } catch (e) {
        console.error("Error conectando a JARVIS: " + url + " -> " + e)
        return null
    }
}

function formatMoney(amount) {
    const num = Number(amount) || 0
    const abs = Math.abs(num)
    let formatted
    if (abs >= 1000000) {
        formatted = "$" + (abs / 1000000).toFixed(1) + "M"
    } else if (abs >= 10000) {
        formatted = "$" + (abs / 1000).toFixed(0) + "K"
    } else {
        formatted = "$" + abs.toLocaleString('es-CO')
    }
    return num < 0 ? "-" + formatted : formatted
}

async function buildWidget() {
    const w = new ListWidget()
    w.backgroundColor = new Color(COLORS.bg)
    w.setPadding(12, 12, 12, 12)

    const widgetFamily = config.widgetFamily || "medium"

    // Consulta al endpoint adaptado de la colección raíz
    const url = `${BASE_URL}/api/widget/dashboard?usuario_id=${USER_ID}`
    const data = await fetchJSON(url)

    if (!data || data.error) {
        const errStack = w.addStack()
        errStack.layoutVertically()

        const errMsg = errStack.addText("⚠️ Error cargando datos")
        errMsg.font = Font.boldSystemFont(12)
        errMsg.textColor = new Color(COLORS.danger)

        errStack.addSpacer(4)
        const hint = errStack.addText("Revisa el servidor /api/widget/dashboard")
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

    const mesLabel = w.addText(data.mes || "Mes Actual")
    mesLabel.font = Font.systemFont(9)
    mesLabel.textColor = new Color(COLORS.subtitle)
    w.addSpacer(6)

    // Total Cuentas
    const balLabel = w.addText("🏦 DISPONIBLE")
    balLabel.font = Font.boldSystemFont(9)
    balLabel.textColor = new Color(COLORS.subtitle)
    w.addSpacer(2)

    const balValue = w.addText(formatMoney(data.total_balance_cuentas || 0))
    balValue.font = Font.boldSystemFont(16)
    balValue.textColor = new Color(COLORS.income)
    w.addSpacer(6)

    // Neto
    const net = (data.total_ingresos || 0) - (data.total_gastos || 0)
    const netVal = w.addText("Neto: " + formatMoney(net))
    netVal.font = Font.boldSystemFont(11)
    netVal.textColor = net >= 0 ? new Color(COLORS.income) : new Color(COLORS.danger)
}

// ============ TAMAÑO MEDIANO ============
function renderMediumWidget(w, data) {
    // Header
    const headerRow = w.addStack()
    headerRow.layoutHorizontally()

    const title = headerRow.addText("🤖 JARVIS — " + (data.mes || "Dashboard"))
    title.font = Font.boldSystemFont(13)
    title.textColor = new Color(COLORS.accent)

    headerRow.addSpacer()

    const net = (data.total_ingresos || 0) - (data.total_gastos || 0)
    const netTxt = headerRow.addText("Neto: " + formatMoney(net))
    netTxt.font = Font.boldSystemFont(10)
    netTxt.textColor = net >= 0 ? new Color(COLORS.income) : new Color(COLORS.danger)

    w.addSpacer(6)

    // SECCIÓN 1: Cuentas
    const cuentas = data.cuentas || []
    if (cuentas.length > 0) {
        const cLabel = w.addText("🏦 CUENTAS")
        cLabel.font = Font.boldSystemFont(9)
        cLabel.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        const cRow = w.addStack()
        cRow.layoutHorizontally()

        cuentas.slice(0, 3).forEach((acc, idx) => {
            if (idx > 0) cRow.addSpacer(6)
            const stack = cRow.addStack()
            stack.layoutVertically()
            stack.backgroundColor = new Color(COLORS.card)
            stack.cornerRadius = 6
            stack.setPadding(4, 6, 4, 6)

            const name = stack.addText(acc.nombre || acc.name || "Cuenta")
            name.font = Font.systemFont(8)
            name.textColor = new Color(COLORS.text_dim)
            name.lineLimit = 1

            const amt = stack.addText(formatMoney(acc.disponible || acc.balance || 0))
            amt.font = Font.boldSystemFont(10)
            amt.textColor = new Color(COLORS.income)
        })

        w.addSpacer(6)
    }

    // SECCIÓN 2: Presupuesto vs Gastos
    const presupuestos = data.presupuestos || []
    if (presupuestos.length > 0) {
        const pLabel = w.addText("📋 PRESUPUESTOS")
        pLabel.font = Font.boldSystemFont(9)
        pLabel.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        presupuestos.slice(0, 2).forEach(p => {
            const row = w.addStack()
            row.layoutHorizontally()

            const cat = row.addText(p.categoria || "General")
            cat.font = Font.systemFont(10)
            cat.textColor = p.excedido ? new Color(COLORS.danger) : new Color(COLORS.text)
            cat.lineLimit = 1

            row.addSpacer()

            const vsTxt = row.addText(formatMoney(p.gastado || 0) + " / " + formatMoney(p.limite || 0))
            vsTxt.font = Font.boldSystemFont(10)
            vsTxt.textColor = p.excedido ? new Color(COLORS.danger) : new Color(COLORS.text_dim)

            w.addSpacer(2)
        })
    }
}

// ============ TAMAÑO GRANDE ============
function renderLargeWidget(w, data) {
    renderMediumWidget(w, data)
}

const widget = await buildWidget()
if (config.runsInWidget) {
    Script.setWidget(widget)
} else {
    widget.presentMedium()
}
Script.complete()