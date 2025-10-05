# Código que usei — copie/cole em seu ambiente Python (requer pdfplumber ou PyPDF2)
import re
from pathlib import Path
import pandas as pd

pdf_path = Path(
    "D:/Fatec/PI6/Balancetes/histórico/pgprev/202507_P&G_BALANCETE_CONSOLIDADO.pdf")
output_csv = Path(
    "C:/Users/guilh/Desktop/Trabalhos/PI6/balancetes/pgprev/202507_balancete_parsed.csv")


def to_float(num_str):
    s = num_str.strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def parse_text_lines(lines):
    rows = []
    pattern = re.compile(
        r'^(?P<conta>/d{4,})\s+'
        r'(?P<nome>.+?)\s+'
        r'(?P<sld_inicial>[-\d\.\,]+)\s+'
        r'(?P<nat1>DV|CR)\s+'
        r'(?P<debito>[-\d\.\,]+)\s+'
        r'(?P<credito>[-\d\.\,]+)\s+'
        r'(?P<sld_final>[-\d\.\,]+)\s+'
        r'(?P<nat2>DV|CR)$'
    )
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        m = pattern.match(ln)
        if m:
            d = m.groupdict()
            rows.append({
                "conta": d["conta"],
                "nome": d["nome"].strip(),
                "sld_inicial_raw": d["sld_inicial"],
                "nat_inicio": d["nat1"],
                "debito_raw": d["debito"],
                "credito_raw": d["credito"],
                "sld_final_raw": d["sld_final"],
                "nat_final": d["nat2"],
                "sld_inicial": to_float(d["sld_inicial"]),
                "debito": to_float(d["debito"]),
                "credito": to_float(d["credito"]),
                "sld_final": to_float(d["sld_final"])
            })
        else:
            if re.match(r'^\d{4,}', ln):
                tokens = ln.split()
                if len(tokens) >= 7:
                    last6 = tokens[-6:]
                    try:
                        sld_inicial_raw, nat1, debito_raw, credito_raw, sld_final_raw, nat2 = last6
                        nome = " ".join(tokens[1:-6])
                        rows.append({
                            "conta": tokens[0],
                            "nome": nome.strip(),
                            "sld_inicial_raw": sld_inicial_raw,
                            "nat_inicio": nat1,
                            "debito_raw": debito_raw,
                            "credito_raw": credito_raw,
                            "sld_final_raw": sld_final_raw,
                            "nat_final": nat2,
                            "sld_inicial": to_float(sld_inicial_raw),
                            "debito": to_float(debito_raw),
                            "credito": to_float(credito_raw),
                            "sld_final": to_float(sld_final_raw)
                        })
                    except Exception:
                        pass
    return rows


# tentativa com pdfplumber, fallback PyPDF2
extracted_lines = []
method_used = None
try:
    import pdfplumber
    method_used = "pdfplumber"
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_lines.extend(text.split("\n"))
except Exception:
    try:
        from PyPDF2 import PdfReader
        method_used = "PyPDF2"
        reader = PdfReader(str(pdf_path))
        for p in reader.pages:
            txt = p.extract_text() or ""
            extracted_lines.extend(txt.split("\n"))
    except Exception:
        raise RuntimeError(
            "Nenhuma biblioteca disponível para extrair texto de PDF (pdfplumber/PyPDF2).")

rows = parse_text_lines(extracted_lines)
df = pd.DataFrame(rows, columns=[
    "conta", "nome", "sld_inicial_raw", "nat_inicio", "debito_raw", "credito_raw", "sld_final_raw", "nat_final",
    "sld_inicial", "debito", "credito", "sld_final"
])
df.to_csv(output_csv, index=False, encoding="utf-8-sig")
print(
    f"Extração usando: {method_used}. Linhas extraídas: {len(extracted_lines)}. Registros detectados: {len(df)}")
print(output_csv)
