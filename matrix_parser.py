"""
matrix_parser.py — Control.ILL
Parser de PDF Matrix Connect + regras de importação por setor.
"""

import re
import io
import pdfplumber

# ── Palavras de layout — não são códigos de exame ─────────────────────────────
SKIP_WORDS = {
    'LISTAGEM', 'DA', 'BANDEJA', 'RETIRADA', 'USUARIO', 'MOTIVO',
    'EXAMES', 'AMOSTRA', 'POSICAO', 'PACIENTE', 'ORIGEM', 'LIBERADA',
    'DATA', 'HORA', 'OPERADOR', 'WILLIANC', 'SEG', 'SAB', 'A',
    'POSIÇÃO', 'SIM', 'NÃO', 'NAO', 'SEGUNDA', 'TERCA', 'QUARTA',
    'QUINTA', 'SEXTA',
}

# ── Mapeamento código Matrix → nome canonical do reagente ─────────────────────
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
    'VDRL':   'VDRL',          # ← VDRL aparece como VDRL no PDF
    'BETAQL': 'B-hCG Qualitativo',
    'BHCG':   'B-hCG Quantitativo',
    'TROQN':  'Troponina Qualitativa',
    'PROCAL': 'Procalcitonina',
    'PROBNP': 'PRO-BNP-NT',
    'DIMERO': 'Dímero-D',
    'HIV':    'HIV Teste Rápido',
    'COVID':  'COVIDAg',
    'NS1':    'NS1',
    'PTHi':   'PTHi',
    'VANC':   'Vancomicina',
}

# ── Aliases: nomes alternativos que o usuário pode ter digitado ───────────────
_ALIASES_EXTRA: dict[str, str] = {
    'ast':                       'AST',
    'tgo':                       'AST',
    'ast/tgo':                   'AST',
    'tgo/ast':                   'AST',
    'alt':                       'ALT',
    'tgp':                       'ALT',
    'alt/tgp':                   'ALT',
    'tgp/alt':                   'ALT',
    'fosfatase alcalina':        'Fosfatase Alcalina (ALKP)',
    'fosfatase alcalina (alkp)': 'Fosfatase Alcalina (ALKP)',
    'alkp':                      'Fosfatase Alcalina (ALKP)',
    'fal':                       'Fosfatase Alcalina (ALKP)',
    'beta-hcg qualitativo':      'B-hCG Qualitativo',
    'b-hcg qualitativo':         'B-hCG Qualitativo',
    'beta-hcg quantitativo':     'B-hCG Quantitativo',
    'b-hcg quantitativo':        'B-hCG Quantitativo',
    'pcr':                       'Proteína C - Reativa',
    'proteina c reativa':        'Proteína C - Reativa',
    'proteínas totais':          'Proteínas Totais',
    'proteinas totais':          'Proteínas Totais',
    'prt':                       'Proteínas Totais',
    'col':                       'Colesterol Total',
    'colesterol':                'Colesterol Total',
    'acu':                       'Ácido Úrico',
    'acido urico':               'Ácido Úrico',
    'ácido úrico':               'Ácido Úrico',
    'triglicerideos':            'Triglicerídeos',
    'triglicerídeos':            'Triglicerídeos',
    'tri':                       'Triglicerídeos',
    'pth':                       'PTHi',
    'pthi':                      'PTHi',
    'ck-mb':                     'CK-MB',
    'ckmb':                      'CK-MB',
    'ckbm':                      'CK-MB',
    'magnesio':                  'Magnésio',
    'magnésio':                  'Magnésio',
    'mag':                       'Magnésio',
    'fosforo':                   'Fósforo',
    'fósforo':                   'Fósforo',
    'fos':                       'Fósforo',
    'calcio':                    'Cálcio',
    'cálcio':                    'Cálcio',
    'cal':                       'Cálcio',
    'vdrl':                      'VDRL',
}

# Lookup reverso: lower(nome) → nome canonical
_CANONICAL_LOWER: dict[str, str] = {
    v.lower(): v for v in CODIGO_PARA_REAGENTE.values()
}
for alias_lower, canonical in _ALIASES_EXTRA.items():
    _CANONICAL_LOWER[alias_lower] = canonical


def _canonicalizar(nome: str):
    if not nome:
        return None
    return _CANONICAL_LOWER.get(nome.strip().lower())


