from flask import Flask, request, render_template, redirect, session, url_for, jsonify
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from mnemonic import Mnemonic
import hashlib
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

UPLOAD_FOLDER = 'static/uploads'
TRASH_FOLDER = 'static/trash'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Conectar ao banco de dados SQLite
conn = sqlite3.connect('usuarios.db', check_same_thread=False)
c = conn.cursor()

# Criar a tabela de usuários se não existir
c.execute('''CREATE TABLE IF NOT EXISTS usuarios
             (email text, frase_semente text)''')
c.execute('''CREATE TABLE IF NOT EXISTS arquivos
             (id INTEGER PRIMARY KEY, user_email text, filename text)''')
conn.commit()

def hash_frase_semente(frase_semente):
    return hashlib.sha256(frase_semente.encode()).hexdigest()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('pagina-inicial.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        frase_semente = request.form.get('palavra_semente')

        # Verificar se o campo da frase-semente foi preenchido
        if not frase_semente:
            return "A frase semente deve ser preenchida", 400

        # Hash da frase-semente para comparação
        frase_semente_hashed = hash_frase_semente(frase_semente)

        # Verificar se a frase-semente está correta
        c.execute("SELECT email, frase_semente FROM usuarios WHERE frase_semente = ?", (frase_semente_hashed,))
        resultado = c.fetchone()

        if resultado and resultado[1] == frase_semente_hashed:
            session['email'] = resultado[0]
            session['frase_semente'] = frase_semente
            return redirect('/oficial')
        else:
            return "Frase-semente incorreta", 400

    return render_template('pagina-login.html')

@app.route('/oficial')
def oficial():
    if 'frase_semente' in session and 'email' in session:
        user_email = session['email']
        c.execute("SELECT filename FROM arquivos WHERE user_email = ?", (user_email,))
        images = [row[0] for row in c.fetchall()]
        return render_template('pagina-oficial.html', images=images)
    else:
        return redirect('/login')
    
@app.route('/lixeira')
def lixeira():
    images = os.listdir(TRASH_FOLDER)
    return render_template('lixeira.html', images=images)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'email' not in session:
        return redirect('/login')

    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        user_email = session['email']
        filename = secure_filename(file.filename)
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], user_email)

        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        file.save(os.path.join(user_folder, filename))

        # Salvar a referência do arquivo no banco de dados
        c.execute("INSERT INTO arquivos (user_email, filename) VALUES (?, ?)", (user_email, filename))
        conn.commit()

        return redirect(url_for('oficial'))
    
@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    if 'email' not in session:
        return redirect('/login')

    user_email = session['email']
    src_path = os.path.join(app.config['UPLOAD_FOLDER'], user_email, filename)
    dst_path = os.path.join(TRASH_FOLDER, filename)

    if os.path.exists(src_path):
        os.rename(src_path, dst_path)

        # Remover a referência do arquivo do banco de dados
        c.execute("DELETE FROM arquivos WHERE user_email = ? AND filename = ?", (user_email, filename))
        conn.commit()

    return jsonify({'status': 'success'})

@app.route('/files', methods=['GET'])
def list_files():
    if 'email' not in session:
        return redirect('/login')

    user_email = session['email']
    c.execute("SELECT filename FROM arquivos WHERE user_email = ?", (user_email,))
    files = [row[0] for row in c.fetchall()]
    return jsonify({'files': files})

# Rota para lidar com o registro de novos usuários
@app.route('/signup', methods=['POST'])
def registrar():
    email = request.form.get('email')
    if email is None:
        return "Email não encontrado no formulário", 400

    print(f"Email recebido: {email}")  # Log para depuração

    # Gerar frase-semente
    frase_semente = gerar_frase_semente()

    # Hash da frase-semente antes de salvar no banco de dados
    frase_semente_hashed = hash_frase_semente(frase_semente)

    # Salvar o email e a frase-semente criptografada no banco de dados
    c.execute("INSERT INTO usuarios (email, frase_semente) VALUES (?, ?)", (email, frase_semente_hashed))
    conn.commit()

    # Enviar email de verificação com a frase-semente
    enviar_email_verificacao(email, frase_semente)
    
    return redirect('/login')

def gerar_frase_semente():
    mnemo = Mnemonic("portuguese")
    return mnemo.generate(strength=128)

def enviar_email_verificacao(email, frase_semente):
    try:
        smtp_server = 'smtp.gmail.com'
        port = 587
        sender_email = 'cryptoarchives00@gmail.com'
        password = 'rydn shtk fwlg akyw'  # Use a senha de aplicativo configurada no Gmail

        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = email
        message['Subject'] = 'Verificação de email'
        body = (
            "Gostaríamos de informá-lo(a) que sua chave de acesso exclusiva foi gerada com sucesso. "
            "Para garantir a segurança e privacidade de seus dados, solicitamos que você utilize a chave abaixo ao acessar nossos serviços:\n\n"
            f"Chave de Acesso: {frase_semente}\n\n"
            "Por favor, mantenha esta chave em um local seguro e não a compartilhe com terceiros. "
            "Se tiver qualquer dúvida ou precisar de assistência adicional, não hesite em entrar em contato conosco.\n\n"
            "Agradecemos pela sua atenção e cooperação.\n\n"
            "Atenciosamente, CryptoArchives"
        )
        message.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, email, message.as_string())
        print("Email enviado com sucesso!")  # Log de sucesso
    except Exception as e:
        print(f"Erro ao enviar email: {e}")  # Log de erro

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(TRASH_FOLDER):
        os.makedirs(TRASH_FOLDER)
    app.run(debug=True)
