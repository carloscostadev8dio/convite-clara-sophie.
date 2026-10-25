# 🐑 Chá de Fraldas da Clara Sophie

Aplicação web em [Streamlit](https://streamlit.io) para os convidados confirmarem presença no chá de fraldas da Clara Sophie (sábado, 21 de novembro, 19h, horário de Manaus). O visual segue o convite: tema de ovelhinha, fundo xadrez bege, nuvens e letras cursivas.

## Funcionalidades

**Para os convidados**
- Ovelhinha animada, nuvens passando e contagem regressiva ao vivo até o evento.
- Formulário de confirmação com acompanhantes, tipo de presente (fraldas P, M, G ou outro mimo) e recado.
- Mural de recados (só aparece quem permitir).
- Botões para abrir o mapa, adicionar ao Google Agenda, baixar o arquivo `.ics` e falar com os pais no WhatsApp.

**Para os pais**
- Área protegida por senha com total de respostas, confirmados e pessoas (com acompanhantes).
- Gráfico dos tamanhos de fralda planejados e lista completa.
- Exportação da lista em CSV.

## Segurança e privacidade

- Senha, chave do Google e número de WhatsApp ficam em `st.secrets`, nunca no código.
- Comparação de senha em tempo constante, com bloqueio após 5 tentativas erradas por sessão.
- Dados salvos em planilha do Google (produção), acessada por conta de serviço.
- Consentimento obrigatório no formulário. Dados coletados: nome, presença, acompanhantes, presente e recado.
- Mural mostra só o primeiro nome e apenas se o convidado permitir.
- Texto dos convidados é limpo, limitado em tamanho e escapado antes de ser exibido. Células que começam com `=`, `+`, `-` ou `@` são neutralizadas contra injeção de fórmulas.
- Nomes repetidos são barrados e há limite de envios por sessão.

Limites conhecidos: o bloqueio de tentativas e o limite de envios valem por sessão do navegador, então não substituem uma senha forte. Quem tiver o link acessa a página, que mostra o endereço do evento. Compartilhe o link apenas com os convidados.

## Estrutura

```
.
├── main.py                        # aplicação completa
├── requirements.txt               # dependências
├── SETUP.md                       # passo a passo do deploy
├── .gitignore                     # bloqueia segredos e dados dos convidados
└── .streamlit/
    ├── config.toml                # tema claro e configurações do servidor
    └── secrets.toml.example       # modelo dos segredos (copie para secrets.toml)
```

## Configuração dos segredos

Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e preencha:

| Chave | Obrigatória | Para quê |
|---|---|---|
| `ADMIN_PASSWORD` | Sim | Senha da área dos pais. Sem ela, a área fica desativada. |
| `WHATSAPP_NUMBER` | Não | Número com DDD (o 55 é adicionado sozinho). Sem ele, o botão não aparece. |
| `SHEET_ID` | Em produção | ID da planilha do Google. |
| `[gcp_service_account]` | Em produção | Conteúdo da chave JSON da conta de serviço. |

Sem `SHEET_ID` e `gcp_service_account` válidos, o app usa o arquivo local `confirmacoes.csv`, só para testes. Valores de exemplo (`COLE_AQUI...`, `...`) são tratados como "não configurado".

## Rodar localmente (Windows)

Requer Python 3.10 ou superior (testado com 3.12).

```powershell
py -m pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml   # edite os valores
streamlit run main.py
```

Para testar localmente, deixe no `secrets.toml` apenas `ADMIN_PASSWORD` e `WHATSAPP_NUMBER`. Para apagar os testes, delete o `confirmacoes.csv`. Se o comando `streamlit` não for reconhecido, use `py -m streamlit run main.py`.

## Deploy

Veja o [SETUP.md](SETUP.md): criação da planilha e da conta de serviço no Google, repositório privado no GitHub e publicação no Streamlit Community Cloud.

## Depois do evento

Apague a planilha (ou as linhas), revogue a chave da conta de serviço no Google Cloud e remova o app do Streamlit Cloud. Os dados dos convidados só devem existir enquanto forem necessários para organizar a festa.

## Tecnologias

Python · Streamlit · pandas · gspread (Google Sheets) · HTML/CSS/SVG para o visual e as animações
