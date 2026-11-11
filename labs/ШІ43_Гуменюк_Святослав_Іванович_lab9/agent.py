import json

import groq

from tools import TOOL_SCHEMAS, run_tool

MODEL = "openai/gpt-oss-120b"
MAX_TOOL_ROUNDS = 10
TEMPERATURE = 0.5
SUBMIT_ANSWER_TOOL = "submit_answer"

SUBMIT_ANSWER_SCHEMA = {
    "type": "function",
    "function": {
        "name": SUBMIT_ANSWER_TOOL,
        "description": "Фінальна відповідь користувачу. Викликай її один раз, коли даних достатньо.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer_text": {"type": "string", "description": "Вільна відповідь на питання у 2-4 реченнях"},
                "key_facts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 4,
                    "description": "Ключові факти з конкретними даними з інструментів, на яких ґрунтується відповідь",
                },
            },
            "required": ["answer_text", "key_facts"],
        },
    },
}

FORCE_ANSWER = {"type": "function", "function": {"name": SUBMIT_ANSWER_TOOL}}

SYSTEM_PROMPT = """Ти — Радник, космічно логічна система, що передбачає найтонші події світу. Користувач ставить питання вільним текстом.
Правила:
- Сам вирішуй, які дані потрібні для відповіді, і викликай відповідні інструменти. Не викликай зайвих: для різних питань потрібні різні джерела.
- Якщо інструмент повернув помилку, не вигадуй дані: чесно скажи в ключових фактах, яких даних бракує.
- Коли даних достатньо, виклич {answer_tool}. Відповідь і ключові факти мають спиратися на конкретні значення з інструментів.
- Відповідай українською, з легким гумором, але по суті.
- Ніколи не згадуй у відповіді й фактах назви інструментів, функцій чи API (get_weather, get_moon_phase тощо). Подавай самі дані як власні знамення: «зараз у Києві 3 °C», а не «за даними get_weather».
- Місто користувача: {city}."""


def ask_model(client, messages, tool_choice):
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS + [SUBMIT_ANSWER_SCHEMA],
        tool_choice=tool_choice,
        temperature=TEMPERATURE,
    ).choices[0].message


def execute_tool_call(call):
    arguments = json.loads(call.function.arguments)

    return {
        "tool": call.function.name,
        "arguments": arguments,
        "result": run_tool(call.function.name, arguments),
    }


def run_agent(question: str, city: str, api_key: str) -> tuple[dict, list[dict]]:
    client = groq.Groq(api_key=api_key)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(city=city, answer_tool=SUBMIT_ANSWER_TOOL)},
        {"role": "user", "content": question},
    ]
    trace = []

    for _ in range(MAX_TOOL_ROUNDS):
        message = ask_model(client, messages, tool_choice="auto")
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            break

        for call in message.tool_calls:
            if call.function.name == SUBMIT_ANSWER_TOOL:
                return json.loads(call.function.arguments), trace

            tool_call = execute_tool_call(call)
            trace.append(tool_call)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(tool_call["result"], ensure_ascii=False),
            })

    final_message = ask_model(client, messages, tool_choice=FORCE_ANSWER)

    return json.loads(final_message.tool_calls[0].function.arguments), trace
