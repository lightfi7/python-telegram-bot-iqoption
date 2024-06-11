import json

with open('./lang/lang.json', 'r', encoding="utf-8") as file:
    translations = json.load(file)


def translate(key, lang='en'):
    text = translations[lang][key]
    text_encode = text
    return text_encode