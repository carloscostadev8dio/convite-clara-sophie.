# Deploy do RSVP – Chá de Fraldas da Clara Sophie

## 1. Planilha do Google (guarda as confirmações com segurança)
1. Crie uma planilha em branco no Google Sheets e copie o ID (trecho entre `/d/` e `/edit` na URL).
2. Em https://console.cloud.google.com crie um projeto > ative **Google Sheets API** e **Google Drive API**.
3. IAM e administrador > Contas de serviço > criar conta > aba Chaves > **Adicionar chave (JSON)**.
4. Abra a planilha > Compartilhar > cole o `client_email` do JSON como **Editor**.

## 2. GitHub
- Crie um repositório **privado** com `main.py`, `requirements.txt`, `.gitignore` e `.streamlit/config.toml`.
- Não suba `secrets.toml` nem arquivos `.csv` (o `.gitignore` já bloqueia).

## 3. Streamlit Community Cloud
1. share.streamlit.io > New app > escolha o repositório e `main.py`.
2. Advanced settings > **Secrets**: cole o conteúdo de `.streamlit/secrets.toml.example` já preenchido.
3. Deploy. Teste uma confirmação e confira se a linha apareceu na planilha.

## 4. Depois do evento
Apague a planilha (ou as linhas) e revogue a chave da conta de serviço.

## Teste local
```
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # edite os valores
streamlit run main.py
```
Sem `SHEET_ID`/`gcp_service_account`, o app usa `confirmacoes.csv` local (só para testes).
