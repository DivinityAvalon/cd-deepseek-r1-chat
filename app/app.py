import gradio as gr
import requests
import logging
import threading
import time
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder
)
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# URL Ollama API
OLLAMA_API = "http://ollama:11434"

# Проверка подключения к Ollama перед запуском
def test_ollama_connection(retries=3, delay=3):
    for i in range(retries):
        try:
            response = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)
            response.raise_for_status()
            logging.info("✅ Успешное подключение к Ollama")
            return True
        except requests.exceptions.RequestException as e:
            logging.warning(f"❌ Ошибка подключения ({i+1}/{retries}): {e}")
            time.sleep(delay)
    logging.error("🚨 Не удалось подключиться к Ollama после нескольких попыток")
    return False

if not test_ollama_connection():
    exit(1)  # Прерываем запуск, если Ollama недоступен

# Инициализация движка LLM
def get_llm_engine(model_name):
    logging.info(f"🚀 Инициализация модели {model_name}")
    try:
        return ChatOllama(
            model=model_name,
            base_url=OLLAMA_API,
            temperature=0.3
        ) 
    except Exception as e:
        logging.error(f"❌ Ошибка инициализации модели {model_name}: {e}")
        return None

# Настройки системного промпта
SYSTEM_TEMPLATE = """You are an expert AI coding assistant. Provide concise, correct solutions 
with strategic print statements for debugging. Always respond in English."""

chat_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_TEMPLATE),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])
class ChatBot:
    def __init__(self):
        self.chat_history = [
            {"role": "ai", "content": "Hi! I'm DeepSeek. How can I help you code today? 💻"}
        ]

    def generate_ai_response(self, user_input, llm_engine):
        logging.info(f"📝 Отправка запроса в модель: {user_input}")
        self.chat_history.append(HumanMessage(content=user_input))

        chain = chat_prompt | llm_engine | StrOutputParser()
        response = chain.invoke({"input": user_input, "chat_history": self.chat_history}) or "⚠️ Ошибка: модель не вернула ответ."

        self.chat_history.append(AIMessage(content=response))
        logging.info(f"💡 Полный ответ от модели: {response}")

        return response

    def chat(self, message, model_choice, history):
        """Обработка чата в Gradio"""
        if not message:
            return "", history  # Если пустое сообщение, ничего не делаем

        # Инициализация LLM-движка
        llm_engine = get_llm_engine(model_choice)

        # Добавляем сообщение пользователя в историю
        history.append({"role": "user", "content": message})

        # Генерация ответа
        ai_response = self.generate_ai_response(message, llm_engine)

        # Обновляем историю сообщений
        history.append({"role": "ai", "content": ai_response})

        return history, ""  # Чат обновляется первым, поле ввода очищается вторым

    def clear_chat(self):
        """Очистка чата"""
        logging.info("🗑 Очистка истории чата")
        self.chat_history = [
            {"role": "ai", "content": "Hi! I'm DeepSeek. How can I help you code today? 💻"}
        ]
        return "", self.chat_history


def create_demo():
    chatbot = ChatBot()
    
    with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue", neutral_hue="zinc")) as demo:
        gr.Markdown("# 🧠 DeepSeek Code Companion")
        gr.Markdown("🚀 Your AI Pair Programmer with Debugging Superpowers")
            
        with gr.Row():
            with gr.Column(scale=4):
                chatbot_component = gr.Chatbot(
                    value=[{"role": "ai", "content": "Hi! I'm DeepSeek. How can I help you code today? 💻"}],
                    show_copy_button=True,
                    height=500,
                    type="messages"  # Указываем правильный формат
                )
                
                msg = gr.Textbox(
                    placeholder="Type your coding question here...",
                    show_label=False
                )
                
                with gr.Row():
                    send_btn = gr.Button("📩 Send message")  # Кнопка отправки
                    clear_btn = gr.Button("🗑 Clear chat")
                
            with gr.Column(scale=1):
                model_dropdown = gr.Dropdown(
                    choices=["deepseek-r1:1.5b", "deepseek-r1:7b", "deepseek-r1:14b"],
                    value="deepseek-r1:1.5b",
                    label="Choose Model"
                )
                gr.Markdown("### Model Capabilities")
                gr.Markdown("""
                - 🐍 Python Expert
                - 🐞 Debugging Assistant
                - 📝 Code Documentation
                - 💡 Solution Design
                """)
                
                gr.Markdown("Built with [Ollama](https://ollama.ai/) | [LangChain](https://python.langchain.com/)")

        # Обрабатываем ввод сообщений
        msg.submit(
            fn=chatbot.chat,
            inputs=[msg, model_dropdown, chatbot_component],
            outputs=[chatbot_component, msg]  # Чат первым, поле ввода вторым!
        )

        send_btn.click(
            fn=chatbot.chat,
            inputs=[msg, model_dropdown, chatbot_component],
            outputs=[chatbot_component, msg]  # Чат первым, поле ввода вторым!
        )

        # Очистка чата
        clear_btn.click(fn=chatbot.clear_chat, inputs=[], outputs=[msg, chatbot_component], queue=False)

    return demo

if __name__ == "__main__":
    demo = create_demo()
    demo.launch(server_name="0.0.0.0", server_port=7860)