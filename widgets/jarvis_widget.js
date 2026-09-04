// JARVIS Widget para Scriptable
// Muestra: Cuentas + Balance + Top categorías + Préstamos por cobrar + Alertas
//
// TAMAÑO PEQUEÑO: Cuentas + por cobrar
// TAMAÑO MEDIANO: Cuentas + Resumen mes + Alertas
// TAMAÑO GRANDE: Todo (cuentas + resumen + categorías + préstamos + metas + recurrentes)
//
// Configura la URL según tu servidor:
const BASE_URL = "https://jarvis-h20g.onrender.com"
const USUARIO = "iphone_user"

// Colores tema oscuro
const COLORS = {
    bg: "#0f0f23",
    card: "#1a1a2e",
    card_alt: "#16213e",
    card_loan: "#3d2818",  // fondo préstamos
    text: "#ffffff",
    subtitle: "#8b8b9e",
    income: "#10b981",
    expense: "#ef4444",
    accent: "#6366f1",
    progress: "#3b82f6",
    warning: "#f59e0b",
    danger: "#ef4444",
    loan: "#fbbf24"  // dorado para préstamos
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
    const formatted = abs >= 1000000
        ? `$${(abs/1000000).toFixed(1)}M`
        : abs >= 1000
            ? `$${(abs/1000).toFixed(0)}K`
            : `$${abs.toFixed(0)}`
    return num < 0 ? `-${formatted}` : formatted
}

function formatMoneyFull(amount) {
    const num = Number(amount) || 0
    return `$${num.toLocaleString('es-CO')}`
}

async function main() {
    const w = new ListWidget()
    w.backgroundColor = new Color(COLORS.bg)
    w.setPadding(12, 12, 12, 12)

    // Obtener tamaño del widget
    const widgetFamily = config.widgetFamily || "small"

    // Cargar datos en paralelo
    const [cuentasData, resumenData, prestamosData, alertasData] = await Promise.all([
        fetchJSON(`${BASE_URL}/api/kebo/cuentas?usuario_id=${USUARIO}`),
        fetchJSON(`${BASE_URL}/api/finanzas/resumen?usuario_id=${USUARIO}`),
        fetchJSON(`${BASE_URL}/api/prestamos/por-cobrar?usuario_id=${USUARIO}`),
        fetchJSON(`${BASE_URL}/api/kebo/alertas?usuario_id=${USUARIO}`)
    ])

    if (widgetFamily === "small") {
        await renderSmallWidget(w, cuentasData, prestamosData, alertasData)
    } else if (widgetFamily === "medium") {
        await renderMediumWidget(w, cuentasData, resumenData, prestamosData, alertasData)
    } else {
        // large
        await renderLargeWidget(w, cuentasData, resumenData, prestamosData, alertasData)
    }

    Script.setWidget(w)
    Script.complete()
}

// ============ TAMAÑO PEQUEÑO ============
async function renderSmallWidget(w, cuentasData, prestamosData, alertasData) {
    // Header
    const header = w.addText("🤖 JARVIS")
    header.font = Font.boldSystemFont(14)
    header.textColor = new Color(COLORS.accent)
    w.addSpacer(4)

    // Por cobrar (destacado arriba)
    if (prestamosData && prestamosData.total_por_cobrar > 0) {
        const porCobrar = prestamosData.total_por_cobrar
        const numPrestamos = prestamosData.total || 0
        const txt = w.addText(`💰 Por cobrar: ${formatMoneyFull(porCobrar)}`)
        txt.font = Font.boldSystemFont(13)
        txt.textColor = new Color(COLORS.loan)
        const sub = w.addText(`${numPrestamos} préstamo${numPrestamos !== 1 ? 's' : ''} pendiente${numPrestamos !== 1 ? 's' : ''}`)
        sub.font = Font.systemFont(9)
        sub.textColor = new Color(COLORS.subtitle)
        w.addSpacer(6)
    }

    // Cuentas
    if (cuentasData && cuentasData.cuentas && cuentasData.cuentas.length > 0) {
        for (const cuenta of cuentasData.cuentas.slice(0, 2)) {
            const icono = cuenta.icono || "💳"
            const nombre = cuenta.nombre || "Cuenta"
            const balance = Number(cuenta.balance) || 0
            const row = w.addText(`${icono} ${nombre}: ${formatMoney(balance)}`)
            row.font = Font.systemFont(11)
            row.textColor = balance >= 0 ? new Color(COLORS.text) : new Color(COLORS.expense)
            w.addSpacer(2)
        }

        if (cuentasData.total_balance !== undefined) {
            w.addSpacer(3)
            const total = w.addText(`Total: ${formatMoney(cuentasData.total_balance)}`)
            total.font = Font.boldSystemFont(11)
            total.textColor = new Color(COLORS.income)
        }
    } else {
        const empty = w.addText("Sin cuentas")
        empty.font = Font.systemFont(11)
        empty.textColor = new Color(COLORS.subtitle)
    }

    // Alerta pequeña al final si hay excedidos
    if (alertasData && alertasData.alertas) {
        const excedidos = alertasData.alertas.filter(a => a.tipo === "excedido")
        if (excedidos.length > 0) {
            w.addSpacer(4)
            const alertTxt = w.addText(`🚨 ${excedidos[0].categoria || 'Presupuesto'} excedido`)
            alertTxt.font = Font.systemFont(9)
            alertTxt.textColor = new Color(COLORS.danger)
        }
    }
}

