import os
import re
from typing import List, Dict, Any, Optional
from google.adk.agents import Agent
from google.adk.tools import agent_tool, google_search as AdkGoogleSearchTool
import google.generativeai as genai

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or "AIzaSyBIosCu2QCVW3-uxd4cN0Euy7gXrhWswnk"
genai.configure(api_key=GOOGLE_API_KEY)

class GeminiLlmConnection:
    def __init__(self, model_name: str = "models/gemini-1.5-flash"):
        self.model = genai.GenerativeModel(model_name)

    def send_content(self, content):
        prompt = content.parts[0].text if content.parts else ""
        try:
            response = self.model.generate_content(prompt)
            return {"text": response.text}
        except Exception as e:
            return {"text": f"[Erro] Falha ao gerar conteúdo: {e}"}

class FakeContent:
    def __init__(self, parts):
        self.parts = parts

class Part:
    def __init__(self, text):
        self.text = text
        self.function_response = None

class AgenteProfessor(Agent):
    def __init__(self, name: str = "Agente_Professor"):
        super().__init__(
            name=name,
            description="Responsável por ensinar a matéria, criar resumos e explicações detalhadas.",
            instruction="Você é um professor experiente e didático.",
            model="gemini-1.5-flash",
            tools=[AdkGoogleSearchTool],
        )

    def process_query(self, query: str) -> str:
        print(f"[{self.name}]: Preparando resumo sobre '{query}'...")
        model = GeminiLlmConnection("models/gemini-1.5-flash")
        prompt = f"Gere um resumo detalhado e didático sobre '{query}' para um aluno do ensino médio."
        response = model.send_content(FakeContent([Part(prompt)]))
        return response["text"] if isinstance(response, dict) and "text" in response else str(response)

class AgenteTirarDuvidas(Agent):
    def __init__(self, name: str = "Agente_Duvidas"):
        super().__init__(
            name=name,
            description="Responde perguntas pontuais sobre a matéria.",
            instruction="Você é um monitor atencioso.",
            model="gemini-1.5-flash",
            tools=[AdkGoogleSearchTool],
        )

    def process_query(self, query: str) -> str:
        print(f"[{self.name}]: Respondendo à dúvida: '{query}'")
        model = GeminiLlmConnection("models/gemini-1.5-flash")
        prompt = f"Explique de forma clara para um aluno do ensino médio: '{query}'."
        response = model.send_content(FakeContent([Part(prompt)]))
        return response["text"] if isinstance(response, dict) and "text" in response else str(response)

