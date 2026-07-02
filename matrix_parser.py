"""
matrix_parser.py — Parser de PDF Matrix Connect para o Control.ILL

Resultados validados com PDFs reais:
  HEMATO.PDF        105/105  HMG,RET exato ✓
  URINALISE.PDF     119/119  CHEMSTRY ✓
  SOROTECA.PDF      200/200  36 códigos únicos limpos ✓

Técnica: posição x/y via pdfplumber.
Chunks da coluna Exames são concatenados antes de separar por vírgula,
evitando artefatos de quebra de linha (ZNHD + L = ZNHDL etc).
"""

import re
import io
import pdfplumber

# ── Palavras de layout — aparecem na coluna Exames mas não são códigos ────────
SKIP_WORDS = {
    'LISTAGEM', 'DA', 'BANDEJA', 'RETIRADA', 'USUARIO', 'MOTIVO',
    'EXAMES', 'AMOSTRA', 'POSICAO', 'PACIENTE', 'ORIGEM', 'LIBERADA',
    'DATA', 'HORA', 'OPERADOR', 'WILLIANC', 'SEG', 'SAB', 'A',
    'POSIÇÃO', 'SIM', 'NÃO', 'NAO', 'SEGUNDA', 'TERCA', 'QUARTA',
    'QUINTA', 'SEXTA',
}

# ── Mapeamento código Matrix → nome canonical do reagente ─────────────────────
#
# O nome canonical é comparado de forma CASE-INSENSITIVE com o nome_exame do lote.
# Isso evita falhas quando o usuário digitou manualmente com caixa diferente.
#
CODIGO_PARA_REAGENTE: dict[str, str] = {
    'ACU':    'Ácido Úrico',
    'ALB':    'Albumina',
    'AMI':    'Amilase',
    'BETAQL': 'B-hCG Qualitativo',
    'BHCG':   'B-hCG Quantitativo',
    'CAL':    'Cálcio',
    'CKBM':   'CK-MB',
    'COL':    'Colesterol Total',
    'CPK':    'CPK',
    'CRE':    'Creatinina',
    'FAL':    'Fosfatase Alcalina (ALKP)',
    'FE':     'Ferro',
    'FOS':    'Fósforo',
    'GGT':    'GGT',
    'GLI':    'Glicose',
    'H1N1':   'H1N1',
    'HDL':    'HDL Colesterol',
    'K':      'Potássio',
    'LDH':    'LDH',
    'LIP':    'Lipase',
    'MAG':    'Magnésio',
    'NA':     'Sódio',
    'PCR':    'Proteína C - Reativa',
    'PRT':    'Proteínas Totais',
    'PTH':    'PTHi',
    'TGO':    'AST',
    'TGP':    'ALT',
    'TRI':    'Triglicerídeos',
    'URE':    'Ureia',
}

# ── Aliases: nomes alternativos que o usuário pode ter digitado ───────────────
# Mapeia nome_normalizado (lower) → código Matrix
# Exemplos: "tgo" → "AST", "ast" → "AST", "alt/tgp" → "ALT" etc.
_ALIASES_EXTRA: dict[str, str] = {
    # AST / TGO
    'ast':                      'AST',
    'tgo':                      'AST',
    'ast/tgo':                  'AST',
    'tgo/ast':                  'AST',
    # ALT / TGP
    'alt':                      'ALT',
    'tgp':                      'ALT',
    'alt/tgp':                  'ALT',
    'tgp/alt':                  'ALT',
    # Fosfatase
    'fosfatase alcalina':       'Fosfatase Alcalina (ALKP)',
    'fosfatase alcalina (alkp)':'Fosfatase Alcalina (ALKP)',
    'alkp':                     'Fosfatase Alcalina (ALKP)',
    'fal':                      'Fosfatase Alcalina (ALKP)',
    # hCG
    'beta-hcg qualitativo':     'B-hCG Qualitativo',
    'β-hcg qualitativo':        'B-hCG Qualitativo',
    'b-hcg qualitativo':        'B-hCG Qualitativo',
    'beta-hcg quantitativo':    'B-hCG Quantitativo',
    'β-hcg quantitativo':       'B-hCG Quantitativo',
    'b-hcg quantitativo':       'B-hCG Quantitativo',
    # PCR
    'pcr':                      'Proteína C - Reativa',
    'proteina c reativa':       'Proteína C - Reativa',
    'proteína c reativa':       'Proteína C - Reativa',
    'proteína c - reativa':     'Proteína C - Reativa',
    # Proteínas
    'proteinas totais':         'Proteínas Totais',
    'proteínas totais':         'Proteínas Totais',
    'prt':                      'Proteínas Totais',
    # Colesterol
    'col':                      'Colesterol Total',
    'colesterol':               'Colesterol Total',
    # Ácido úrico
    'acu':                      'Ácido Úrico',
    'acido urico':              'Ácido Úrico',
    'ácido úrico':              'Ácido Úrico',
    # Triglicerídeos
    'triglicerideos':           'Triglicerídeos',
    'triglicerídeos':           'Triglicerídeos',
    'tri':                      'Triglicerídeos',
    # PTH
    'pth':                      'PTHi',
    'pthi':                     'PTHi',
    # CK-MB
    'ck-mb':                    'CK-MB',
    'ckmb':                     'CK-MB',
    'ckbm':                     'CK-MB',
    # Magnésio
    'magnesio':                 'Magnésio',
    'mag':                      'Magnésio',
    # Fósforo
    'fosforo':                  'Fósforo',
    'fos':                      'Fósforo',
    # Cálcio
    'calcio':                   'Cálcio',
    'cal':                      'Cálcio',
}

