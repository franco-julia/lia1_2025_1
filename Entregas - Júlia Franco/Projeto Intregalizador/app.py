from flask import Flask, request, jsonify, render_template
from tutor import AgenteProfessor, AgenteTirarDuvidas, AgenteQuizzes, AgentePesquisador, AgenteGerenteEstudo, AgenteBuscarQuestaoProva

app = Flask(__name__, template_folder='templates')

professor = AgenteProfessor()
duvidas = AgenteTirarDuvidas()
quiz = AgenteQuizzes()
pesquisador = AgentePesquisador()
provas = AgenteBuscarQuestaoProva()
gerente = AgenteGerenteEstudo(professor, duvidas, quiz, pesquisador, provas)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/tutor', methods=['POST'])
def tutor():
    data = request.json
    pergunta = data.get('pergunta', '')
    if not pergunta:
        return jsonify({'resposta': 'Envie uma pergunta válida.'})
    try:
        resposta = gerente.process_student_request(pergunta)
        return jsonify({'resposta': resposta})
    except Exception as e:
        return jsonify({'resposta': f'Erro: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)
