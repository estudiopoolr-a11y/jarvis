// JARVIS Widget para Scriptable
// Muestra tabla de presupuestos (presupuestado vs gastado vs disponible)
// + préstamos por cobrar al final
//
// TAMAÑO PEQUEÑO: Total por cobrar + balance total
// TAMAÑO MEDIANO: Resumen mes + total por cobrar + alertas
// TAMAÑO GRANDE: Tabla completa de presupuestos + préstamos
//
// Configura la URL según tu servidor:
const BASE_URL = "https://jarvis-h20g.onrender.com"
const USUARIO = "iphone_user"

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
    const req = new Request(url)
    try {
        const result = await req.loadJSON()
        return result
    } catch(e) {
        console.error("Error fetching:", url, e)
        return null
    }
}

function formatMoney(amount) {
    const num = Number(amount) || 0
    const abs = Math.abs(num)
    let formatted
    if (abs >= 1000000) {
        formatted = `$${(abs/1000000).toFixed(1)}M`
    } else if (abs >= 100000) {
        formatted = `$${(abs/1000).toFixed(0)}K`
    } else {
        formatted = `$${abs.toLocaleString('es-CO')}`
    }
    return num < 0 ? `-${formatted}` : formatted
}

async function main() {
    const w = new ListWidget()
    w.backgroundColor = new Color(COLORS.bg)
    w.setPadding(10, 10, 10, 10)

    const widgetFamily = config.widgetFamily || "small"

    // Cargar datos en paralelo
    const [presupuestosData, prestamosData, alertasData, resumenData] = await Promise.all([
        fetchJSON(`${BASE_URL}/api/admin/presupuestos-tabla?usuario_id=${USUARIO}`),
        fetchJSON(`${BASE_URL}/api/prestamos/por-cobrar?usuario_id=${USUARIO}`),
        fetchJSON(`${BASE_URL}/api/kebo/alertas?usuario_id=${USUARIO}`),
        fetchJSON(`${BASE_URL}/api/finanzas/resumen?usuario_id=${USUARIO}`)
    ])

    if (widgetFamily === "small") {
        await renderSmallWidget(w, presupuestosData, prestamosData)
    } else if (widgetFamily === "medium") {
        await renderMediumWidget(w, presupuestosData, prestamosData, resumenData, alertasData)
    } else {
        await renderLargeWidget(w, presupuestosData, prestamosData, resumenData, alertasData)
    }

    Script.setWidget(w)
    Script.complete()
}

// ============ TAMAÑO PEQUEÑO ============
async function renderSmallWidget(w, presupuestosData, prestamosData) {
    // Header
    const header = w.addText("🤖 JARVIS")
    header.font = Font.boldSystemFont(14)
    header.textColor = new Color(COLORS.accent)
    w.addSpacer(4)

    // Por cobrar (lo más importante)
    if (prestamosData && prestamosData.total_por_cobrar > 0) {
        const label = w.addText("💰 POR COBRAR")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.loan)

        const total = w.addText(formatMoney(prestamosData.total_por_cobrar))
        total.font = Font.boldSystemFont(22)
        total.textColor = new Color(COLORS.loan)

        const numTxt = w.addText(`${prestamosData.total || 0} préstamo${(prestamosData.total || 0) !== 1 ? 's' : ''}`)
        numTxt.font = Font.systemFont(9)
        numTxt.textColor = new Color(COLORS.subtitle)
    } else {
        const empty = w.addText("Sin préstamos")
        empty.font = Font.systemFont(11)
        empty.textColor = new Color(COLORS.subtitle)
    }

    w.addSpacer(4)

    // Total disponible del mes
    if (presupuestosData && presupuestosData.totales) {
        const t = presupuestosData.totales
        const dispLabel = w.addText("💵 DISPONIBLE")
        dispLabel.font = Font.boldSystemFont(9)
        dispLabel.textColor = new Color(COLORS.subtitle)

        const dispValue = w.addText(formatMoney(t.disponible))
        dispValue.font = Font.boldSystemFont(18)
        dispValue.textColor = t.disponible >= 0 ? new Color(COLORS.income) : new Color(COLORS.danger)
    }
}

