#-----------------------------------------------------------BIBLIOTECAS--------------------------------------------------------------------#
#Importando as bibliotecas
import streamlit as st
import geopandas as gpd
import rasterio as rio
import folium
from streamlit_folium import folium_static
from streamlit_folium import st_folium
import plotly.express as px

#---------------------------------------------------------AJUSTE_DE_TELAS------------------------------------------------------------------#
#Configurar o layout para ser expansível
st.set_page_config(
    page_title="Sistema de crédito rural",
    layout="wide"  #Define o layout como 'wide' (modo largura total)
)

#-------------------------------------------------------------FUNÇÕES----------------------------------------------------------------------#
#Definindo a leitura em cache
@st.cache_data
def load_geodataframe(nome_tabela):
    
    #Caminho do Banco de Dados Geoespaciais
    bd_geopackage = './bd_campos_novos.gpkg'

    #Criando a SQL
    sql = f"SELECT * FROM {nome_tabela}"

    #Filtrando os dados a partir da SQL
    gdf = gpd.read_file(bd_geopackage, sql=sql)

    return gdf

#Selecionar CAR
def selecionar_car (gdf_area_imovel, gdf_reserva_legal, gdf_area_imovel_lulc, gdf_reserva_legal_lulc, opcao):
    #Selecionar o CAR considerando selectbox
    area_imovel = gdf_area_imovel[gdf_area_imovel['cod_imovel'] == opcao]
    reserva_legal = gdf_reserva_legal[gdf_reserva_legal['cod_imovel'] == opcao]
    area_imovel_lulc = gdf_area_imovel_lulc[gdf_area_imovel_lulc['matricula'] == opcao]
    reserva_legal_lulc = gdf_reserva_legal_lulc[gdf_reserva_legal_lulc['matricula'] == opcao]
    #Calcular o Bounding Box do polígono
    bounds = area_imovel.geometry.total_bounds
    minx, miny, maxx, maxy = bounds

    #Definir o centro do mapa com base no polígono selecionado
    centro_lat = (miny + maxy) / 2
    centro_lon = (minx + maxx) / 2

    return area_imovel, reserva_legal, area_imovel_lulc, reserva_legal_lulc, centro_lat, centro_lon, miny, maxy, minx, maxx

#--------------------------------------------------------------DADOS-----------------------------------------------------------------------#
#Ler GeoDataFrame
ai_campos_novos = load_geodataframe('area_imovel')
rl_campos_novos = load_geodataframe('reserva_legal')

#Ler dados de uso e ocupação
ai_lulc = load_geodataframe('ai_lulc')
rl_lulc = load_geodataframe('rl_lulc')

#Obter as matrículas
matriculas = ai_campos_novos.cod_imovel.values.tolist()

#Obtendo as coordenadas centrais do GeoDataFrame 
#union_all pega a coordenada entral da união de todos os poligonos do arquivo, sem ele teria as coords centrais de cada pol
coords_centrais = ai_campos_novos.geometry.centroid.union_all().centroid.xy
#Salvando as coordenadas centrais em lat e long separadas
longitude, latitude = coords_centrais[0][0], coords_centrais[1][0]

#Adicionar camada raster
with rio.open('./lulc.tif') as src: #caminho da imagem
   #salvando a imagem como um numpy - matriz de valores
   img = src.read()
   #Obter as coordenadas do retângulo envolvente [variavel.propriedades que vou salvar nas novas variaveis]
   min_lon, min_lat, max_lon, max_lat = src.bounds
   #Organizar as coordenadas das bordas conforme o Folium
   bounds_orig = [[min_lat, min_lon], [max_lat, max_lon]]

#----------------------------------------------------------BARRA_LATERAL-------------------------------------------------------------------#
#Componentes na barra lateral
st.sidebar.title("Filtros")

#Seleção de opções com selectbox
opcao = st.sidebar.selectbox(
    "Selecione a matrícula:",  #Texto descritivo
    matriculas #Opções disponíveis
)

#Selecionar o CAR de acordo com o selectbox do sidebar
area_imovel, reserva_legal, area_imovel_lulc, reserva_legal_lulc, centro_lat, centro_lon, miny, maxy, minx, maxx = selecionar_car(
    ai_campos_novos,rl_campos_novos,ai_lulc,rl_lulc,opcao)

#Exibir situação do CAR
situacao_car = area_imovel.des_condic.values[0]

#Situação do CAR
st.sidebar.write(f'Situação do CAR: **{situacao_car}**.')

