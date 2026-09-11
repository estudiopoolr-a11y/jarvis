// JARVIS Widget para Scriptable
// Muestra tabla de presupuestos + préstamos por cobrar
// Usa /api/widget/dashboard (UNA sola llamada HTTP)
//
// TAMAÑO PEQUEÑO: Total por cobrar + balance total
// TAMAÑO MEDIANO: Resumen mes + total por cobrar + alertas
// TAMAÑO GRANDE: Tabla completa de presupuestos + préstamos

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

// Fetch SIN async/await (mejor compatibilidad con Scriptable widgets)
function fetchJSON(url) {
    try {
        const req = new Request(url)
        req.timeoutInterval = 10  // 10 segundos máximo
        return req.loadJSON()
    } catch(e) {
        console.error("Error fetching: " + url + " - " + e)
        return null
    }
}

function formatMoney(amount) {
    const num = Number(amount) || 0
    const abs = Math.abs(num)
    let formatted
    if (abs >= 1000000) {
        formatted = "$" + (abs/1000000).toFixed(1) + "M"
    } else if (abs >= 100000) {
        formatted = "$" + (abs/1000).toFixed(0) + "K"
    } else {
        formatted = "$" + abs.toLocaleString('es-CO')
    }
    return num < 0 ? "-" + formatted : formatted
}

function buildWidget() {
    const w = new ListWidget()
    w.backgroundColor = new Color(COLORS.bg)
    w.setPadding(10, 10, 10, 10)

    const widgetFamily = config.widgetFamily || "small"

    // UNA SOLA LLAMADA HTTP
    const url = BASE_URL + "/api/widget/dashboard?usuario_id=" + USUARIO
    const data = fetchJSON(url)

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
    // Header
    const header = w.addText("🤖 JARVIS")
    header.font = Font.boldSystemFont(14)
    header.textColor = new Color(COLORS.accent)
    w.addSpacer(4)

    // Mes actual
    const mesLabel = w.addText(data.mes || "")
    mesLabel.font = Font.systemFont(9)
    mesLabel.textColor = new Color(COLORS.subtitle)
    w.addSpacer(6)

    // Por cobrar
    const numPrestamos = (data.prestamos_pendientes || []).length
    if (data.total_por_cobrar > 0) {
        const label = w.addText("💰 POR COBRAR")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.loan)
        w.addSpacer(2)

        const total = w.addText(formatMoney(data.total_por_cobrar))
        total.font = Font.boldSystemFont(22)
        total.textColor = new Color(COLORS.loan)
        w.addSpacer(2)

        const numTxt = w.addText(numPrestamos + " préstamo" + (numPrestamos !== 1 ? 's' : ''))
        numTxt.font = Font.systemFont(9)
        numTxt.textColor = new Color(COLORS.subtitle)
    } else {
        const empty = w.addText("Sin préstamos")
        empty.font = Font.systemFont(11)
        empty.textColor = new Color(COLORS.subtitle)
    }

    w.addSpacer(6)

    // Balance del mes
    if (data.balance_general) {
        const bg = data.balance_general
        const balLabel = w.addText("📊 BALANCE")
        balLabel.font = Font.boldSystemFont(9)
        balLabel.textColor = new Color(COLORS.subtitle)
        w.addSpacer(2)

        const balValue = w.addText(formatMoney(bg.balance))
        balValue.font = Font.boldSystemFont(18)
        balValue.textColor = bg.balance >= 0 ? new Color(COLORS.income) : new Color(COLORS.danger)
        w.addSpacer(1)

        const subTxt = w.addText(formatMoney(bg.ingresos) + " in — " + formatMoney(bg.gastos) + " out")
        subTxt.font = Font.systemFont(8)
        subTxt.textColor = new Color(COLORS.subtitle)
    }
}