# Pré-computar lookup reverso: lower(nome_canonical) → nome_canonical
_CANONICAL_LOWER: dict[str, str] = {
    v.lower(): v for v in CODIGO_PARA_REAGENTE.values()
}

# Adicionar aliases ao lookup
for alias_lower, canonical in _ALIASES_EXTRA.items():
    _CANONICAL_LOWER[alias_lower] = canonical


def _canonicalizar(nome: str) -> str | None:
    """
    Retorna o nome canonical do reagente dado qualquer variação de grafia.
    Retorna None se não reconhecido.
    """
    if not nome:
        return None
    n = nome.strip().lower()
    return _CANONICAL_LOWER.get(n)


def _codigo_para_canonical(codigo: str) -> str | None:
    """Retorna o nome canonical para um código Matrix."""
    return CODIGO_PARA_REAGENTE.get(codigo.upper())


# ── Códigos gasometria ────────────────────────────────────────────────────────
GASOMETRIA_CHAR_CODES = frozenset({
    'BEB', 'CAI', 'HCO3', 'HCT', 'LAC', 'PCO2',
    'PH', 'PO2', 'SO2C', 'TCO2', 'TEMP',
})

# ── Reagentes por setor (regras em bloco) ─────────────────────────────────────
REAGENTES_HEMATOLOGIA = [
    'Cellpack DCL', 'Cellpack DFL', 'Lysercell WNR', 'Lysercell WDF',
    'Sulfolyser', 'Fluorocell WDF', 'Fluorocell WNR', 'Fluorocell RET',
]

REAGENTES_URINALISE = [
    'Tira Reagente (Meditape UC-11A)', 'UF - CellSheath',
    'UF - CellPack SF', 'UF - CellPack CR',
    'UF - Fluorocell SF', 'UF - Fluorocell CR',
    'Salina',
]