if situacao_car != 'Cancelado por decisao administrativa':
    #Verificar se possui reserva legal declarada
    if not reserva_legal.empty:
        #Calcular o valor do crédito rural
        #credito total por vegetação nativa no imóvel
        total_credito_vgn_ai = float(area_imovel_lulc.veg_nativa.values[0])*1000
        #credito adicional para regeneração de reserva legal antropizada
        total_credito_ant_rl = float(reserva_legal_lulc.antropizada.values[0])*500

        #Exibir
        st.sidebar.write(f'Esse CAR tem direito ao crédito rural.')
        st.sidebar.write(f'Valor do crédito rural para a vegetação nativa da Área do Imóvel: **R${total_credito_vgn_ai}**')
        st.sidebar.write(f'Valor do crédito rural para regeneração da área antropizada da Reserva Legal: **R${total_credito_ant_rl}**')
        st.sidebar.markdown(f'<p style="color:#32CD32;">Valor total do crédito rural: R${total_credito_ant_rl+total_credito_vgn_ai}</p>',
                            unsafe_allow_html=True)
    else:
        st.sidebar.write(f'Esse CAR não possui Reserva Legal declarada.')
        st.sidebar.markdown( """<p style="color:#FF0000;">Esse CAR não tem direito ao crédito rural.</p>""",
                            unsafe_allow_html=True)
else:
    st.sidebar.write(f'Esse CAR está **{situacao_car}**.')
    st.sidebar.markdown("""<p style="color:#FF0000;">Esse CAR não tem direito ao crédito rural.</p>""",
                        unsafe_allow_html=True)
    
#----------------------------------------------------------TELA_PRINCIPAL------------------------------------------------------------------#
#Título do aplicativo
st.title("Sistema de crédito rural - CPR Preserva+")
#Texto explicativo
st.write("Calcula o valor em reais do crédito rural considerando o Cadastro Ambiental Rural (CAR).")

#Exibindo os resultados na página principal
st.write(f"Você escolheu: **{opcao}**.")

#Situação do CAR
st.write(f'Situação do CAR: **{situacao_car}**.')

#Crédito rural
if situacao_car != 'Cancelado por decisao administrativa':
    #Verificar se possui reserva legal declarada
    if not reserva_legal.empty:
        st.markdown(f'<p style="color:#32CD32;">Esse CAR tem direito ao crédito rural no total de R${total_credito_ant_rl+total_credito_vgn_ai}</p>',
                            unsafe_allow_html=True)
    else:
        st.markdown( """<p style="color:#FF0000;">Esse CAR não tem direito ao crédito rural porque não possui Reserva Legal declarada.</p>""",
                            unsafe_allow_html=True)
else:
    st.markdown("""<p style="color:#FF0000;">Esse CAR não tem direito ao crédito rural.</p>""",
                        unsafe_allow_html=True)

#--------------------------------------------------------------MAPA------------------------------------------------------------------------#
#Inicialiando o mapa Folium com os centróides do polígono selecionado
mapa = folium.Map(location=[centro_lat, centro_lon], zoom_start=10)

#Adicionar a camada de imóveis rurais
folium.GeoJson(
    data=area_imovel, #CAR selecionado filtrado pela função selecionar_car
    name='Imóveis rurais', #nome da camada no layercontrol
    tooltip=folium.GeoJsonTooltip( #configurar o que aparece quando passo o mouse
        fields=['des_condic'], #coluna que vai aparecer no tooltip
        aliases=['Situação:'], #nome da coluna no tooltip
        localize=True #melhorar a visualização para localização do usuário
    ),
    style_function=lambda x: { #loop pra aplicar em todos os polígonos
        'fillColor': 'white', #cor de preenchimento
        'color': 'black', #cor das bordas
        'weight': 1, #largura das bordas
        'fillOpacity': 0.01 #opacidade do preenchimento
    }
).add_to(mapa)

#Verificar se Reserva Legal não está vazia
if not reserva_legal.empty:
    #Adicionar a camada de reserva legal
    folium.GeoJson( 
        data=reserva_legal, #CAR selecionado filtrado pela função selecionar_car
        name='Reserva Legal', #nome do layer na visualização 
        tooltip=folium.GeoJsonTooltip( #configurar o que aparece quando passo o mouse
            fields=['cod_imovel','des_condic'], #coluna que vai aparecer no tooltip
            aliases=['Matrícula','Situação:'], #nome da coluna no tooltip
            localize=True #melhorar a visualização para localização do usuário
        ),
        style_function=lambda y: { #loop pra aplicar em todos os polígonos
            'fillColor': 'green', #cor de preenchimento
            'color': 'black', #cor das bordas
            'weight': 1, #largura das bordas
            'fillOpacity': 1 #opacidade do preenchimento
        }
    ).add_to(mapa)

