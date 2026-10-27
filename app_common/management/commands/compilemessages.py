import os
import shutil
import struct
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand


def po_to_mo(po_content: str) -> bytes:
    """
    Convierte el contenido en formato gettext .po a bytes en formato binario .mo.
    Implementación en Python puro sin dependencias externas de GNU gettext.
    """
    entries: dict[str, str] = {}
    current_id: str | None = None
    current_str: str | None = None
    state: str | None = None

    for raw_line in po_content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("msgid "):
            if current_id is not None and current_str is not None:
                entries[current_id] = current_str
            current_id = eval(line[6:].strip())
            current_str = None
            state = "id"
        elif line.startswith("msgstr "):
            current_str = eval(line[7:].strip())
            state = "str"
        elif line.startswith('"') and line.endswith('"'):
            val = eval(line)
            if state == "id" and current_id is not None:
                current_id += val
            elif state == "str" and current_str is not None:
                current_str += val

    if current_id is not None and current_str is not None:
        entries[current_id] = current_str

    keys = sorted(entries.keys())
    n = len(keys)
    orig_table_offset = 28
    trans_table_offset = orig_table_offset + 8 * n
    strings_offset = trans_table_offset + 8 * n

    orig_table: list[tuple[int, int]] = []
    trans_table: list[tuple[int, int]] = []
    orig_strings = b""
    trans_strings = b""

    for k in keys:
        kb = k.encode("utf-8") + b"\x00"
        orig_table.append((len(kb) - 1, strings_offset + len(orig_strings)))
        orig_strings += kb

    trans_strings_offset = strings_offset + len(orig_strings)
    for k in keys:
        v = entries[k]
        vb = v.encode("utf-8") + b"\x00"
        trans_table.append((len(vb) - 1, trans_strings_offset + len(trans_strings)))
        trans_strings += vb

    output = bytearray(
        struct.pack(
            "Iiiiiii",
            0x950412DE,
            0,
            n,
            orig_table_offset,
            trans_table_offset,
            0,
            trans_strings_offset + len(trans_strings),
        )
    )

    for length, offset in orig_table:
        output.extend(struct.pack("ii", length, offset))
    for length, offset in trans_table:
        output.extend(struct.pack("ii", length, offset))

    output.extend(orig_strings)
    output.extend(trans_strings)
    return bytes(output)


class Command(BaseCommand):
    help = (
        "Compila archivos .po a .mo para traducciones i18n "
        "(utiliza compilador en Python puro si msgfmt no está disponible)."
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--locale",
            "-l",
            dest="locale",
            action="append",
            help="El código de idioma a compilar (ej: es, en).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        selected_locales = options.get("locale")
        base_project_dir = getattr(settings, "BASE_DIR", Path.cwd())
        locale_paths: list[Path] = [Path(p) for p in getattr(settings, "LOCALE_PATHS", [])]

        # También incluir locales dentro de aplicaciones locales del proyecto
        # (excluyendo entornos virtuales y site-packages)
        for app in getattr(settings, "INSTALLED_APPS", []):
            try:
                mod = __import__(app, fromlist=["__path__"])
                app_dir = Path(mod.__file__).parent if mod.__file__ else None
                if app_dir and app_dir.is_relative_to(base_project_dir):
                    app_dir_str = str(app_dir)
                    if ".venv" in app_dir_str or "site-packages" in app_dir_str:
                        continue
                    app_locale = app_dir / "locale"
                    if app_locale.exists() and app_locale not in locale_paths:
                        locale_paths.append(app_locale)
            except Exception:
                continue

        compiled_count = 0
        has_msgfmt = shutil.which("msgfmt") is not None

        for base_dir in locale_paths:
            if not base_dir.exists():
                continue

            for root, _, files in os.walk(base_dir):
                for file in files:
                    if not file.endswith(".po"):
                        continue

                    po_path = Path(root) / file
                    parts = po_path.parts
                    locale_name = parts[-3] if len(parts) >= 3 else ""

                    if selected_locales and locale_name not in selected_locales:
                        continue

                    mo_path = po_path.with_suffix(".mo")

                    # Si msgfmt de GNU está disponible en el sistema, lo intentamos usar
                    if has_msgfmt:
                        res = os.system(f'msgfmt -o "{mo_path}" "{po_path}"')
                        if res == 0:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Procesando archivo {po_path} en {mo_path} (msgfmt)"
                                )
                            )
                            compiled_count += 1
                            continue

                    # Compilación nativa en Python puro (robusta en Windows sin gettext)
                    try:
                        content = po_path.read_text(encoding="utf-8")
                        mo_bytes = po_to_mo(content)
                        mo_path.write_bytes(mo_bytes)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Procesando archivo {po_path} en {mo_path} (pure-python)"
                            )
                        )
                        compiled_count += 1
                    except Exception as e:
                        self.stderr.write(
                            self.style.ERROR(f"Error compilando {po_path} a {mo_path}: {e}")
                        )

        if compiled_count == 0:
            self.stdout.write(self.style.WARNING("No se encontraron archivos .po para compilar."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Compilación completada: {compiled_count} archivo(s) .mo generado(s)."
                )
            )