// ============ TAMAÑO MEDIANO ============
async function renderMediumWidget(w, presupuestosData, prestamosData, resumenData, alertasData) {
    // Header con fecha
    const headerRow = w.addStack()
    headerRow.layoutHorizontal()

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
    if (prestamosData && prestamosData.total_por_cobrar > 0) {
        const card = w.addStack()
        card.backgroundColor = new Color(COLORS.card_loan)
        card.cornerRadius = 6
        card.paddingAll = 6

        const content = card.addStack()
        content.layoutVertical()

        const label = content.addText("💰 POR COBRAR")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.loan)

        const total = content.addText(formatMoney(prestamosData.total_por_cobrar))
        total.font = Font.boldSystemFont(20)
        total.textColor = new Color(COLORS.loan)

        const sub = content.addText(`${prestamosData.total || 0} préstamo${(prestamosData.total || 0) !== 1 ? 's' : ''} pendiente${(prestamosData.total || 0) !== 1 ? 's' : ''}`)
        sub.font = Font.systemFont(9)
        sub.textColor = new Color(COLORS.subtitle)

        w.addSpacer(6)
    }

    // Tabla compacta: top 5 categorías
    if (presupuestosData && presupuestosData.filas && presupuestosData.filas.length > 0) {
        const label = w.addText("📋 PRESUPUESTOS")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        // Mostrar top 5
        const top = presupuestosData.filas.slice(0, 5)
        for (const fila of top) {
            const row = w.addStack()
            row.layoutHorizontal()

            const catText = row.addText(fila.categoria)
            catText.font = Font.systemFont(10)
            catText.textColor = fila.excedido ? new Color(COLORS.danger) : new Color(COLORS.text)
            catText.lineLimit = 1

            row.addSpacer()

            const valText = row.addText(formatMoney(fila.disponible))
            valText.font = Font.boldSystemFont(10)
            valText.textColor = fila.disponible < 0 ? new Color(COLORS.danger) : (fila.disponible < fila.presupuestado * 0.2 ? new Color(COLORS.warning) : new Color(COLORS.income))

            w.addSpacer(1)
        }

        w.addSpacer(4)
    }

    // Totales
    if (presupuestosData && presupuestosData.totales) {
        const t = presupuestosData.totales
        const sep = w.addText("─".repeat(20))
        sep.font = Font.systemFont(8)
        sep.textColor = new Color(COLORS.border)
        w.addSpacer(2)

        const totalRow = w.addStack()
        totalRow.layoutHorizontal()

        const totalLabel = totalRow.addText("DISPONIBLE")
        totalLabel.font = Font.boldSystemFont(9)
        totalLabel.textColor = new Color(COLORS.subtitle)

        totalRow.addSpacer()

        const totalVal = totalRow.addText(formatMoney(t.disponible))
        totalVal.font = Font.boldSystemFont(14)
        totalVal.textColor = t.disponible >= 0 ? new Color(COLORS.income) : new Color(COLORS.danger)
    }

    // Alerta si hay excedidos
    if (alertasData && alertasData.alertas) {
        const excedidos = alertasData.alertas.filter(a => a.tipo === "excedido")
        if (excedidos.length > 0) {
            w.addSpacer(2)
            const alert = w.addText(`🚨 ${excedidos.length} presupuesto${excedidos.length !== 1 ? 's' : ''} excedido${excedidos.length !== 1 ? 's' : ''}`)
            alert.font = Font.systemFont(9)
            alert.textColor = new Color(COLORS.danger)
        }
    }
}