// ============ TAMAÑO MEDIANO ============
function renderMediumWidget(w, data) {
    // Header con fecha
    const headerRow = w.addStack()
    headerRow.layoutHorizontally()

    const title = headerRow.addText("🤖 JARVIS")
    title.font = Font.boldSystemFont(14)
    title.textColor = new Color(COLORS.accent)

    headerRow.addSpacer()

    const fecha = new Date()
    const fechaStr = fecha.toLocaleDateString('es-ES', { month: 'short', year: 'numeric' }).toUpperCase()
    const fechaTxt = headerRow.addText(fechaStr)
    fechaTxt.font = Font.systemFont(10)
    fechaTxt.textColor = new Color(COLORS.subtitle)

    w.addSpacer(6)

    // Por cobrar
    const numPrestamos = (data.prestamos_pendientes || []).length
    if (data.total_por_cobrar > 0) {
        const card = w.addStack()
        card.backgroundColor = new Color(COLORS.card_loan)
        card.cornerRadius = 6
        card.paddingAll = 6

        const content = card.addStack()
        content.layoutVertically()

        const label = content.addText("💰 POR COBRAR")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.loan)

        const total = content.addText(formatMoney(data.total_por_cobrar))
        total.font = Font.boldSystemFont(20)
        total.textColor = new Color(COLORS.loan)

        const sub = content.addText(numPrestamos + " préstamo" + (numPrestamos !== 1 ? 's' : '') + " pendiente" + (numPrestamos !== 1 ? 's' : ''))
        sub.font = Font.systemFont(9)
        sub.textColor = new Color(COLORS.subtitle)

        w.addSpacer(6)
    }

    // Tabla compacta: top 5 categorías
    const presupuestos = data.presupuestos || []
    if (presupuestos.length > 0) {
        const label = w.addText("📋 PRESUPUESTOS")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        // Ordenar: excedidos primero, luego por menor disponible
        const ordenados = presupuestos.slice().sort((a, b) => {
            if (a.excedido && !b.excedido) return -1
            if (!a.excedido && b.excedido) return 1
            return a.disponible - b.disponible
        })

        const top = ordenados.slice(0, 5)
        for (let i = 0; i < top.length; i++) {
            const fila = top[i]
            const row = w.addStack()
            row.layoutHorizontally()

            const catText = row.addText(fila.categoria)
            catText.font = Font.systemFont(10)
            catText.textColor = fila.excedido ? new Color(COLORS.danger) : new Color(COLORS.text)
            catText.lineLimit = 1

            row.addSpacer()

            const valText = row.addText(formatMoney(fila.disponible))
            valText.font = Font.boldSystemFont(10)
            if (fila.disponible < 0) {
                valText.textColor = new Color(COLORS.danger)
            } else if (fila.disponible < fila.limite * 0.2) {
                valText.textColor = new Color(COLORS.warning)
            } else {
                valText.textColor = new Color(COLORS.income)
            }

            w.addSpacer(1)
        }

        w.addSpacer(4)
    }

    // Totales
    const sep = w.addText("─".repeat(20))
    sep.font = Font.systemFont(8)
    sep.textColor = new Color(COLORS.border)
    w.addSpacer(2)

    const totalRow = w.addStack()
    totalRow.layoutHorizontally()

    const totalLabel = totalRow.addText("DISPONIBLE")
    totalLabel.font = Font.boldSystemFont(9)
    totalLabel.textColor = new Color(COLORS.subtitle)

    totalRow.addSpacer()

    const totalVal = totalRow.addText(formatMoney(data.total_disponible))
    totalVal.font = Font.boldSystemFont(14)
    totalVal.textColor = data.total_disponible >= 0 ? new Color(COLORS.income) : new Color(COLORS.danger)

    // Alerta si hay excedidos
    const excedidas = data.excedidas || []
    if (excedidas.length > 0) {
        w.addSpacer(2)
        const alert = w.addText("🚨 " + excedidas.length + " presupuesto" + (excedidas.length !== 1 ? 's' : '') + " excedido" + (excedidas.length !== 1 ? 's' : ''))
        alert.font = Font.systemFont(9)
        alert.textColor = new Color(COLORS.danger)
    }
}