#Adicionar o Numpy ao mapa
folium.raster_layers.ImageOverlay(
   image=img.transpose(1, 2, 0), #indicar a imagem e passar para banda, linha e coluna
   bounds=bounds_orig, #indicar as coordenadas das bordas
   opacity=0.6, #opacidade
   name='Uso e Ocupação' #nome da camada
).add_to(mapa)

#Ajustar o mapa para os limites do polígono
mapa.fit_bounds([[miny, minx], [maxy, maxx]])

#Adicionar controle de camadas
folium.LayerControl().add_to(mapa)

st_folium(mapa, use_container_width=True, height=500)

#-------------------------------------------------------------GRÁFICOS---------------------------------------------------------------------#
#Transformar o DataFrame para o formato longo (long format) usando melt
ai_lulc_melt = area_imovel_lulc[['veg_nativa','antropizada','agua']].melt(var_name="Classes", value_name="Área (ha)")
rl_lulc_melt = reserva_legal_lulc[['veg_nativa','antropizada','agua']].melt(var_name="Classes", value_name="Área (ha)")

#Dicionário com o nome das classes
grafico_label = {
    'veg_nativa': 'Vegetação Nativa',
    'antropizada': 'Área Antropizada',
    'agua': 'Recursos Hídricos'
}

#Renomear classes
ai_lulc_melt['Classes'] = ai_lulc_melt['Classes'].replace(grafico_label)
rl_lulc_melt['Classes'] = rl_lulc_melt['Classes'].replace(grafico_label)

#Converter dado
ai_lulc_melt['Área (ha)'] = ai_lulc_melt['Área (ha)'].astype(float)
rl_lulc_melt['Área (ha)'] = rl_lulc_melt['Área (ha)'].astype(float)

#Dicionário com as cores do gráfico
cores_personalizadas = {
    "Vegetação Nativa": "rgb(13, 141, 41)",  # Verde
    "Área Antropizada": "rgb(225, 237, 54)", # Amarelo
    "Recursos Hídricos": "rgb(52, 16, 214)"  # Azul
}

#Gráfico de barras com plotly
fig_ai = px.bar(ai_lulc_melt, x='Classes', y='Área (ha)',
                color = 'Classes', #define qual parâmetro vai ser utilizado para colorir
                color_discrete_map=cores_personalizadas,
                title='Área do Imóvel')

fig_rl = px.bar(rl_lulc_melt, x='Classes', y='Área (ha)',
                color = 'Classes', #define qual parâmetro vai ser utilizado para colorir
                color_discrete_map=cores_personalizadas,
                title='Reserva Legal')

#Plotar
st.write('**Uso e Cobertura da Terra**')

#Criar duas colunas no Streamlit
col1, col2 = st.columns(2)

#Exibir os gráficos nas colunas
with col1:
    st.plotly_chart(fig_ai, use_container_width=True)

if not reserva_legal.empty: 
    with col2:
            st.plotly_chart(fig_rl, use_container_width=True)
else: 
    with col2:
        st.write('Esse CAR **não** possui Reserva Legal declarada')
    

#-------------------------------------------------------------TABELAS----------------------------------------------------------------------#
#Dicionários com os nomes das colunas
ai_label={'nom_tema':'Tema', 
          'cod_imovel':'Matrícula', 
          'mod_fiscal':'Módulos Fiscais',
          'num_area':'Área (ha)', 
          'des_condic':'Situação',
          'municipio':'Município', 
          'cod_estado':'UF'}

rl_label={'nom_tema':'Tema', 
          'cod_imovel':'Matrícula', 
          'mod_fiscal':'Módulos Fiscais', 
          'num_area':'Área (ha)', 
          'des_condic':'Situação', 
          'municipio':'Município', 
          'cod_estado':'Unidade Federativa'}

#Criar duas colunas no Streamlit
col1, col2 = st.columns(2)

#Exibir as tabelas nas colunas

if not reserva_legal.empty:
    with col1:
        st.write('Área do Imóvel')
        st.dataframe(area_imovel, 
                    hide_index=True, 
                    column_order=('nom_tema', 'cod_imovel', 'mod_fiscal', 'num_area', 'des_condic', 'municipio', 'cod_estado'),
                    column_config=ai_label
                    )

    with col2:
        st.write('Reserva Legal')
        st.dataframe(reserva_legal, 
                    hide_index=True, 
                    column_order=('nom_tema', 'cod_imovel', 'num_area', 'des_condic'),
                    column_config=rl_label
                    )
else:
    st.write('Área do Imóvel')
    st.dataframe(area_imovel, 
                hide_index=True, 
                column_order=('nom_tema', 'cod_imovel', 'mod_fiscal', 'num_area', 'des_condic', 'municipio', 'cod_estado'),
                column_config=ai_label
                )

