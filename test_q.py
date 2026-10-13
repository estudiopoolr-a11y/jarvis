from modules.finance.interceptor import detectar_e_interactuar_finanzas

queries = [
    "cuales son mis categorias",
    "muéstrame mis categorías", 
    "que categorias tengo",
    "presupuesto de julio",
    "gastos de agosto",
    "hello",
    "como estas",
]

for q in queries:
    r = detectar_e_interactuar_finanzas(q)
    status = "INTERCEPTED" if r else "SKIP"
    print(status + ": " + q)
