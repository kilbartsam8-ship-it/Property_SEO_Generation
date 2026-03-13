from groq import Groq


def generate_seo_markdown(client: Groq, model: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    content = response.choices[0].message.content
    if content is None:
        return ""
    if not isinstance(content, str):
        return str(content)
    return content
