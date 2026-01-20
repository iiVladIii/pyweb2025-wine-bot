def split_long_message(text: str, max_length: int = 4000) -> list:
    """Разбивает длинное сообщение на части для Telegram (лимит 4096 символов)"""
    if len(text) <= max_length:
        return [text]

    parts = []
    current_part = ""

    paragraphs = text.split('\n\n')

    for paragraph in paragraphs:
        if len(current_part) + len(paragraph) + 2 > max_length:
            if current_part:
                parts.append(current_part.strip())
                current_part = ""

            if len(paragraph) > max_length:
                lines = paragraph.split('\n')
                for line in lines:
                    if len(current_part) + len(line) + 1 > max_length:
                        if current_part:
                            parts.append(current_part.strip())
                        current_part = line + "\n"
                    else:
                        current_part += line + "\n"
            else:
                current_part = paragraph + "\n\n"
        else:
            current_part += paragraph + "\n\n"

    if current_part.strip():
        parts.append(current_part.strip())

    return parts if parts else [text[:max_length]]

def format_search_results(docs: list, doc_type: str = "wine") -> str:
    """Форматирование результатов поиска"""
    if not docs:
        return "Ничего не найдено"

    result = []
    for i, doc in enumerate(docs, 1):
        name = doc.metadata.get('name', f'{doc_type.capitalize()} {i}')
        content = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content

        result.append(f"**{i}. {name}**\n{content}\n")

    return "\n".join(result)