class AgenteQuizzes(Agent):
    def __init__(self, name: str = "Agente_Quizzes"):
        super().__init__(
            name=name,
            description="Cria quizzes para testar o conhecimento.",
            instruction="Você é um criador de quizzes.",
            model="gemini-1.5-pro",
            tools=[],
        )
        self._current_quiz: Optional[Dict[str, Any]] = None
        self._current_index: int = 0
        self._student_answers: Dict[int, str] = {}

    def create_quiz(self, topic: str) -> str:
        print(f"[{self.name}]: Criando quiz sobre '{topic}'...")
        model = GeminiLlmConnection("models/gemini-1.5-flash")
        prompt = f"""
        Elabore 3 questões de múltipla escolha no estilo ENEM sobre o tema: '{topic}'.

        Para cada questão, siga rigorosamente as seguintes instruções:
        - Comece com um texto motivador de até 60 palavras.
        - Em seguida, apresente um enunciado cujo sentido deve ser completado corretamente por uma das alternativas.
        - O enunciado **não deve terminar com dois-pontos**.
        - Apresente cinco alternativas (A a E), dispostas na vertical.
        - Todas as alternativas devem começar com verbos no infinitivo ou imperativo, com letra inicial minúscula.
        - Coloque ponto final ao fim de todas as alternativas.
        - Após as alternativas, indique a alternativa correta e forneça um breve comentário justificando a resposta escolhida.

        Siga esse padrão para todas as três questões.
        """
        quiz_text = model.send_content(FakeContent([Part(prompt)]))
        quiz_text = quiz_text["text"] if isinstance(quiz_text, dict) and "text" in quiz_text else str(quiz_text)

        self._current_quiz = self._parse_quiz(quiz_text)

        if not self._current_quiz["questions"]:
            return "Não foi possível gerar o quiz. Tente reformular o tema ou tentar novamente."

        self._current_index = 0
        self._student_answers = {}
        return self.next_question()

    def next_question(self) -> str:
        if not self._current_quiz or self._current_index >= len(self._current_quiz["questions"]):
            return self.evaluate_quiz(self._student_answers)

        q = self._current_quiz["questions"][self._current_index]
        texto = f"{q['motivador']}\n\n{q['question']}\n"
        for letra in ["A", "B", "C", "D", "E"]:
            if letra in q["options"]:
                texto += f"{letra}) {q['options'][letra]}\n"
        return texto


    def submit_answer(self, answer: str) -> str:
        if not self._current_quiz or self._current_index >= len(self._current_quiz["questions"]):
            return "Nenhuma pergunta pendente."

        current_question = self._current_quiz["questions"][self._current_index]
        self._student_answers[current_question["number"]] = answer.strip().upper()
        self._current_index += 1
        return self.next_question()

    def _parse_quiz(self, quiz_text: str) -> Dict[str, Any]:
        quiz_data = {"questions": []}
        blocos = re.split(r"\*\*Quest[aã]o\s+\d+\*\*", quiz_text, flags=re.IGNORECASE)

        for i, bloco in enumerate(blocos[1:], 1):
            linhas = bloco.strip().split('\n')
            motivador = []
            enunciado = ""
            opcoes = {}
            correta = ""
            comentario = ""

            etapa = "motivador"
            for linha in linhas:
                linha = linha.strip()
                if not linha:
                    continue
                if re.match(r"^[Aa-eE]\)", linha):  # A) B) C) D) E)
                    etapa = "alternativas"
                    letra = linha[0].upper()
                    texto = linha[2:].strip()
                    opcoes[letra] = texto
                elif "resposta correta" in linha.lower():
                    etapa = "comentario"
                    correta = linha.split(":")[-1].strip().upper()
                elif etapa == "comentario" and not comentario:
                    comentario = linha.strip()
                elif etapa == "motivador":
                    motivador.append(linha)
                elif etapa == "alternativas":
                    enunciado += linha + " "

            quiz_data["questions"].append({
                "number": i,
                "motivador": " ".join(motivador),
                "question": enunciado.strip(),
                "options": opcoes,
                "correct_answer": correta,
                "comment": comentario
            })

        return quiz_data

    def evaluate_quiz(self, student_answers: Dict[int, str]) -> str:
        if not self._current_quiz:
            return "Nenhum quiz ativo."

        feedback = []
        score = 0
        total = len(self._current_quiz["questions"])

        for q in self._current_quiz["questions"]:
            num = q["number"]
            correta = q["correct_answer"].strip().upper()
            resposta = student_answers.get(num, "").strip().upper()
            comentario = q.get("comment", "")
            if resposta == correta:
                feedback.append(f"Pergunta {num}: ✅ Correta.\nComentário: {comentario}")
                score += 1
            else:
                feedback.append(f"Pergunta {num}: ❌ Incorreta. Sua: {resposta}, Correta: {correta}\nComentário: {comentario}")

        feedback.append(f"\nPontuação final: {score}/{total}")
        self._current_quiz = None
        return "\n\n".join(feedback)

class AgentePesquisador(Agent):
    def __init__(self, name: str = "Agente_Pesquisador"):
        super().__init__(
            name=name,
            description="Faz pesquisas no Google.",
            instruction="Você é um pesquisador eficiente.",
            model="gemini-1.5-flash",
            tools=[AdkGoogleSearchTool],
        )

    def process_query(self, query: str) -> str:
        print(f"[{self.name}]: Pesquisando '{query}'...")
        model = GeminiLlmConnection("models/gemini-1.5-flash")
        prompt = f"Resuma os 3 pontos mais importantes sobre '{query}' para um aluno do ensino médio."
        response = model.send_content(FakeContent([Part(prompt)]))
        return response["text"] if isinstance(response, dict) and "text" in response else str(response)

