import google.generativeai as genai

import vector
import json
from ticket_manager import DatabaseHandler, clean_history
import schemas

import os

API_KEY = os.getenv("API_KEY")
genai.configure(api_key=API_KEY)

TEMP_CHAT_HISTORY = []


def generate_prompt(query, context):
    with open("prompt.txt", "r") as file:
        prompt = file.read().format(query=query, context=context)

    return prompt


def ask_bot(query, _ticket_name):
    db = DatabaseHandler()

    print('Loading...')
    context = vector.get_similar(query)
    print(context)
    prompt = generate_prompt(query, context)

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            response_mime_type="application/json",
            response_schema=list[schemas.AnswerStructure],
        )
    )

    chat = model.start_chat()

    response = chat.send_message(prompt)
    data = json.loads(response.text)[0]

    print(data)

    _answer = data["answer"]
    _send = bool(data["send"]) if "send" in data.keys() else False

    if _ticket_name:
        db.append_history('history_user', _ticket_name, 'bot', _answer)
    else:
        TEMP_CHAT_HISTORY.append({"role": "bot", "message": _answer})

    return _answer, _send


def generate_subject(history):
    prompt = ("Generate an email subject for an email regarding the following chat history between a chatbot and human."
              "Make sure it is only one line of text with no new lines or carriage return characters. Do not include"
              "anything other than the subject. Don't mention that it is a chatbot referral, only consider the "
              "conversation and its contents. This is the chat history:\n"
              f"{history}")
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=1,
        )
    )
    chat = model.start_chat()
    response = chat.send_message(prompt)

    return response.text.replace('\n', ' ').replace('\r', ' ').strip()


def summarise_solution(ticket_name):
    db = DatabaseHandler()
    subject = db.get_ticket_field(ticket_name, 'subject')
    history = clean_history(db.get_history('history_admin', ticket_name))

    prompt = ("Summarise the following user (called bot) and customer service conversation regarding a certain issue."
              f"This is the subject of their conversation (via email): {subject}. The solution to the problem/question "
              "posed by the user is in this conversation, whether in one specific location, or across the whole "
              "conversation. You need to summarise the solution, and include it in the output. Summarise it in such a "
              "way that the issue/question can be inferred from the solution you provide. Don't make up anything or "
              "use external information, only consider the conversation and its contents. Only write the solution "
              "summary, not what happened in the conversation (like who said what, etc.). This is the chat history:\n"
              f"{history}")
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=1,
        )
    )
    chat = model.start_chat()
    response = chat.send_message(prompt)

    print(response.text)

    return response.text