// ============ TAMAÑO GRANDE ============
async function renderLargeWidget(w, presupuestosData, prestamosData, resumenData, alertasData) {
    // Header
    const header = w.addStack()
    header.layoutHorizontal()

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
    if (prestamosData && prestamosData.total_por_cobrar > 0) {
        const card = w.addStack()
        card.backgroundColor = new Color(COLORS.card_loan)
        card.cornerRadius = 6
        card.paddingAll = 6

        const content = card.addStack()
        content.layoutVertical()

        const labelRow = content.addStack()
        labelRow.layoutHorizontal()
        const label = labelRow.addText("💰 POR COBRAR")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.loan)
        labelRow.addSpacer()
        const numLabel = labelRow.addText(`${prestamosData.total || 0} préstamo${(prestamosData.total || 0) !== 1 ? 's' : ''}`)
        numLabel.font = Font.systemFont(9)
        numLabel.textColor = new Color(COLORS.subtitle)

        const total = content.addText(formatMoney(prestamosData.total_por_cobrar))
        total.font = Font.boldSystemFont(20)
        total.textColor = new Color(COLORS.loan)

        // Top 2 préstamos
        if (prestamosData.prestamos && prestamosData.prestamos.length > 0) {
            content.addSpacer(2)
            for (const p of prestamosData.prestamos.slice(0, 2)) {
                const pRow = content.addStack()
                pRow.layoutHorizontal()
                const left = pRow.addText(`• ${p.persona || '?'}`)
                left.font = Font.systemFont(9)
                left.textColor = new Color(COLORS.text_dim)
                left.lineLimit = 1
                pRow.addSpacer()
                const right = pRow.addText(formatMoney(p.monto_pendiente))
                right.font = Font.boldSystemFont(9)
                right.textColor = new Color(COLORS.loan)
            }
        }

        w.addSpacer(6)
    }

    // ===== TABLA DE PRESUPUESTOS =====
    if (presupuestosData && presupuestosData.filas && presupuestosData.filas.length > 0) {
        const label = w.addText("📋 PRESUPUESTOS DEL MES")
        label.font = Font.boldSystemFont(10)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        // Header de la tabla
        const headerRow = w.addStack()
        headerRow.layoutHorizontal()
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
        for (const fila of presupuestosData.filas) {
            const row = w.addStack()
            row.layoutHorizontal()

            // Categoría
            const catText = row.addText(fila.categoria)
            catText.font = Font.systemFont(9)
            catText.textColor = fila.excedido ? new Color(COLORS.danger) : new Color(COLORS.text)
            catText.lineLimit = 1

            row.addSpacer()

            // Valores en línea: Presup / Gastado / Disp
            const vals = row.addText(`${formatMoney(fila.presupuestado)}  ${formatMoney(fila.gastado)}  ${formatMoney(fila.disponible)}`)
            vals.font = Font.systemFont(9)
            vals.textColor = fila.disponible < 0
                ? new Color(COLORS.danger)
                : (fila.disponible < fila.presupuestado * 0.2 ? new Color(COLORS.warning) : new Color(COLORS.text_dim))
            vals.lineLimit = 1

            w.addSpacer(1)
        }

        w.addSpacer(3)

        // Separador
        const sep2 = w.addText("─".repeat(40))
        sep2.font = Font.systemFont(6)
        sep2.textColor = new Color(COLORS.border)
        w.addSpacer(2)

        // Total
        const t = presupuestosData.totales
        const totalRow = w.addStack()
        totalRow.layoutHorizontal()

        const totalLabel = totalRow.addText("💵 DISPONIBLE")
        totalLabel.font = Font.boldSystemFont(10)
        totalLabel.textColor = new Color(COLORS.text)

        totalRow.addSpacer()

        const totalText = totalRow.addText(formatMoney(t.disponible))
        totalText.font = Font.boldSystemFont(14)
        totalText.textColor = t.disponible >= 0 ? new Color(COLORS.income) : new Color(COLORS.danger)

        w.addSpacer(2)

        // Excedidos
        if (t.excedidos_count > 0) {
            const excTxt = w.addText(`🚨 ${t.excedidos_count} categoría${t.excedidos_count !== 1 ? 's' : ''} excedida${t.excedidos_count !== 1 ? 's' : ''}`)
            excTxt.font = Font.systemFont(9)
            excTxt.textColor = new Color(COLORS.danger)
        } else {
            const okTxt = w.addText("✅ Todo en orden")
            okTxt.font = Font.systemFont(9)
            okTxt.textColor = new Color(COLORS.income)
        }
    } else {
        const empty = w.addText("Sin presupuestos configurados")
        empty.font = Font.systemFont(11)
        empty.textColor = new Color(COLORS.subtitle)
    }

    // Footer
    w.addSpacer()
    const footer = w.addText("JARVIS · " + new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit'}))
    footer.font = Font.systemFont(8)
    footer.textColor = new Color(COLORS.subtitle)
    footer.centerAlignText()
}

main()
