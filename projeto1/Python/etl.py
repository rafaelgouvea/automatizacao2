# Importar bibliotecas ----
from bcb import sgs


# Importar dados ----
dados_brutos = sgs.get(
    codes = {"IPCA": 433, "INPC": 188, "IGP-M": 189, "IGP-DI": 190, "IPC-Br": 191},
    start = "2000-01-01"
    )


# Tratar dados ----
dados_tratados = dados_brutos.reset_index()


# Salvar dados ----
dados_tratados.to_csv(path_or_buf = "dados_tratados.csv", index = False)