// ============ TAMAÑO GRANDE ============
function renderLargeWidget(w, data) {
    // Header
    const header = w.addStack()
    header.layoutHorizontally()

    const logo = header.addText("🤖 JARVIS")
    logo.font = Font.boldSystemFont(14)
    logo.textColor = new Color(COLORS.accent)

    header.addSpacer()

    const fecha = new Date()
    const fechaStr = fecha.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' }).toUpperCase()
    const fechaTxt = header.addText(fechaStr)
    fechaTxt.font = Font.systemFont(10)
    fechaTxt.textColor = new Color(COLORS.subtitle)

    w.addSpacer(4)

    // ===== PRÉSTAMOS POR COBRAR =====
    const prestamos = data.prestamos_pendientes || []
    if (data.total_por_cobrar > 0) {
        const card = w.addStack()
        card.backgroundColor = new Color(COLORS.card_loan)
        card.cornerRadius = 6
        card.paddingAll = 6

        const content = card.addStack()
        content.layoutVertically()

        const labelRow = content.addStack()
        labelRow.layoutHorizontally()
        const label = labelRow.addText("💰 POR COBRAR")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.loan)
        labelRow.addSpacer()
        const numLabel = labelRow.addText(prestamos.length + " préstamo" + (prestamos.length !== 1 ? 's' : ''))
        numLabel.font = Font.systemFont(9)
        numLabel.textColor = new Color(COLORS.subtitle)

        const total = content.addText(formatMoney(data.total_por_cobrar))
        total.font = Font.boldSystemFont(20)
        total.textColor = new Color(COLORS.loan)

        // Top 2 préstamos
        if (prestamos.length > 0) {
            content.addSpacer(2)
            for (let i = 0; i < Math.min(2, prestamos.length); i++) {
                const p = prestamos[i]
                const pRow = content.addStack()
                pRow.layoutHorizontally()
                const left = pRow.addText("• " + (p.persona || '?'))
                left.font = Font.systemFont(9)
                left.textColor = new Color(COLORS.text_dim)
                left.lineLimit = 1
                pRow.addSpacer()
                const right = pRow.addText(formatMoney(p.pendiente))
                right.font = Font.boldSystemFont(9)
                right.textColor = new Color(COLORS.loan)
            }
        }

        w.addSpacer(6)
    }

    // ===== TABLA DE PRESUPUESTOS =====
    const presupuestos = data.presupuestos || []
    if (presupuestos.length > 0) {
        // Ordenar: excedidos primero, luego por menor disponible
        const ordenados = presupuestos.slice().sort((a, b) => {
            if (a.excedido && !b.excedido) return -1
            if (!a.excedido && b.excedido) return 1
            return a.disponible - b.disponible
        })

        const label = w.addText("📋 PRESUPUESTOS DEL MES")
        label.font = Font.boldSystemFont(10)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        // Header de la tabla
        const headerRow = w.addStack()
        headerRow.layoutHorizontally()
        const hCat = headerRow.addText("Categoría")
        hCat.font = Font.boldSystemFont(8)
        hCat.textColor = new Color(COLORS.text_dim)
        headerRow.addSpacer()
        const hPres = headerRow.addText("Presup.  Gastado  Disp.")
        hPres.font = Font.boldSystemFont(8)
        hPres.textColor = new Color(COLORS.text_dim)

        w.addSpacer(2)

        // Separador
        const sep1 = w.addText("─".repeat(40))
        sep1.font = Font.systemFont(6)
        sep1.textColor = new Color(COLORS.border)
        w.addSpacer(1)

        // Filas
        for (let i = 0; i < ordenados.length; i++) {
            const fila = ordenados[i]
            const row = w.addStack()
            row.layoutHorizontally()

            const catText = row.addText(fila.categoria)
            catText.font = Font.systemFont(9)
            catText.textColor = fila.excedido ? new Color(COLORS.danger) : new Color(COLORS.text)
            catText.lineLimit = 1

            row.addSpacer()

            const vals = row.addStack()
            vals.layoutHorizontally()

            const presText = vals.addText(formatMoney(fila.limite))
            presText.font = Font.systemFont(9)
            presText.textColor = new Color(COLORS.text_dim)
            vals.addSpacer(4)
            const gasText = vals.addText(formatMoney(fila.gastado))
            gasText.font = Font.systemFont(9)
            gasText.textColor = new Color(COLORS.expense)
            vals.addSpacer(4)
            const dispText = vals.addText(formatMoney(fila.disponible))
            dispText.font = Font.boldSystemFont(9)
            if (fila.disponible < 0) {
                dispText.textColor = new Color(COLORS.danger)
            } else if (fila.disponible < fila.limite * 0.2) {
                dispText.textColor = new Color(COLORS.warning)
            } else {
                dispText.textColor = new Color(COLORS.income)
            }

            w.addSpacer(1)
        }

        w.addSpacer(4)

        // Separador + Totales
        const sep2 = w.addText("─".repeat(40))
        sep2.font = Font.systemFont(6)
        sep2.textColor = new Color(COLORS.border)
        w.addSpacer(2)

        const totRow = w.addStack()
        totRow.layoutHorizontally()
        const totLabel = totRow.addText("TOTALES")
        totLabel.font = Font.boldSystemFont(9)
        totLabel.textColor = new Color(COLORS.subtitle)
        totRow.addSpacer()
        const totVals = totRow.addStack()
        totVals.layoutHorizontally()
        const tPres = totVals.addText(formatMoney(data.total_presupuestado))
        tPres.font = Font.boldSystemFont(9)
        tPres.textColor = new Color(COLORS.text)
        totVals.addSpacer(4)
        const tGas = totVals.addText(formatMoney(data.total_gastado))
        tGas.font = Font.boldSystemFont(9)
        tGas.textColor = new Color(COLORS.expense)
        totVals.addSpacer(4)
        const tDisp = totVals.addText(formatMoney(data.total_disponible))
        tDisp.font = Font.boldSystemFont(9)
        tDisp.textColor = data.total_disponible >= 0 ? new Color(COLORS.income) : new Color(COLORS.danger)

        // Excedidos count
        const excedidas = (data.excedidas || [])
        if (excedidas.length > 0) {
            w.addSpacer(2)
            const alert = w.addText("🚨 " + excedidas.length + " presupuesto" + (excedidas.length !== 1 ? 's' : '') + " excedido" + (excedidas.length !== 1 ? 's' : ''))
            alert.font = Font.systemFont(9)
            alert.textColor = new Color(COLORS.danger)
        }
    } else {
        const empty = w.addText("Sin presupuestos")
        empty.font = Font.systemFont(11)
        empty.textColor = new Color(COLORS.subtitle)
    }
}

// Ejecutar
const widget = buildWidget()
if (config.runsInWidget) {
    Script.setWidget(widget)
} else {
    widget.presentSmall()
}
Script.complete()