class AgenteBuscarQuestaoProva(Agent):
    def __init__(self, name: str = "Agente_Prova"):
        super().__init__(
            name=name,
            description="Busca e comenta questões de provas como ENEM ou vestibulares.",
            instruction="Você é um analista de provas experiente. Apresente a questão solicitada e comente a alternativa correta.",
            model="gemini-1.5-flash",
            tools=[]
        )

    def process_query(self, query: str) -> str:
        print(f"[{self.name}]: Buscando questão solicitada: '{query}'")
        model = GeminiLlmConnection("models/gemini-1.5-flash")
        prompt = f"""
        Um aluno está solicitando a questão '{query}' de uma prova como ENEM ou vestibular. 
        Tente reproduzir a questão completa (enunciado + alternativas), indique a alternativa correta e escreva um breve comentário justificando a resposta.
        Se não for possível localizar exatamente, responda com um exemplo semelhante com base no tema implícito da questão.
        """
        response = model.send_content(FakeContent([Part(prompt)]))
        return response["text"] if isinstance(response, dict) and "text" in response else str(response)

class AgenteGerenteEstudo(Agent):
    def __init__(self, professor, duvidas, quiz, pesquisador, provas, name="Agente_Gerente_Estudo"):
        super().__init__(
            name=name,
            description="Coordena os agentes educacionais.",
            instruction="Encaminha a solicitação do aluno ao agente certo.",
            model="gemini-1.5-pro",
            tools=[],
        )
        self._agents = {
            "professor": professor,
            "duvidas": duvidas,
            "quiz": quiz,
            "pesquisador": pesquisador,
            "provas": provas
        }

    def process_student_request(self, request: str) -> str:
        lower = request.lower()

        if self._agents["quiz"]._current_quiz and self._agents["quiz"]._current_index < len(self._agents["quiz"]._current_quiz["questions"]):
            return self._agents["quiz"].submit_answer(request.strip())

        if any(k in lower for k in ["estudar", "aprender", "resumo", "ensinar"]):
            match = re.search(r"sobre\s+(.*)", lower)
            topic = match.group(1).strip() if match else ""
            return self._agents["professor"].process_query(topic) if topic else "Especifique o tópico."

        if any(k in lower for k in ["dúvida", "não entendi", "exercício"]):
            doubt = re.sub(r".*sobre\s+", "", lower).strip()
            return self._agents["duvidas"].process_query(doubt) if doubt else "Qual é sua dúvida?"

        if "quiz" in lower or "testar" in lower or "avaliar" in lower:
            topic = re.sub(r".*(quiz|testa|avaliar)\s+(sobre|de)?\s*", "", lower).strip()
            return self._agents["quiz"].create_quiz(topic) if topic else "Sobre qual tema deseja o quiz?"

        if "pesquisar" in lower or "aprofundar" in lower or "mais sobre" in lower:
            query = re.sub(r".*(pesquisar|aprofundar|mais sobre)\s+", "", lower).strip()
            return self._agents["pesquisador"].process_query(query) if query else "O que deseja pesquisar?"
        
        if re.search(r"(quest[aã]o\s+\d+.*(enem|fuvest|unicamp|uel|unesp|vestibular))", lower):
            return self._agents["provas"].process_query(request)

        return "Posso te ensinar, tirar dúvidas, testar com quizzes ou pesquisar. Como posso ajudar?"

def main():
    professor = AgenteProfessor()
    duvidas = AgenteTirarDuvidas()
    quiz = AgenteQuizzes()
    pesquisador = AgentePesquisador()
    provas = AgenteBuscarQuestaoProva()
    gerente = AgenteGerenteEstudo(professor, duvidas, quiz, pesquisador, provas)

    print("--- Bem-vindo ao Tutor Inteligente Multiagente! ---")
    print("Eu sou o TUIN, no que posso ajudar?")
    print("Digite 'sair' para encerrar.")

    while True:
        user_input = input("\nAluno: ")
        if user_input.lower() == 'sair':
            print("Tutor: Até a próxima!")
            break

        try:
            response = gerente.process_student_request(user_input)
        except Exception as e:
            response = f"Erro ao processar a solicitação: {str(e)}"

        print(f"Tutor: {response}")

if __name__ == "__main__":
    main()