import json
import os
import sys
import subprocess
from datetime import datetime
import customtkinter as ctk
from tkinter import ttk, messagebox
from PIL import Image

try:
    import requests
except ImportError:
    requests = None


ARQUIVO_JSON = r"\\servidor\D\Automacoes\associadosCOD.json"
def caminho_recurso(nome_arquivo):
    """Retorna o caminho de um arquivo embutido, funcionando tanto no .py quanto no .exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nome_arquivo)


ARQUIVO_LOGO = caminho_recurso("logo_cod.png")

# --- Configuração do auto-update ---
VERSAO_ATUAL = "1.0.1"

# Troque SEU_USUARIO/SEU_REPO pelo caminho real do seu repositório no GitHub.
# O arquivo version.json deve estar na raiz do branch "main".
URL_VERSION_JSON = "https://raw.githubusercontent.com/Srmc-Tecnologia/COD/main/version.json"

# Arquivo local que guarda os dados da última atualização aplicada,
# usado para mostrar o aviso "o que há de novo" na primeira abertura pós-update.
ARQUIVO_INFO_ATUALIZACAO = "ultima_atualizacao.json"

mostrar_detalhes = True
coluna_ordenada = None
ordem_reversa = False
ultima_modificacao_json = None
notificacoes_pendentes = []


COR_FUNDO = "#102014"
COR_CARD = "#17351F"
COR_CARD_2 = "#1F4A2A"
COR_VERDE_ESCURO = "#006D1F"
COR_VERDE_MEDIO = "#178A1E"
COR_VERDE_CLARO = "#8DCB14"
COR_VERDE_LIMAO = "#A8D80D"
COR_TEXTO = "#FFFFFF"
COR_TEXTO_ESCURO = "#111111"


def carregar_json(mostrar_erro=True):
    try:
        with open(ARQUIVO_JSON, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except FileNotFoundError:
        if mostrar_erro:
            messagebox.showerror("Erro", f"Arquivo '{ARQUIVO_JSON}' não encontrado.")
        return None
    except json.JSONDecodeError:
        if mostrar_erro:
            messagebox.showerror("Erro", "O arquivo JSON está inválido.")
        return None


def codigo_eh_alfanumerico(codigo):
    return any(caractere.isalpha() for caractere in codigo)


def encontrar_novos_associados(lista_antiga, lista_nova):
    codigos_antigos = {str(a.get("cod", "")) for a in lista_antiga}
    return [
        a for a in lista_nova
        if str(a.get("cod", "")) and str(a.get("cod", "")) not in codigos_antigos
    ]


def atualizar_sino():
    quantidade = len(notificacoes_pendentes)

    if quantidade > 0:
        botao_sino.configure(
            text=f"🔔 {quantidade}",
            fg_color=COR_VERDE_CLARO,
            hover_color=COR_VERDE_LIMAO,
            text_color=COR_TEXTO_ESCURO
        )
    else:
        botao_sino.configure(
            text="🔔 0",
            fg_color=COR_VERDE_ESCURO,
            hover_color=COR_VERDE_MEDIO,
            text_color=COR_TEXTO
        )


def mostrar_notificacoes():
    if not notificacoes_pendentes:
        messagebox.showinfo("Notificações", "Nenhum novo associado.")
        return

    janela_notificacao = ctk.CTkToplevel(janela)
    janela_notificacao.title("Novos Associados")
    janela_notificacao.geometry("520x420")
    janela_notificacao.configure(fg_color=COR_FUNDO)
    janela_notificacao.grab_set()

    ctk.CTkLabel(
        janela_notificacao,
        text="Novos associados adicionados",
        font=("Segoe UI", 22, "bold"),
        text_color=COR_TEXTO
    ).pack(pady=15)

    caixa_texto = ctk.CTkTextbox(
        janela_notificacao,
        width=470,
        height=270,
        font=("Segoe UI", 14),
        fg_color=COR_CARD,
        text_color=COR_TEXTO,
        border_color=COR_VERDE_CLARO,
        border_width=1
    )
    caixa_texto.pack(padx=20, pady=10, fill="both", expand=True)

    for associado in notificacoes_pendentes:
        codigo = str(associado.get("cod", ""))
        nome = associado.get("nome", "")
        categoria = associado.get("categoria", "Comum")

        caixa_texto.insert("end", f"Código: {codigo}\n")
        caixa_texto.insert("end", f"Nome: {nome}\n")
        caixa_texto.insert("end", f"Categoria: {categoria}\n")
        caixa_texto.insert("end", "-" * 42 + "\n")

    caixa_texto.configure(state="disabled")

    def limpar_notificacoes():
        notificacoes_pendentes.clear()
        atualizar_sino()
        janela_notificacao.destroy()

    ctk.CTkButton(
        janela_notificacao,
        text="Marcar como visto",
        command=limpar_notificacoes,
        fg_color=COR_VERDE_CLARO,
        hover_color=COR_VERDE_LIMAO,
        text_color=COR_TEXTO_ESCURO,
        font=("Segoe UI", 14, "bold"),
        corner_radius=12
    ).pack(pady=12)


def aplicar_tamanho_fonte(normal=True):
    tamanho = 12 if normal else 14
    estilo = ttk.Style()
    estilo.configure("Treeview", font=("Segoe UI", tamanho), rowheight=32)
    estilo.configure("Treeview.Heading", font=("Segoe UI", tamanho, "bold"))


def atualizar_colunas():
    if mostrar_detalhes:
        tabela["displaycolumns"] = ("Código", "Nome", "Categoria", "Tipo do Código")
        botao_detalhes.configure(text="Esconder detalhes")
        aplicar_tamanho_fonte(True)
    else:
        tabela["displaycolumns"] = ("Código", "Nome")
        botao_detalhes.configure(text="Mostrar detalhes")
        aplicar_tamanho_fonte(False)


def alternar_detalhes():
    global mostrar_detalhes
    mostrar_detalhes = not mostrar_detalhes
    atualizar_colunas()


def atualizar_estatisticas(total, exibidos, isencao, alfanumericos, numericos):
    label_total_num.configure(text=str(total))
    label_exibidos_num.configure(text=str(exibidos))
    label_isencao_num.configure(text=str(isencao))
    label_alfanumericos_num.configure(text=str(alfanumericos))
    label_numericos_num.configure(text=str(numericos))


def preparar_dados_filtrados():
    filtro = combo_filtro.get()
    pesquisa = campo_pesquisa.get().lower()

    dados_filtrados = []
    total = len(associados)
    total_isencao = 0
    total_alfanumericos = 0
    total_numericos = 0

    for associado in associados:
        codigo = str(associado.get("cod", ""))
        nome = associado.get("nome", "")
        categoria = associado.get("categoria", "Comum")

        alfanumerico = codigo_eh_alfanumerico(codigo)
        numerico = codigo.isnumeric()
        tipo_codigo = "Alfanumérico" if alfanumerico else "Numérico"

        if categoria == "Isenção de IPTU":
            total_isencao += 1

        if alfanumerico:
            total_alfanumericos += 1
        else:
            total_numericos += 1

        if filtro == "Todos":
            mostrar = True
        elif filtro == "Isenção de IPTU":
            mostrar = categoria == "Isenção de IPTU"
        elif filtro == "Emp. Múltiplas/Doméstica":
            mostrar = categoria == "Emp. Múltiplas/Doméstica"
        elif filtro == "Alfanuméricos":
            mostrar = alfanumerico
        elif filtro == "Numéricos":
            mostrar = numerico
        else:
            mostrar = True

        if mostrar and pesquisa:
            mostrar = (
                pesquisa in codigo.lower()
                or pesquisa in nome.lower()
                or pesquisa in categoria.lower()
                or pesquisa in tipo_codigo.lower()
            )

        if mostrar:
            dados_filtrados.append({
                "Código": codigo,
                "Nome": nome,
                "Categoria": categoria,
                "Tipo do Código": tipo_codigo
            })

    return dados_filtrados, total, total_isencao, total_alfanumericos, total_numericos


def chave_ordenacao(item, coluna):
    valor = item.get(coluna, "")

    if coluna == "Código":
        codigo = str(valor)
        if codigo.isnumeric():
            return (0, int(codigo))
        return (1, codigo.lower())

    return str(valor).lower()


def atualizar_cabecalhos():
    for coluna in colunas:
        texto = coluna

        if coluna == coluna_ordenada:
            texto += " ↓" if ordem_reversa else " ↑"

        tabela.heading(
            coluna,
            text=texto,
            command=lambda c=coluna: ordenar_por_coluna(c)
        )


def ordenar_por_coluna(coluna):
    global coluna_ordenada, ordem_reversa

    if coluna_ordenada == coluna:
        ordem_reversa = not ordem_reversa
    else:
        coluna_ordenada = coluna
        ordem_reversa = False

    atualizar_lista()


def atualizar_lista():
    tabela.delete(*tabela.get_children())

    dados, total, isencao, alfanumericos, numericos = preparar_dados_filtrados()

    if coluna_ordenada:
        dados.sort(
            key=lambda item: chave_ordenacao(item, coluna_ordenada),
            reverse=ordem_reversa
        )

    for item in dados:
        tabela.insert(
            "",
            "end",
            values=(
                item["Código"],
                item["Nome"],
                item["Categoria"],
                item["Tipo do Código"]
            )
        )

    atualizar_estatisticas(total, len(dados), isencao, alfanumericos, numericos)
    atualizar_cabecalhos()


def verificar_atualizacao_json():
    global associados, ultima_modificacao_json

    try:
        modificacao_atual = os.path.getmtime(ARQUIVO_JSON)

        if ultima_modificacao_json is None:
            ultima_modificacao_json = modificacao_atual
            janela.after(5000, verificar_atualizacao_json)
            return

        if modificacao_atual != ultima_modificacao_json:
            novos_dados = carregar_json(mostrar_erro=False)

            if novos_dados is None:
                label_status.configure(text="Aguardando JSON válido...")
                janela.after(5000, verificar_atualizacao_json)
                return

            ultima_modificacao_json = modificacao_atual

            adicionados = encontrar_novos_associados(associados, novos_dados)

            if adicionados:
                notificacoes_pendentes.extend(adicionados)
                atualizar_sino()
                label_status.configure(text=f"{len(adicionados)} novo(s) associado(s)")
            else:
                label_status.configure(text="Lista atualizada automaticamente")

            associados = novos_dados
            atualizar_lista()
            label_hora.configure(text=f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    except FileNotFoundError:
        label_status.configure(text="Arquivo JSON não encontrado")

    janela.after(5000, verificar_atualizacao_json)


def verificar_atualizacao_disponivel():
    """Consulta o version.json remoto. Retorna dict com dados da nova versão, ou None."""
    if requests is None:
        return None

    try:
        resposta = requests.get(URL_VERSION_JSON, timeout=5)
        resposta.raise_for_status()
        dados = resposta.json()

        versao_remota = dados.get("versao")
        url_exe = dados.get("url_exe")
        notas = dados.get("notas", "")

        if versao_remota and versao_remota != VERSAO_ATUAL and url_exe:
            return {"versao": versao_remota, "url_exe": url_exe, "notas": notas}
        return None

    except requests.RequestException:
        return None


def baixar_e_aplicar_atualizacao(atualizacao):
    """Baixa o novo .exe, guarda as notas da versão e dispara o script que substitui o executável atual."""
    pasta_atual = os.path.dirname(sys.executable)
    exe_atual = sys.executable
    exe_novo = os.path.join(pasta_atual, "app_novo.exe")

    with requests.get(atualizacao["url_exe"], stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(exe_novo, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    # Guarda versão e notas para exibir o aviso "o que há de novo" na próxima abertura
    caminho_info = os.path.join(pasta_atual, ARQUIVO_INFO_ATUALIZACAO)
    with open(caminho_info, "w", encoding="utf-8") as f:
        json.dump(
            {"versao": atualizacao["versao"], "notas": atualizacao["notas"]},
            f,
            ensure_ascii=False
        )

    nome_exe_atual = os.path.basename(exe_atual)
    caminho_bat = os.path.join(pasta_atual, "atualizar.bat")

    conteudo_bat = f"""@echo off