def _codigo_para_canonical(codigo: str):
    return CODIGO_PARA_REAGENTE.get(codigo.upper())


# ── Gasometria ────────────────────────────────────────────────────────────────
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
# PARSER
# ═══════════════════════════════════════════════════════════════════════════════

def parse_matrix_pdf(filepath_or_bytes) -> list[tuple[str, str]]:
    """
    Lê PDF Matrix Connect e retorna lista de (amostra, exames_normalizados).
    Aceita caminho em disco ou bytes em memória.
    """
    source = (io.BytesIO(filepath_or_bytes)
              if isinstance(filepath_or_bytes, (bytes, bytearray))
              else filepath_or_bytes)

    EXAMES_COL_X = None
    AMOSTRA_COL_X = None
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

    # Linhas de amostra
    amostra_rows = [
        (w['y'], w['text'])
        for w in all_words
        if abs(w['x0'] - AMOSTRA_COL_X) < 15
        and re.match(r'^\d{8,12}$', w['text'])
    ]
    if not amostra_rows:
        return []

    # Chunks da coluna Exames (apenas letras maiúsculas, dígitos e vírgulas)
    _CHUNK_RE = re.compile(r'^[A-Z0-9,]+$')
    exames_chunks = []
    for w in all_words:
        if w['x0'] < EXAMES_COL_X - 10:
            continue
        tu = w['text'].upper().strip()
        if not tu or tu in SKIP_WORDS:
            continue
        if not _CHUNK_RE.match(tu):
            continue
        exames_chunks.append((w['y'], tu))

    # Associar chunks a cada amostra
    results = []
    for idx, (am_y, am_num) in enumerate(amostra_rows):
        y_start = (amostra_rows[idx-1][0] + am_y) / 2 if idx > 0 else am_y - 20.0
        y_end   = (am_y + amostra_rows[idx+1][0]) / 2 if idx < len(amostra_rows)-1 else am_y + 30.0

        chunks = sorted(
            [(ey, et) for ey, et in exames_chunks if y_start < ey <= y_end],
            key=lambda x: x[0],
        )

        raw = ''.join(et for _, et in chunks)

        seen: set[str] = set()
        final_codes: list[str] = []
        for code in raw.split(','):
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
# APLICAR REGRAS
# ═══════════════════════════════════════════════════════════════════════════════

def aplicar_regras(
    parsed: list[tuple[str, str]],
    lotes_abertos: list[dict],
) -> dict[int, set[str]]:
    """
    Aplica regras de importação a todos os lotes abertos.
    Retorna dict: lote_id → set de amostras a inserir.
    Comparação de nome_exame é CASE-INSENSITIVE.
    """
    resultado: dict[int, set[str]] = {}

    for amostra, exames_str in parsed:
        codigos = set(c.strip() for c in exames_str.split(',') if c.strip())

        for lote in lotes_abertos:
            lt_id      = lote['id']
            setor      = (lote.get('setor') or '').strip()
            nome_raw   = (lote.get('nome_exame') or '').strip()
            nome_canon = _canonicalizar(nome_raw) or nome_raw
            match      = False

            # ── Hematologia: exato HMG,RET ────────────────────────────────────
            if setor == 'Hematologia':
                if exames_str.replace(' ','').upper() == 'HMG,RET':
                    if nome_raw.lower() in [r.lower() for r in REAGENTES_HEMATOLOGIA]:
                        match = True

            # ── Urinálise: contém CHEMSTRY ────────────────────────────────────
            elif setor == 'Urinálise':
                if 'CHEMSTRY' in codigos:
                    if nome_raw.lower() in [r.lower() for r in REAGENTES_URINALISE]:
                        match = True

            # ── Todos os outros setores: mapeamento por código ─────────────────
            else:
                # Gasometria — códigos característicos
                if nome_canon.lower() in ('gasometria', 'gasometria arterial', 'gasometria venosa'):
                    if codigos & GASOMETRIA_CHAR_CODES:
                        match = True
                else:
                    # Mapeamento individual (Imunobioquímica, Bioquímica, etc.)
                    for codigo in codigos:
                        mapped = _codigo_para_canonical(codigo)
                        if mapped and mapped.lower() == nome_canon.lower():
                            match = True
                            break

            if match:
                resultado.setdefault(lt_id, set()).add(amostra)

    return resultado