// ============ TAMAÑO MEDIANO ============
async function renderMediumWidget(w, cuentasData, resumenData, prestamosData, alertasData) {
    // Header
    const headerRow = w.addStack()
    headerRow.layoutHorizontal()

    const title = headerRow.addText("🤖 JARVIS")
    title.font = Font.boldSystemFont(14)
    title.textColor = new Color(COLORS.accent)

    headerRow.addSpacer()

    const fecha = new Date()
    const fechaStr = fecha.toLocaleDateString('es-ES', { month: 'short' }).toUpperCase()
    const fechaTxt = headerRow.addText(fechaStr)
    fechaTxt.font = Font.systemFont(10)
    fechaTxt.textColor = new Color(COLORS.subtitle)

    w.addSpacer(6)

    // Por cobrar (siempre visible en mediano)
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

        const total = content.addText(formatMoneyFull(prestamosData.total_por_cobrar))
        total.font = Font.boldSystemFont(18)
        total.textColor = new Color(COLORS.loan)

        const sub = content.addText(`${prestamosData.total || 0} préstamo${(prestamosData.total || 0) !== 1 ? 's' : ''} pendiente${(prestamosData.total || 0) !== 1 ? 's' : ''}`)
        sub.font = Font.systemFont(9)
        sub.textColor = new Color(COLORS.subtitle)

        w.addSpacer(6)
    }

    // Cuentas (compacta)
    if (cuentasData && cuentasData.cuentas && cuentasData.cuentas.length > 0) {
        const label = w.addText("💳 CUENTAS")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        for (const cuenta of cuentasData.cuentas.slice(0, 3)) {
            const row = w.addStack()
            row.layoutHorizontal()

            const icono = cuenta.icono || "💳"
            const nombre = cuenta.nombre || ""
            const balance = Number(cuenta.balance) || 0

            const left = row.addText(`${icono} ${nombre}`)
            left.font = Font.systemFont(10)
            left.textColor = new Color(COLORS.text)
            row.addSpacer()
            const right = row.addText(formatMoney(balance))
            right.font = Font.boldSystemFont(10)
            right.textColor = balance >= 0 ? new Color(COLORS.text) : new Color(COLORS.expense)
            w.addSpacer(1)
        }

        w.addSpacer(6)
    }

    // Resumen mes
    if (resumenData && !resumenData.error) {
        const label = w.addText("📊 ESTE MES")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        const balance = Number(resumenData.balance) || 0
        const ingresos = Number(resumenData.ingresos) || 0
        const gastos = Number(resumenData.gastos) || 0

        const balRow = w.addStack()
        balRow.layoutHorizontal()
        balRow.addSpacer()
        const balTxt = balRow.addText(formatMoneyFull(balance))
        balTxt.font = Font.boldSystemFont(20)
        balTxt.textColor = balance >= 0 ? new Color(COLORS.income) : new Color(COLORS.expense)

        w.addSpacer(2)

        const stats = w.addStack()
        stats.layoutHorizontal()
        const ingTxt = stats.addText(`↑ ${formatMoneyFull(ingresos)}`)
        ingTxt.font = Font.systemFont(10)
        ingTxt.textColor = new Color(COLORS.income)
        stats.addSpacer()
        const gasTxt = stats.addText(`↓ ${formatMoneyFull(gastos)}`)
        gasTxt.font = Font.systemFont(10)
        gasTxt.textColor = new Color(COLORS.expense)

        // Barra presupuesto
        if (resumenData.porcentaje_uso !== undefined && resumenData.porcentaje_uso !== null) {
            w.addSpacer(4)
            const pb = w.addStack()
            pb.layoutHorizontal()
            const pct = Math.max(0, Math.min(Number(resumenData.porcentaje_uso) || 0, 100))
            const barBg = pb.addStack()
            barBg.backgroundColor = new Color("#2a2a3e")
            barBg.cornerRadius = 3
            if (pct > 0) {
                const barFill = barBg.addStack()
                barFill.backgroundColor = pct > 90 ? new Color(COLORS.danger) : pct > 70 ? new Color(COLORS.warning) : new Color(COLORS.progress)
                barFill.cornerRadius = 3
                barFill.size = new Size(Math.max(pct, 4), 6)
            }
            barBg.size = new Size(140, 6)

            const pctTxt = pb.addText(` ${pct}% usado`)
            pctTxt.font = Font.systemFont(9)
            pctTxt.textColor = new Color(COLORS.subtitle)
        }
    }

    // Alertas al pie
    if (alertasData && alertasData.alertas && alertasData.alertas.length > 0) {
        w.addSpacer(4)
        const excedidos = alertasData.alertas.filter(a => a.tipo === "excedido")
        if (excedidos.length > 0) {
            const txt = w.addText(`🚨 ${excedidos.length} presupuesto${excedidos.length !== 1 ? 's' : ''} excedido${excedidos.length !== 1 ? 's' : ''}`)
            txt.font = Font.systemFont(9)
            txt.textColor = new Color(COLORS.danger)
        }
    }
}

