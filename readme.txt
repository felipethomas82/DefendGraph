#Para instalar as dependências
python -m venv .venv
.\.venv\Scripts\activate
python.exe -m pip install --upgrade pip
pip install -r requirements.txt

#Para iniciar a aplicação
streamlit run .\app.py