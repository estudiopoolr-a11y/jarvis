// JARVIS Widget para Scriptable
// Muestra: Cuentas + Balance + Top categorías
//
// TAMAÑO PEQUEÑO: Solo cuentas
// TAMAÑO MEDIANO/GRANDE: Cuentas + Resumen + Categorías
//
// Configura la URL según tu servidor:
const BASE_URL = "https://jarvis-h20g.onrender.com"
const USUARIO = "iphone_user"

// Colores tema oscuro
const COLORS = {
    bg: "#0f0f23",
    card: "#1a1a2e",
    text: "#ffffff",
    subtitle: "#8b8b9e",
    income: "#10b981",
    expense: "#ef4444",
    accent: "#6366f1",
    progress: "#3b82f6"
}

// Iconos por tipo de cuenta
const ICONOS = {
    cash: "💵",
    debit: "💳",
    credit: "💳",
    savings: "🏦"
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

    // Cargar datos en paralelo
    const [cuentasData, resumenData] = await Promise.all([
        fetchJSON(`${BASE_URL}/api/kebo/cuentas?usuario_id=${USUARIO}`),
        fetchJSON(`${BASE_URL}/api/finanzas/resumen?usuario_id=${USUARIO}`)
    ])

    if (widgetFamily === "small") {
        // WIDGET PEQUEÑO: Solo cuentas principales
        await renderSmallWidget(w, cuentasData)
    } else {
        // WIDGET MEDIANO/GRANDE: Todo
        await renderMediumLargeWidget(w, cuentasData, resumenData)
    }

    Script.setWidget(w)
    Script.complete()
}