// ============ TAMAÑO GRANDE ============
async function renderLargeWidget(w, cuentasData, resumenData, prestamosData, alertasData) {
    // Header
    const header = w.addStack()
    header.layoutHorizontal()

    const logo = header.addText("🤖 JARVIS")
    logo.font = Font.boldSystemFont(14)
    logo.textColor = new Color(COLORS.accent)

    header.addSpacer()

    const fecha = new Date()
    const fechaStr = fecha.toLocaleDateString('es-ES', { month: 'short', year: 'numeric' }).toUpperCase()
    const fechaTxt = header.addText(fechaStr)
    fechaTxt.font = Font.systemFont(10)
    fechaTxt.textColor = new Color(COLORS.subtitle)

    w.addSpacer(6)

    // ===== POR COBRAR (PRÉSTAMOS) =====
    if (prestamosData && prestamosData.total_por_cobrar > 0) {
        const label = w.addText("💰 PRÉSTAMOS POR COBRAR")
        label.font = Font.boldSystemFont(10)
        label.textColor = new Color(COLORS.loan)
        w.addSpacer(3)

        const card = w.addStack()
        card.backgroundColor = new Color(COLORS.card_loan)
        card.cornerRadius = 6
        card.paddingAll = 8

        const content = card.addStack()
        content.layoutVertical()

        // Total
        const totalRow = content.addStack()
        totalRow.layoutHorizontal()
        totalRow.addSpacer()
        const totalTxt = totalRow.addText(formatMoneyFull(prestamosData.total_por_cobrar))
        totalTxt.font = Font.boldSystemFont(22)
        totalTxt.textColor = new Color(COLORS.loan)

        const numTxt = content.addText(`${prestamosData.total || 0} préstamo${(prestamosData.total || 0) !== 1 ? 's' : ''} pendiente${(prestamosData.total || 0) !== 1 ? 's' : ''}`)
        numTxt.font = Font.systemFont(9)
        numTxt.textColor = new Color(COLORS.subtitle)
        numTxt.centerAlignText()

        // Top 2 personas
        if (prestamosData.prestamos && prestamosData.prestamos.length > 0) {
            content.addSpacer(3)
            for (const p of prestamosData.prestamos.slice(0, 2)) {
                const pRow = content.addStack()
                pRow.layoutHorizontal()
                const nombre = p.persona || "?"
                const monto = Number(p.monto_pendiente) || 0
                const left = pRow.addText(`👤 ${nombre}`)
                left.font = Font.systemFont(10)
                left.textColor = new Color(COLORS.text)
                left.lineLimit = 1
                pRow.addSpacer()
                const right = pRow.addText(formatMoneyFull(monto))
                right.font = Font.boldSystemFont(10)
                right.textColor = new Color(COLORS.loan)
            }
        }

        w.addSpacer(8)
    }

    // ===== ALERTAS =====
    if (alertasData && alertasData.alertas && alertasData.alertas.length > 0) {
        const excedidos = alertasData.alertas.filter(a => a.tipo === "excedido")
        if (excedidos.length > 0) {
            const txt = w.addText(`🚨 ${excedidos.length} presupuesto${excedidos.length !== 1 ? 's' : ''} excedido${excedidos.length !== 1 ? 's' : ''}`)
            txt.font = Font.systemFont(10)
            txt.textColor = new Color(COLORS.danger)
            w.addSpacer(4)
        }
    }

    // ===== CUENTAS =====
    if (cuentasData && cuentasData.cuentas && cuentasData.cuentas.length > 0) {
        const label = w.addText("💳 CUENTAS")
        label.font = Font.boldSystemFont(10)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        for (const cuenta of cuentasData.cuentas) {
            const row = w.addStack()
            row.layoutHorizontal()

            const icono = cuenta.icono || "💳"
            const nombre = cuenta.nombre || ""
            const balance = Number(cuenta.balance) || 0

            const left = row.addText(`${icono} ${nombre}`)
            left.font = Font.systemFont(11)
            left.textColor = new Color(COLORS.text)
            left.lineLimit = 1

            row.addSpacer()

            const right = row.addText(formatMoneyFull(balance))
            right.font = Font.boldSystemFont(11)
            right.textColor = balance >= 0 ? new Color(COLORS.text) : new Color(COLORS.expense)
            w.addSpacer(2)
        }

        w.addSpacer(6)
    }

    // ===== RESUMEN =====
    if (resumenData && !resumenData.error) {
        const label = w.addText("📊 ESTE MES")
        label.font = Font.boldSystemFont(10)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        const balance = Number(resumenData.balance) || 0
        const ingresos = Number(resumenData.ingresos) || 0
        const gastos = Number(resumenData.gastos) || 0

        const balRow = w.addStack()
        balRow.layoutHorizontal()
        balRow.addSpacer()
        const balTxt = balRow.addText(formatMoneyFull(balance))
        balTxt.font = Font.boldSystemFont(20)
        balTxt.textColor = balance >= 0 ? new Color(COLORS.income) : new Color(COLORS.expense)

        w.addSpacer(2)

        const stats = w.addStack()
        stats.layoutHorizontal()
        const ingTxt = stats.addText(`↑ ${formatMoneyFull(ingresos)}`)
        ingTxt.font = Font.systemFont(11)
        ingTxt.textColor = new Color(COLORS.income)
        stats.addSpacer()
        const gasTxt = stats.addText(`↓ ${formatMoneyFull(gastos)}`)
        gasTxt.font = Font.systemFont(11)
        gasTxt.textColor = new Color(COLORS.expense)

        // Barra presupuesto
        if (resumenData.porcentaje_uso !== undefined && resumenData.porcentaje_uso !== null) {
            w.addSpacer(4)
            const pct = Math.max(0, Math.min(Number(resumenData.porcentaje_uso) || 0, 100))
            const pb = w.addStack()
            pb.layoutHorizontal()
            const barBg = pb.addStack()
            barBg.backgroundColor = new Color("#2a2a3e")
            barBg.cornerRadius = 3
            if (pct > 0) {
                const barFill = barBg.addStack()
                barFill.backgroundColor = pct > 90 ? new Color(COLORS.danger) : pct > 70 ? new Color(COLORS.warning) : new Color(COLORS.progress)
                barFill.cornerRadius = 3
                barFill.size = new Size(Math.max(pct, 4), 8)
            }
            barBg.size = new Size(160, 8)

            const pctTxt = pb.addText(` ${pct}% usado`)
            pctTxt.font = Font.systemFont(10)
            pctTxt.textColor = new Color(COLORS.subtitle)
        }

        // Top categorías
        if (resumenData.datos_por_categoria && resumenData.datos_por_categoria.length > 0) {
            w.addSpacer(6)
            const catsLabel = w.addText("📁 TOP CATEGORÍAS")
            catsLabel.font = Font.boldSystemFont(10)
            catsLabel.textColor = new Color(COLORS.subtitle)
            w.addSpacer(3)

            for (const cat of resumenData.datos_por_categoria.slice(0, 3)) {
                const row = w.addStack()
                row.layoutHorizontal()

                const gastado = Number(cat.gastado) || 0
                const limite = Number(cat.limite) || 0
                const txt = row.addText(`${cat.categoria || "?"}: ${formatMoneyFull(gastado)}`)
                txt.font = Font.systemFont(10)
                txt.textColor = new Color(COLORS.text)
                txt.lineLimit = 1

                row.addSpacer()

                if (limite > 0) {
                    const pctCat = Math.round((gastado / limite) * 100)
                    const pctTxt = row.addText(`${pctCat}%`)
                    pctTxt.font = Font.systemFont(10)
                    pctTxt.textColor = pctCat > 90 ? new Color(COLORS.danger) : pctCat > 70 ? new Color(COLORS.warning) : new Color(COLORS.subtitle)
                }
                w.addSpacer(1)
            }
        }
    }

    // Footer
    w.addSpacer()
    const footer = w.addText("JARVIS · " + new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit'}))
    footer.font = Font.systemFont(8)
    footer.textColor = new Color(COLORS.subtitle)
    footer.centerAlignText()
}

main()
