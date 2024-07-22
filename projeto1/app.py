# Importar bibliotecas ----
from shiny import App, render, ui, reactive
from statsmodels.tsa.seasonal import STL
import pandas as pd
import plotnine as p9


# Importar dados ----
dados = (
    pd.read_csv(
        filepath_or_buffer = "dados_tratados.csv",
        converters = {"Date": pd.to_datetime}
        )
    .assign(indice = lambda x: pd.to_datetime(x.Date))
    .set_index("indice")
    .asfreq("MS")
    )


# Interface do Usuário
app_ui = ui.page_navbar(
    ui.nav(
        "",
        ui.layout_sidebar(
            ui.panel_sidebar(

                ui.markdown(
                    "Dashboard analítica para diagnosticar o comportamento" +
                    " histórico da inflação brasileira, medida pelos princ" +
                    "ipais indicadores de conjuntura econômica. Utilize as" +
                    " opções abaixo para customização da análise."
                ),

                ui.input_select(
                    id = "indicador",
                    label = ui.strong("Indicador:"),
                    choices = dados.columns[1:len(dados.columns)].tolist(),
                    selected = "IPCA",
                    multiple = False
                ),

                ui.input_date_range(
                    id = "datas",
                    label = ui.strong("Data inicial e final:"),
                    start = dados.Date.astype(str).min(),
                    end = dados.Date.astype(str).max(),
                    min = dados.Date.astype(str).min(),
                    max = dados.Date.astype(str).max(),
                    format = "mm/yyyy",
                    startview = "year",
                    language = "pt-BR",
                    separator = " - "
                ),

                ui.input_numeric(
                    id = "ano",
                    label = ui.strong("Comparar com o ano:"),
                    value = int(dados.Date.dt.year.max()),
                    min = int(dados.Date.dt.year.min()),
                    max = int(dados.Date.dt.year.max()),
                    step = 1
                ),

                ui.input_checkbox_group(
                    id = "componentes",
                    label = ui.strong("Componentes:"),
                    choices = ["% a.m.", "Tendência", "Sazonalidade", "Média"],
                    selected = ["% a.m.", "Tendência", "Média"]
                ),

                ui.markdown(
                    """
                    Dados: FGV e IBGE

                    Elaboração: [Análise Macro](https://analisemacro.com.br/)
                    """
                ),
                width = 3
            ),
            ui.panel_main(
                ui.row(ui.output_plot("grafico_padrao_sazonal")),
                ui.row(ui.output_plot("grafico_componentes"))
            )
        )
    ),
    title = ui.strong("Diagnóstico da Inflação"),
    bg = "blue",
    inverse = True
)


# Servidor
def server(input, output, session):

    @reactive.Calc
    def prepara_componentes():

        data_inicial = input.datas()[0].strftime("%Y-%m-%d")
        data_final = input.datas()[1].strftime("%Y-%m-%d")
        selecao_componentes = input.componentes()

        df = (
            dados
            .filter(
                items = ["Date", input.indicador()],
                axis = "columns"
                )
            .rename(columns = {input.indicador(): "indicador"})
            .query("Date >= @data_inicial and Date <= @data_final")
            .dropna()
        )

        modelo = STL(endog = df.indicador, robust = True).fit()

        tabela_componentes = (
            pd.DataFrame(
                data = {
                    "Date": df.Date,
                    "% a.m.": df.indicador,
                    "Tendência": modelo.trend,
                    "Sazonalidade": modelo.seasonal,
                    "Média": df.indicador.mean()
                    },
                index = df.index
                )
            .melt(
                id_vars = "Date",
                value_name = "valor",
                var_name = "variavel"
                )
            .query("variavel in @selecao_componentes")
            )

        return tabela_componentes
    
    @reactive.Calc
    def prepara_padrao_sazonal():

        data_inicial = input.datas()[0].strftime("%Y-%m-%d")
        data_final = input.datas()[1].strftime("%Y-%m-%d")
        ano_selecionado = input.ano()

        dados_ano = (
            dados
            .filter(
                items = ["Date", input.indicador()],
                axis = "columns"
                )
            .rename(columns = {input.indicador(): "indicador"})
            .query("Date.dt.year == @ano_selecionado")
            .assign(
                mes = lambda x: (
                    x.Date.dt.month_name()
                    .astype("category")
                    .cat.set_categories(
                        dados.Date.dt.month_name().unique(),
                        ordered = True
                        )
                    )
                )
            .set_index("mes")
            .filter(items = ["indicador"], axis = "columns")
            .rename(columns = {"indicador": ano_selecionado})
        )

        df = (
            dados
            .filter(
                items = ["Date", input.indicador()],
                axis = "columns"
                )
            .rename(columns = {input.indicador(): "indicador"})
            .query("Date >= @data_inicial and Date <= @data_final")
            .assign(
                mes = lambda x: (
                    x.Date.dt.month_name()
                    .astype("category")
                    .cat.set_categories(
                        dados.Date.dt.month_name().unique(),
                        ordered = True
                        )
                    )
                )
            .groupby("mes")
            .indicador
            .agg(
                ymin = lambda x: x.quantile(0.25),
                Mediana = lambda x: x.quantile(0.5),
                ymax = lambda x: x.quantile(0.75)
            )
            .join(other = dados_ano, how = "left")
            .reset_index()
            .melt(
                id_vars = ["mes", "ymin", "ymax"],
                var_name = "variavel",
                value_name = "valor"
                )
            .assign(variavel = lambda x: x.variavel.astype(str))
        )
        
        return df
    
    @output
    @render.plot
    def grafico_componentes():
        grafico = (
            p9.ggplot(prepara_componentes()) +
            p9.aes(x = "Date", y = "valor", color = "variavel") +
            p9.geom_line(size = 1) +
            p9.labs(
                title = input.indicador() + ": componentes da série",
                caption = "Dados: FGV e IBGE | Elaboração: Análise Macro",
                color = ""
                ) +
            p9.xlab("") +
            p9.ylab("") +
            p9.theme(legend_position = "bottom")
        )
        return grafico

    @output
    @render.plot
    def grafico_padrao_sazonal():
        grafico = (
            p9.ggplot(prepara_padrao_sazonal()) +
            p9.aes(
                x = "mes",
                y = "valor",
                color = "variavel",
                group = "variavel",
                ymin = "ymin",
                ymax = "ymax"
                ) +
            p9.geom_ribbon(alpha = 0.25, color = "none") +
            p9.geom_line(size = 1) +
            p9.labs(
                title = input.indicador() + ": padrão sazonal",
                caption = "Dados: FGV e IBGE | Elaboração: Análise Macro",
                color = ""
                ) +
            p9.xlab("") +
            p9.ylab("") +
            p9.theme(legend_position = "bottom")
        )
        return grafico



# Dashboard Shiny
app = App(app_ui, server)