async function renderSmallWidget(w, cuentasData) {
    // Header
    const header = w.addText("💳 CUENTAS")
    header.font = Font.boldSystemFont(12)
    header.textColor = new Color(COLORS.accent)
    w.addSpacer(6)

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

async function renderMediumLargeWidget(w, cuentasData, resumenData) {
    // Header con logo y fecha
    const header = w.addStack()
    header.layoutHorizontal()

    const logo = header.addText("🤖 JARVIS")
    logo.font = Font.boldSystemFont(14)
    logo.textColor = new Color(COLORS.accent)

    header.addSpacer()

    const fecha = new Date()
    const mesNombre = fecha.toLocaleDateString('es-ES', { month: 'short' }).toUpperCase()
    const fechaStr = `${mesNombre} ${fecha.getFullYear()}`
    const fechaTxt = header.addText(fechaStr)
    fechaTxt.font = Font.systemFont(10)
    fechaTxt.textColor = new Color(COLORS.subtitle)

    w.addSpacer(8)

    // ===== SECCIÓN: CUENTAS =====
    if (cuentasData && cuentasData.cuentas && cuentasData.cuentas.length > 0) {
        const cuentasLabel = w.addText("💳 CUENTAS")
        cuentasLabel.font = Font.boldSystemFont(10)
        cuentasLabel.textColor = new Color(COLORS.subtitle)
        w.addSpacer(4)

        // Tarjeta de cuentas
        const cuentasCard = w.addStack()
        cuentasCard.backgroundColor = new Color(COLORS.card)
        cuentasCard.cornerRadius = 8
        cuentasCard.paddingAll = 8

        const cuentasContent = cuentasCard.addStack()
        cuentasContent.layoutVertical()

        for (const cuenta of cuentasData.cuentas) {
            const row = cuentasContent.addStack()
            row.layoutHorizontal()

            const icono = cuenta.icono || "💳"
            const nombre = cuenta.nombre || "Cuenta"
            const balance = Number(cuenta.balance) || 0
            const balanceStr = formatMoneyFull(balance)
            const colorBalance = balance >= 0 ? COLORS.text : COLORS.expense

            const nombreTxt = row.addText(`${icono} ${nombre}`)
            nombreTxt.font = Font.systemFont(11)
            nombreTxt.textColor = new Color(COLORS.text)

            row.addSpacer()

            const balanceTxt = row.addText(balanceStr)
            balanceTxt.font = Font.boldSystemFont(11)
            balanceTxt.textColor = new Color(colorBalance)

            row.addSpacer(4)
        }

        w.addSpacer(8)
    }

    // ===== SECCIÓN: RESUMEN DEL MES =====
    if (resumenData && !resumenData.error) {
        const resumenLabel = w.addText("📊 ESTE MES")
        resumenLabel.font = Font.boldSystemFont(10)
        resumenLabel.textColor = new Color(COLORS.subtitle)
        w.addSpacer(4)

        // Tarjeta resumen
        const resumenCard = w.addStack()
        resumenCard.backgroundColor = new Color(COLORS.card)
        resumenCard.cornerRadius = 8
        resumenCard.paddingAll = 8

        const resumenContent = resumenCard.addStack()
        resumenContent.layoutVertical()

        const balance = Number(resumenData.balance) || 0
        const ingresos = Number(resumenData.ingresos) || 0
        const gastos = Number(resumenData.gastos) || 0

        // Balance principal
        const balanceRow = resumenContent.addStack()
        balanceRow.layoutHorizontal()
        balanceRow.addSpacer()

        const balanceTxt = balanceRow.addText(formatMoneyFull(balance))
        balanceTxt.font = Font.boldSystemFont(16)
        balanceTxt.textColor = balance >= 0 ? new Color(COLORS.income) : new Color(COLORS.expense)

        resumenContent.addSpacer(4)

        // Ingresos y gastos
        const statsRow = resumenContent.addStack()
        statsRow.layoutHorizontal()

        const ingTxt = statsRow.addText(`↑ ${formatMoneyFull(ingresos)}`)
        ingTxt.font = Font.systemFont(10)
        ingTxt.textColor = new Color(COLORS.income)

        statsRow.addSpacer()

        const gasTxt = statsRow.addText(`↓ ${formatMoneyFull(gastos)}`)
        gasTxt.font = Font.systemFont(10)
        gasTxt.textColor = new Color(COLORS.expense)

        // Barra de progreso presupuesto
        if (resumenData.porcentaje_uso !== undefined) {
            resumenContent.addSpacer(6)

            const progressBar = resumenContent.addStack()
            progressBar.layoutHorizontal()

            const pct = Number(resumenData.porcentaje_uso) || 0
            const barBg = progressBar.addStack()
            barBg.backgroundColor = new Color("#2a2a3e")
            barBg.cornerRadius = 3

            const barWidth = Math.min(pct, 100) / 100 * 100 // 100 pts width
            const barFill = barBg.addStack()
            barFill.backgroundColor = pct > 90 ? new Color(COLORS.expense) : new Color(COLORS.progress)
            barFill.cornerRadius = 3

            // Ajustar altura del fill
            barFill.size = new Size(barWidth, 8)
            barBg.size = new Size(100, 8)

            const pctTxt = progressBar.addText(` ${pct}%`)
            pctTxt.font = Font.systemFont(9)
            pctTxt.textColor = new Color(COLORS.subtitle)
        }

        w.addSpacer(8)

        // ===== SECCIÓN: TOP CATEGORÍAS =====
        if (resumenData.datos_por_categoria && resumenData.datos_por_categoria.length > 0) {
            const catsLabel = w.addText("📁 TOP GASTOS")
            catsLabel.font = Font.boldSystemFont(10)
            catsLabel.textColor = new Color(COLORS.subtitle)
            w.addSpacer(4)

            const topCats = resumenData.datos_por_categoria.slice(0, 3)
            for (const cat of topCats) {
                const catRow = w.addStack()
                catRow.layoutHorizontal()

                const catNombre = cat.categoria || "General"
                const catGastado = Number(cat.gastado) || 0
                const catLimite = Number(cat.limite) || 0

                const nombreTxt = catRow.addText(catNombre)
                nombreTxt.font = Font.systemFont(10)
                nombreTxt.textColor = new Color(COLORS.text)
                nombreTxt.lineLimit = 1

                catRow.addSpacer()

                const gastoTxt = catRow.addText(formatMoneyFull(catGastado))
                gastoTxt.font = Font.systemFont(10)
                gastoTxt.textColor = new Color(COLORS.expense)

                if (catLimite > 0) {
                    const pctCat = Math.round((catGastado / catLimite) * 100)
                    const pctTxt = catRow.addText(` (${pctCat}%)`)
                    pctTxt.font = Font.systemFont(9)
                    pctTxt.textColor = pctCat > 90 ? new Color(COLORS.expense) : new Color(COLORS.subtitle)
                }

                w.addSpacer(2)
            }
        }
    } else {
        // Error o sin datos
        w.addSpacer()
        const errorTxt = w.addText("📱 Abre JARVIS para ver tus finanzas")
        errorTxt.font = Font.systemFont(11)
        errorTxt.textColor = new Color(COLORS.subtitle)
        errorTxt.centerAlignText()
        w.addSpacer()
    }

    // Footer
    w.addSpacer()
    const footer = w.addText("Actualizado: " + new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit'}))
    footer.font = Font.systemFont(8)
    footer.textColor = new Color(COLORS.subtitle)
    footer.centerAlignText()
}

main()
