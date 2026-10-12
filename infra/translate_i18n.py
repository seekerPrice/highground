"""One-off configured Vertex generation; never imported by runtime rendering."""
import asyncio
import json
from pathlib import Path
import sys

from typing import Literal
from pydantic import ConfigDict, create_model

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.config import load_settings
from api.i18n import ROOT, LANGUAGES, validate_catalog
from api.tools.gemini import create_vertex_client, generate_structured


async def run(languages: list[str]) -> None:
    for language in languages:
        if language not in LANGUAGES or language == "en":
            raise ValueError("Choose a supported non-English language")
        target = ROOT / f"{language}.json"
        if target.exists() and json.loads(target.read_text()).get("_reviewed") is True:
            raise ValueError("Refusing to overwrite a reviewed translation")
    source = json.loads((ROOT / "en.json").read_text())
    strings = {key: value for key, value in source.items() if not key.startswith("_")}
    settings = load_settings()
    client = create_vertex_client(settings)
    try:
        for language in languages:
            if language not in LANGUAGES or language == "en":
                raise ValueError("Choose a supported non-English language")
            target = ROOT / f"{language}.json"
            if target.exists() and json.loads(target.read_text()).get("_reviewed") is True:
                raise ValueError("Refusing to overwrite a reviewed translation")
            existing = json.loads(target.read_text()) if target.exists() else {}
            pending = {key: value for key, value in strings.items() if key not in existing} or strings
            string_schema = create_model("TranslatedStrings", __config__=ConfigDict(extra="forbid"), **{key: (str, ...) for key in pending})
            schema = create_model("Translation", __config__=ConfigDict(extra="forbid"), language=(Literal[language], ...), strings=(string_schema, ...))
            result = await generate_structured(
                client=client, model=settings.gemini_fast_model, schema=schema,
                max_output_tokens=8192, timeout_seconds=60,
                prompt=f"Translate this complete English UI dictionary to language code {language}. Return language and strings. Preserve EVERY key and exact {{placeholders}} including their names. Do not add facts/advice. Preserve safety imperatives and 999. Keep the word SIMULATION as a clear translated label. No Markdown wrappers. Dictionary: " + json.dumps(pending, ensure_ascii=False),
            )
            translated = result.strings.model_dump()
            if result.language != language or set(translated) != set(pending):
                raise ValueError("Generated language/keys mismatch")
            data = {**existing, "_language": language, "_reviewed": False, **translated}
            # Assemble all four STATIC variants now; runtime never adds notices.
            for suffix in ("destination", "no_destination"):
                core = data[f"danger_{suffix}"]
                notice = data["translation_notice"]
                core = core.removeprefix(notice + "\n").removesuffix("\n" + notice)
                if notice in core:
                    raise ValueError("Unexpected review notice inside translated core")
                data[f"danger_{suffix}"] = notice + "\n" + core
                data[f"danger_sim_{suffix}"] = data["simulation_label"] + "\n" + notice + "\n" + core
            validate_catalog(data, language, source)
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            temporary.replace(target)
            print(f"Generated {language}; native-speaker review pending", flush=True)
    finally:
        await client.aio.aclose()
        client.close()


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:] or list(LANGUAGES[1:])))