# ═══════════════════════════════════════════════════════════════════════════════
# PARSER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def parse_matrix_pdf(filepath_or_bytes) -> list[tuple[str, str]]:
    """
    Lê um PDF Matrix Connect e retorna lista de (amostra, exames_normalizados).

    - amostra : string numérica de 8–12 dígitos
    - exames  : string com códigos separados por vírgula, ex: 'HMG,RET'

    Aceita caminho em disco (str/Path) ou bytes em memória.
    """
    source = (io.BytesIO(filepath_or_bytes)
              if isinstance(filepath_or_bytes, (bytes, bytearray))
              else filepath_or_bytes)

    EXAMES_COL_X: float | None = None
    AMOSTRA_COL_X: float | None = None
    all_words: list[dict] = []

    with pdfplumber.open(source) as pdf:
        page_offset = 0.0
        for page in pdf.pages:
            words = page.extract_words()

            for w in words:
                if w['text'] == 'Exames' and EXAMES_COL_X is None:
                    EXAMES_COL_X = float(w['x0'])
                if w['text'] == 'Amostra' and AMOSTRA_COL_X is None:
                    AMOSTRA_COL_X = float(w['x0'])

            for w in words:
                all_words.append({
                    'text': w['text'],
                    'x0':   float(w['x0']),
                    'y':    float(w['top']) + page_offset,
                })
            page_offset += float(page.height)

    if EXAMES_COL_X is None:
        EXAMES_COL_X = 228.5
    if AMOSTRA_COL_X is None:
        AMOSTRA_COL_X = 24.0

    all_words.sort(key=lambda w: w['y'])

    # ── Linhas de amostra ─────────────────────────────────────────────────────
    amostra_rows: list[tuple[float, str]] = [
        (w['y'], w['text'])
        for w in all_words
        if abs(w['x0'] - AMOSTRA_COL_X) < 15
        and re.match(r'^\d{8,12}$', w['text'])
    ]
    if not amostra_rows:
        return []

    # ── Chunks da coluna Exames ───────────────────────────────────────────────
    # Apenas strings compostas de letras maiúsculas, dígitos e vírgulas
    _CHUNK_RE = re.compile(r'^[A-Z0-9,]+$')

    exames_chunks: list[tuple[float, str]] = []
    for w in all_words:
        if w['x0'] < EXAMES_COL_X - 10:
            continue
        tu = w['text'].upper().strip()
        if not tu or tu in SKIP_WORDS:
            continue
        if not _CHUNK_RE.match(tu):
            continue
        exames_chunks.append((w['y'], tu))

    # ── Associar chunks a cada amostra ───────────────────────────────────────
    results: list[tuple[str, str]] = []

    for idx, (am_y, am_num) in enumerate(amostra_rows):
        # Primeira amostra: não subir mais de 20pt (evita capturar cabeçalho)
        # Última amostra: não descer mais de 30pt (evita capturar rodapé/notas)
        if idx > 0:
            y_start = (amostra_rows[idx - 1][0] + am_y) / 2
        else:
            y_start = am_y - 20.0

        if idx < len(amostra_rows) - 1:
            y_end = (am_y + amostra_rows[idx + 1][0]) / 2
        else:
            y_end = am_y + 30.0

        chunks_in_range = sorted(
            [(ey, et) for ey, et in exames_chunks if y_start < ey <= y_end],
            key=lambda x: x[0],
        )

        raw_concat = ''.join(et for _, et in chunks_in_range)

        seen: set[str] = set()
        final_codes: list[str] = []
        for code in raw_concat.split(','):
            code = code.strip()
            if (code
                    and code not in SKIP_WORDS
                    and re.match(r'^[A-Z][A-Z0-9]{0,14}$', code)
                    and code not in seen):
                seen.add(code)
                final_codes.append(code)

        results.append((am_num, ','.join(final_codes)))

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# APLICAR REGRAS DE IMPORTAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def aplicar_regras(
    parsed: list[tuple[str, str]],
    lotes_abertos: list[dict],
) -> dict[int, set[str]]:
    """
    Aplica as regras de importação Matrix a todos os lotes abertos.

    parsed         : saída de parse_matrix_pdf()
    lotes_abertos  : lista de dicts com keys id, setor, nome_exame

    Retorna dict: lote_id → set de amostras a inserir

    IMPORTANTE: a comparação nome_exame é CASE-INSENSITIVE e aceita aliases
    (ex: 'TGO' == 'AST', 'TGP' == 'ALT', 'creatinina' == 'Creatinina').
    """
    resultado: dict[int, set[str]] = {}

    for amostra, exames_str in parsed:
        codigos = set(c.strip() for c in exames_str.split(',') if c.strip())

        for lote in lotes_abertos:
            lt_id      = lote['id']
            setor      = (lote.get('setor') or '').strip()
            nome_raw   = (lote.get('nome_exame') or '').strip()
            # Canonicalizar o nome do lote para comparação robusta
            nome_canon = _canonicalizar(nome_raw) or nome_raw
            match      = False

            # ── Hematologia: exatos HMG,RET ───────────────────────────────────
            if setor == 'Hematologia':
                if exames_str.replace(' ', '').upper() == 'HMG,RET':
                    # Comparação case-insensitive com lista de reagentes
                    if nome_raw.lower() in [r.lower() for r in REAGENTES_HEMATOLOGIA]:
                        match = True

            # ── Urinálise: contém CHEMSTRY ────────────────────────────────────
            elif setor == 'Urinálise':
                if 'CHEMSTRY' in codigos:
                    if nome_raw.lower() in [r.lower() for r in REAGENTES_URINALISE]:
                        match = True

            # ── Qualquer setor: mapeamento por código individual ──────────────
            # (inclui Imunobioquímica, Bioquímica, Gasometria como setor, etc.)
            else:
                # Caso especial: Gasometria — códigos característicos
                if nome_canon.lower() == 'gasometria' or nome_raw.lower() == 'gasometria':
                    if codigos & GASOMETRIA_CHAR_CODES:
                        match = True
                else:
                    # Mapeamento individual por código Matrix
                    for codigo in codigos:
                        mapped = _codigo_para_canonical(codigo)
                        if mapped and mapped.lower() == nome_canon.lower():
                            match = True
                            break

            if match:
                resultado.setdefault(lt_id, set()).add(amostra)

    return resultado