timeout /t 2 /nobreak > NUL
del "{exe_atual}"
ren "{exe_novo}" "{nome_exe_atual}"
start "" "{exe_atual}"
del "%~f0"
"""

    with open(caminho_bat, "w") as f:
        f.write(conteudo_bat)

    subprocess.Popen([caminho_bat], shell=True)
    janela.destroy()
    sys.exit(0)


def mostrar_aviso_pos_atualizacao():
    """Se o app acabou de ser atualizado, mostra uma vez o que mudou nesta versão."""
    if not getattr(sys, "frozen", False):
        return

    pasta_atual = os.path.dirname(sys.executable)
    caminho_info = os.path.join(pasta_atual, ARQUIVO_INFO_ATUALIZACAO)

    if not os.path.exists(caminho_info):
        return

    try:
        with open(caminho_info, "r", encoding="utf-8") as f:
            info = json.load(f)
    except (json.JSONDecodeError, OSError):
        os.remove(caminho_info)
        return

    # Só mostra se a versão salva bate com a versão atual do app
    # (garante que o aviso apareça uma única vez, logo após o update)
    if info.get("versao") == VERSAO_ATUAL:
        messagebox.showinfo(
            "Aplicativo atualizado",
            f"O aplicativo foi atualizado com sucesso para a versão {VERSAO_ATUAL}!\n\n"
            f"O que mudou:\n{info.get('notas', 'Sem detalhes disponíveis.')}"
        )

    # Remove o arquivo para não repetir o aviso nas próximas aberturas
    os.remove(caminho_info)


def checar_atualizacao_na_abertura():
    """Verifica se há atualização disponível e pergunta ao usuário se deseja aplicar."""
    # Só faz sentido se o app estiver rodando como .exe compilado (PyInstaller)
    if not getattr(sys, "frozen", False):
        return

    atualizacao = verificar_atualizacao_disponivel()
    if atualizacao:
        resposta = messagebox.askyesno(
            "Atualização disponível",
            f"Nova versão {atualizacao['versao']} disponível!\n\n"
            f"{atualizacao['notas']}\n\nDeseja atualizar agora?"
        )
        if resposta:
            baixar_e_aplicar_atualizacao(atualizacao)


def criar_card_estatistica(master, titulo, valor_inicial):
    card = ctk.CTkFrame(
        master,
        fg_color=COR_CARD,
        corner_radius=18,
        border_width=1,
        border_color=COR_VERDE_MEDIO
    )
    card.pack(side="left", fill="x", expand=True, padx=8, pady=10)

    label_numero = ctk.CTkLabel(
        card,
        text=valor_inicial,
        font=("Segoe UI", 26, "bold"),
        text_color=COR_VERDE_LIMAO
    )
    label_numero.pack(pady=(12, 0))

    ctk.CTkLabel(
        card,
        text=titulo,
        font=("Segoe UI", 13, "bold"),
        text_color=COR_TEXTO
    ).pack(pady=(0, 12))

    return label_numero


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

associados = carregar_json() or []

janela = ctk.CTk()
janela.title("Lista de Associados")
janela.geometry("1240x760")
janela.configure(fg_color=COR_FUNDO)
janela.minsize(1100, 680)

frame_cabecalho = ctk.CTkFrame(
    janela,
    fg_color=COR_CARD,
    corner_radius=20,
    border_width=1,
    border_color=COR_VERDE_MEDIO
)
frame_cabecalho.pack(fill="x", padx=20, pady=(20, 10))

try:
    imagem_logo = ctk.CTkImage(
        light_image=Image.open(ARQUIVO_LOGO),
        dark_image=Image.open(ARQUIVO_LOGO),
        size=(72, 72)
    )

    label_logo = ctk.CTkLabel(
        frame_cabecalho,
        image=imagem_logo,
        text=""
    )
    label_logo.pack(side="left", padx=25, pady=15)

except FileNotFoundError:
    label_logo = ctk.CTkLabel(
        frame_cabecalho,
        text="COD",
        font=("Segoe UI", 28, "bold"),
        text_color=COR_VERDE_LIMAO
    )
    label_logo.pack(side="left", padx=25, pady=15)

frame_titulo = ctk.CTkFrame(frame_cabecalho, fg_color="transparent")
frame_titulo.pack(side="left", pady=15)

ctk.CTkLabel(
    frame_titulo,
    text="Lista de Códigos dos Associados",
    font=("Segoe UI", 30, "bold"),
    text_color=COR_TEXTO
).pack(anchor="w")

ctk.CTkLabel(
    frame_titulo,
    text="Consulta, filtros e monitoramento automático do cadastro",
    font=("Segoe UI", 14),
    text_color=COR_VERDE_LIMAO
).pack(anchor="w", pady=(2, 0))

frame_estatisticas = ctk.CTkFrame(janela, fg_color="transparent")
frame_estatisticas.pack(fill="x", padx=20, pady=5)

label_total_num = criar_card_estatistica(frame_estatisticas, "Total", "0")
label_exibidos_num = criar_card_estatistica(frame_estatisticas, "Exibidos", "0")
label_isencao_num = criar_card_estatistica(frame_estatisticas, "Isenção IPTU", "0")
label_alfanumericos_num = criar_card_estatistica(frame_estatisticas, "Alfanuméricos", "0")
label_numericos_num = criar_card_estatistica(frame_estatisticas, "Numéricos", "0")

frame_topo = ctk.CTkFrame(
    janela,
    fg_color=COR_CARD,
    corner_radius=18,
    border_width=1,
    border_color=COR_VERDE_MEDIO
)
frame_topo.pack(fill="x", padx=20, pady=10)

combo_filtro = ctk.CTkComboBox(
    frame_topo,
    values=[
        "Todos",
        "Isenção de IPTU",
        "Emp. Múltiplas/Doméstica",
        "Alfanuméricos",
        "Numéricos"
    ],
    command=lambda valor: atualizar_lista(),
    width=220,
    height=36,
    fg_color=COR_CARD_2,
    border_color=COR_VERDE_MEDIO,
    button_color=COR_VERDE_ESCURO,
    button_hover_color=COR_VERDE_CLARO,
    dropdown_fg_color=COR_CARD,
    dropdown_hover_color=COR_VERDE_ESCURO,
    text_color=COR_TEXTO,
    font=("Segoe UI", 13)
)
combo_filtro.set("Todos")
combo_filtro.pack(side="left", padx=12, pady=14)

campo_pesquisa = ctk.CTkEntry(
    frame_topo,
    placeholder_text="Pesquisar código ou nome...",
    width=310,
    height=36,
    fg_color=COR_CARD_2,
    border_color=COR_VERDE_MEDIO,
    border_width=2,
    text_color=COR_TEXTO,
    placeholder_text_color="#B8CBBE",
    font=("Segoe UI", 13),
    corner_radius=10
)
campo_pesquisa.pack(side="left", padx=10)
campo_pesquisa.bind("<KeyRelease>", lambda event: atualizar_lista())

botao_detalhes = ctk.CTkButton(
    frame_topo,
    text="Esconder detalhes",
    command=alternar_detalhes,
    width=170,
    height=36,
    fg_color=COR_VERDE_ESCURO,
    hover_color=COR_VERDE_MEDIO,
    text_color=COR_TEXTO,
    font=("Segoe UI", 13, "bold"),
    corner_radius=10
)
botao_detalhes.pack(side="left", padx=10)

botao_sino = ctk.CTkButton(
    frame_topo,
    text="🔔 0",
    command=mostrar_notificacoes,
    width=95,
    height=36,
    fg_color=COR_VERDE_ESCURO,
    hover_color=COR_VERDE_MEDIO,
    text_color=COR_TEXTO,
    font=("Segoe UI", 13, "bold"),
    corner_radius=10
)
botao_sino.pack(side="left", padx=10)

label_status = ctk.CTkLabel(
    frame_topo,
    text="Atualização automática ativa",
    font=("Segoe UI", 12, "bold"),
    text_color=COR_VERDE_LIMAO
)
label_status.pack(side="left", padx=10)

frame_tabela = ctk.CTkFrame(
    janela,
    fg_color=COR_CARD,
    corner_radius=18,
    border_width=1,
    border_color=COR_VERDE_MEDIO
)
frame_tabela.pack(fill="both", expand=True, padx=20, pady=(10, 20))

frame_rodape = ctk.CTkFrame(
    janela,
    fg_color=COR_CARD,
    corner_radius=12,
    border_width=1,
    border_color=COR_VERDE_MEDIO,
    height=40
)

frame_rodape.pack(
    fill="x",
    padx=20,
    pady=(0, 20)
)

label_hora = ctk.CTkLabel(
    frame_rodape,
    text="Última atualização: --:--:--",
    font=("Segoe UI", 12),
    text_color="#D8F5D8"
)

label_hora.pack(
    side="right",
    padx=15,
    pady=8
)

label_hora.configure(
    text=f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
)

colunas = (
    "Código",
    "Nome",
    "Categoria",
    "Tipo do Código"
)

estilo_tabela = ttk.Style()
estilo_tabela.theme_use("clam")

estilo_tabela.configure(
    "Treeview",
    background="#F7FFF7",
    foreground="#102014",
    fieldbackground="#F7FFF7",
    rowheight=32,
    font=("Segoe UI", 12),
    borderwidth=0
)

estilo_tabela.configure(
    "Treeview.Heading",
    background=COR_VERDE_ESCURO,
    foreground=COR_TEXTO,
    font=("Segoe UI", 12, "bold"),
    relief="flat"
)

estilo_tabela.map(
    "Treeview",
    background=[("selected", COR_VERDE_MEDIO)],
    foreground=[("selected", COR_TEXTO)]
)

tabela = ttk.Treeview(
    frame_tabela,
    columns=colunas,
    show="headings",
    displaycolumns=colunas
)

tabela.column("Código", width=140, anchor="center")
tabela.column("Nome", width=480)
tabela.column("Categoria", width=230, anchor="center")
tabela.column("Tipo do Código", width=170, anchor="center")

tabela.pack(
    fill="both",
    expand=True,
    padx=12,
    pady=12
)

atualizar_lista()
atualizar_colunas()
atualizar_sino()
verificar_atualizacao_json()
janela.after(500, mostrar_aviso_pos_atualizacao)
janela.after(1500, checar_atualizacao_na_abertura)

janela.mainloop()