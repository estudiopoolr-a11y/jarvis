// JARVIS Widget para Scriptable
// Muestra: Cuentas + Balance + Top categorías + Alertas + Metas
//
// TAMAÑO PEQUEÑO: Solo cuentas
// TAMAÑO MEDIANO: Cuentas + Resumen mes
// TAMAÑO GRANDE: Todo (cuentas + resumen + categorías + metas + alertas)
//
// Configura la URL según tu servidor:
const BASE_URL = "https://jarvis-h20g.onrender.com"
const USUARIO = "iphone_user"

// Colores tema oscuro
const COLORS = {
    bg: "#0f0f23",
    card: "#1a1a2e",
    card_alt: "#16213e",
    text: "#ffffff",
    subtitle: "#8b8b9e",
    income: "#10b981",
    expense: "#ef4444",
    accent: "#6366f1",
    progress: "#3b82f6",
    warning: "#f59e0b",
    danger: "#ef4444"
}

async function fetchJSON(url) {
    const req = new Request(url)
    try {
        return await req.loadJSON()
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

    // Obtener tamaño del widget
    const widgetFamily = config.widgetFamily || "small"

    // Cargar datos en paralelo (todos los endpoints Kebo)
    const [cuentasData, resumenData, metasData, alertasData, recurrentesData] = await Promise.all([
        fetchJSON(`${BASE_URL}/api/kebo/cuentas?usuario_id=${USUARIO}`),
        fetchJSON(`${BASE_URL}/api/finanzas/resumen?usuario_id=${USUARIO}`),
        fetchJSON(`${BASE_URL}/api/kebo/metas?usuario_id=${USUARIO}`),
        fetchJSON(`${BASE_URL}/api/kebo/alertas?usuario_id=${USUARIO}`),
        fetchJSON(`${BASE_URL}/api/kebo/recurrentes?usuario_id=${USUARIO}`)
    ])

    if (widgetFamily === "small") {
        await renderSmallWidget(w, cuentasData, alertasData)
    } else if (widgetFamily === "medium") {
        await renderMediumWidget(w, cuentasData, resumenData, alertasData)
    } else {
        // large
        await renderLargeWidget(w, cuentasData, resumenData, metasData, alertasData, recurrentesData)
    }

    Script.setWidget(w)
    Script.complete()
}

async function renderSmallWidget(w, cuentasData, alertasData) {
    // Header
    const header = w.addText("💳 CUENTAS")
    header.font = Font.boldSystemFont(12)
    header.textColor = new Color(COLORS.accent)
    w.addSpacer(6)

    // Alerta destacada si hay excedidos
    const excedidos = (alertasData && alertasData.alertas) ? alertasData.alertas.filter(a => a.tipo === "excedido") : []
    if (excedidos.length > 0) {
        const alertTxt = w.addText(`🚨 ${excedidos[0].categoria} excedido`)
        alertTxt.font = Font.systemFont(10)
        alertTxt.textColor = new Color(COLORS.danger)
        w.addSpacer(4)
    }

    if (!cuentasData || !cuentasData.cuentas || cuentasData.cuentas.length === 0) {
        const empty = w.addText("Sin cuentas")
        empty.font = Font.systemFont(11)
        empty.textColor = new Color(COLORS.subtitle)
        return
    }

    // Mostrar top 3 cuentas
    const topCuentas = cuentasData.cuentas.slice(0, 3)
    for (const cuenta of topCuentas) {
        const icono = cuenta.icono || "💳"
        const nombre = cuenta.nombre || "Cuenta"
        const balance = Number(cuenta.balance) || 0
        const balanceStr = formatMoney(balance)

        const row = w.addText(`${icono} ${nombre}: ${balanceStr}`)
        row.font = Font.systemFont(11)
        row.textColor = balance >= 0 ? new Color(COLORS.text) : new Color(COLORS.expense)
        w.addSpacer(3)
    }

    // Total
    if (cuentasData.total_balance !== undefined) {
        w.addSpacer(4)
        const total = w.addText(`Total: ${formatMoney(cuentasData.total_balance)}`)
        total.font = Font.boldSystemFont(11)
        total.textColor = new Color(COLORS.income)
    }
}

async function renderMediumWidget(w, cuentasData, resumenData, alertasData) {
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

    w.addSpacer(8)

    // Sección cuentas (compacta)
    if (cuentasData && cuentasData.cuentas && cuentasData.cuentas.length > 0) {
        const label = w.addText("💳 CUENTAS")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        const cuentasCard = w.addStack()
        cuentasCard.backgroundColor = new Color(COLORS.card)
        cuentasCard.cornerRadius = 6
        cuentasCard.paddingAll = 6

        const cc = cuentasCard.addStack()
        cc.layoutVertical()

        for (const cuenta of cuentasData.cuentas.slice(0, 4)) {
            const row = cc.addStack()
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
            cc.addSpacer(2)
        }

        w.addSpacer(6)
    }

    // Sección resumen mes
    if (resumenData && !resumenData.error) {
        const label = w.addText("📊 ESTE MES")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        const card = w.addStack()
        card.backgroundColor = new Color(COLORS.card)
        card.cornerRadius = 6
        card.paddingAll = 6

        const content = card.addStack()
        content.layoutVertical()

        const balance = Number(resumenData.balance) || 0
        const ingresos = Number(resumenData.ingresos) || 0
        const gastos = Number(resumenData.gastos) || 0

        // Balance
        const balRow = content.addStack()
        balRow.layoutHorizontal()
        balRow.addSpacer()
        const balTxt = balRow.addText(formatMoneyFull(balance))
        balTxt.font = Font.boldSystemFont(18)
        balTxt.textColor = balance >= 0 ? new Color(COLORS.income) : new Color(COLORS.expense)

        content.addSpacer(3)

        const stats = content.addStack()
        stats.layoutHorizontal()
        const ingTxt = stats.addText(`↑ ${formatMoneyFull(ingresos)}`)
        ingTxt.font = Font.systemFont(10)
        ingTxt.textColor = new Color(COLORS.income)
        stats.addSpacer()
        const gasTxt = stats.addText(`↓ ${formatMoneyFull(gastos)}`)
        gasTxt.font = Font.systemFont(10)
        gasTxt.textColor = new Color(COLORS.expense)

        // Barra progreso presupuesto
        if (resumenData.porcentaje_uso !== undefined) {
            content.addSpacer(4)
            const pb = content.addStack()
            pb.layoutHorizontal()
            const pct = Number(resumenData.porcentaje_uso) || 0
            const barBg = pb.addStack()
            barBg.backgroundColor = new Color("#2a2a3e")
            barBg.cornerRadius = 3
            const barFill = barBg.addStack()
            barFill.backgroundColor = pct > 90 ? new Color(COLORS.danger) : pct > 70 ? new Color(COLORS.warning) : new Color(COLORS.progress)
            barFill.cornerRadius = 3
            barFill.size = new Size(Math.min(pct, 100), 6)
            barBg.size = new Size(120, 6)

            const pctTxt = pb.addText(` ${pct}%`)
            pctTxt.font = Font.systemFont(9)
            pctTxt.textColor = new Color(COLORS.subtitle)
        }

        w.addSpacer(6)
    }

    // Alertas
    if (alertasData && alertasData.alertas && alertasData.alertas.length > 0) {
        const label = w.addText("⚠️ ALERTAS")
        label.font = Font.boldSystemFont(9)
        label.textColor = new Color(COLORS.warning)
        w.addSpacer(2)
        for (const a of alertasData.alertas.slice(0, 2)) {
            const txt = w.addText(a.mensaje)
            txt.font = Font.systemFont(9)
            txt.textColor = a.tipo === "excedido" ? new Color(COLORS.danger) : new Color(COLORS.warning)
            w.addSpacer(1)
        }
    }
}

async function renderLargeWidget(w, cuentasData, resumenData, metasData, alertasData, recurrentesData) {
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

    w.addSpacer(8)

    // ===== ALERTAS =====
    if (alertasData && alertasData.alertas && alertasData.alertas.length > 0) {
        const alertLabel = w.addText("⚠️ ALERTAS")
        alertLabel.font = Font.boldSystemFont(10)
        alertLabel.textColor = new Color(COLORS.warning)
        w.addSpacer(3)

        const alertCard = w.addStack()
        alertCard.backgroundColor = new Color("#2d1f1f")
        alertCard.cornerRadius = 6
        alertCard.paddingAll = 6

        for (const a of alertasData.alertas.slice(0, 2)) {
            const txt = alertCard.addText(a.mensaje)
            txt.font = Font.systemFont(10)
            txt.textColor = a.tipo === "excedido" ? new Color(COLORS.danger) : new Color(COLORS.warning)
            alertCard.addSpacer(2)
        }

        w.addSpacer(8)
    }

    // ===== CUENTAS =====
    if (cuentasData && cuentasData.cuentas && cuentasData.cuentas.length > 0) {
        const label = w.addText("💳 CUENTAS")
        label.font = Font.boldSystemFont(10)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        const card = w.addStack()
        card.backgroundColor = new Color(COLORS.card)
        card.cornerRadius = 6
        card.paddingAll = 6

        const content = card.addStack()
        content.layoutVertical()

        for (const cuenta of cuentasData.cuentas) {
            const row = content.addStack()
            row.layoutHorizontal()

            const icono = cuenta.icono || "💳"
            const nombre = cuenta.nombre || ""
            const balance = Number(cuenta.balance) || 0

            const left = row.addText(`${icono} ${nombre}`)
            left.font = Font.systemFont(11)
            left.textColor = new Color(COLORS.text)

            row.addSpacer()

            const right = row.addText(formatMoneyFull(balance))
            right.font = Font.boldSystemFont(11)
            right.textColor = balance >= 0 ? new Color(COLORS.text) : new Color(COLORS.expense)

            content.addSpacer(3)
        }

        w.addSpacer(8)
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

        const card = w.addStack()
        card.backgroundColor = new Color(COLORS.card)
        card.cornerRadius = 6
        card.paddingAll = 6

        const content = card.addStack()
        content.layoutVertical()

        // Balance grande
        const balRow = content.addStack()
        balRow.layoutHorizontal()
        balRow.addSpacer()
        const balTxt = balRow.addText(formatMoneyFull(balance))
        balTxt.font = Font.boldSystemFont(20)
        balTxt.textColor = balance >= 0 ? new Color(COLORS.income) : new Color(COLORS.expense)

        content.addSpacer(4)

        // Stats
        const stats = content.addStack()
        stats.layoutHorizontal()
        const ingTxt = stats.addText(`↑ ${formatMoneyFull(ingresos)}`)
        ingTxt.font = Font.systemFont(11)
        ingTxt.textColor = new Color(COLORS.income)
        stats.addSpacer()
        const gasTxt = stats.addText(`↓ ${formatMoneyFull(gastos)}`)
        gasTxt.font = Font.systemFont(11)
        gasTxt.textColor = new Color(COLORS.expense)

        // Barra presupuesto
        if (resumenData.porcentaje_uso !== undefined) {
            content.addSpacer(6)
            const pct = Number(resumenData.porcentaje_uso) || 0
            const pb = content.addStack()
            pb.layoutHorizontal()

            const barBg = pb.addStack()
            barBg.backgroundColor = new Color("#2a2a3e")
            barBg.cornerRadius = 3
            const barFill = barBg.addStack()
            barFill.backgroundColor = pct > 90 ? new Color(COLORS.danger) : new Color(COLORS.progress)
            barFill.cornerRadius = 3
            barFill.size = new Size(Math.min(pct, 100), 8)
            barBg.size = new Size(150, 8)

            const pctTxt = pb.addText(` ${pct}%`)
            pctTxt.font = Font.systemFont(10)
            pctTxt.textColor = new Color(COLORS.subtitle)
        }

        w.addSpacer(8)

        // Categorías
        if (resumenData.datos_por_categoria && resumenData.datos_por_categoria.length > 0) {
            const catsLabel = w.addText("📁 TOP CATEGORIAS")
            catsLabel.font = Font.boldSystemFont(10)
            catsLabel.textColor = new Color(COLORS.subtitle)
            w.addSpacer(3)

            for (const cat of resumenData.datos_por_categoria.slice(0, 3)) {
                const row = w.addStack()
                row.layoutHorizontal()

                const txt = row.addText(`${cat.categoria || "?"}: ${formatMoneyFull(cat.gastado || 0)}`)
                txt.font = Font.systemFont(10)
                txt.textColor = new Color(COLORS.text)
                txt.lineLimit = 1

                row.addSpacer()

                if (cat.limite > 0) {
                    const pctCat = Math.round((cat.gastado / cat.limite) * 100)
                    const pctTxt = row.addText(`${pctCat}%`)
                    pctTxt.font = Font.systemFont(10)
                    pctTxt.textColor = pctCat > 90 ? new Color(COLORS.danger) : new Color(COLORS.subtitle)
                }

                w.addSpacer(2)
            }
        }
    }

    w.addSpacer(8)

    // ===== METAS =====
    if (metasData && metasData.metas && metasData.metas.length > 0) {
        const label = w.addText("🎯 METAS")
        label.font = Font.boldSystemFont(10)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        for (const meta of metasData.metas.slice(0, 2)) {
            const row = w.addStack()
            row.layoutHorizontal()

            const nombre = meta.nombre || ""
            const pct = meta.porcentaje || 0

            const txt = row.addText(`🎯 ${nombre}: ${pct}%`)
            txt.font = Font.systemFont(10)
            txt.textColor = pct >= 100 ? new Color(COLORS.income) : new Color(COLORS.text)

            w.addSpacer(2)
        }

        w.addSpacer(8)
    }

    // ===== RECURRENTES =====
    if (recurrentesData && recurrentesData.recurrentes && recurrentesData.recurrentes.length > 0) {
        const label = w.addText("🔁 RECURRENTES")
        label.font = Font.boldSystemFont(10)
        label.textColor = new Color(COLORS.subtitle)
        w.addSpacer(3)

        for (const rec of recurrentesData.recurrentes.slice(0, 2)) {
            const txt = w.addText(`📅 ${rec.nombre || ""}: ${formatMoneyFull(rec.monto || 0)}`)
            txt.font = Font.systemFont(10)
            txt.textColor = new Color(COLORS.subtitle)
            w.addSpacer(2)
        }

        w.addSpacer(8)
    }

    // Footer
    w.addSpacer()
    const footer = w.addText("JARVIS " + new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit'}))
    footer.font = Font.systemFont(8)
    footer.textColor = new Color(COLORS.subtitle)
    footer.centerAlignText()
}

main()
