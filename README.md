# 🔬 Control.ILL
## Sistema de Registro, Validação e Rastreabilidade de Lotes Laboratoriais

---

## 📁 Arquivos

```
controlill/
├── app.py            # Interface principal Streamlit
├── database.py       # Banco de dados SQLite
├── pdf_utils.py      # Geração de relatório PDF
├── requirements.txt  # Dependências Python
├── iniciar.ps1       # Atalho para iniciar
└── controlill.db     # Banco de dados (criado automaticamente)
```

---

## 🚀 Como Iniciar

Clique com botão direito em `iniciar.ps1` → **Executar com PowerShell**

Ou manualmente:
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

---

## 📋 Funcionalidades

### Setores suportados
- **Hematologia** — Cellpack DCL, Cellpack DFL, Lysercell WNR/WDF, Sulfolyser, Fluorocell WDF/WNR/RET, VHS, Reticulócitos, TAP, KPTT
- **Urinálise** — Tira Reagente (Meditape UC-11A), UF - CellSheath, UF - CellPack SF/CR, UF - Fluorocell SF/CR, Salina, Bacterioscopia
- **Parasitologia** — Sangue Oculto, Clostridium, Rotavírus
- **Microbiologia** — 14 meios de cultura/placas individualizados
- **Imunobioquímica** — 42 exames incluindo VDRL, Gasometria, HIV Teste Rápido, etc.
- **Gasometria**, **Bioquímica**, **Agência Transfusional**

### Gestão de Lotes
- Múltiplos lotes simultâneos por setor
- Campo Exame/Teste: lista suspensa dependente do setor selecionado
- Opção de digitar reagente manualmente (não cadastrado na lista)
- Campo Fabricante
- Código de validação: formato VL_AAAA_XXXX
- Alerta automático de validade expirada
- Alerta "Lote ainda não validado para uso"

### Amostras/Etiquetas
- Inserção manual ou por leitor de código de barras
- Validação: exatamente 10 dígitos numéricos
- Enter automático após bipar — sem necessidade de clicar em "Inserir"
- Prevenção de duplicidade no mesmo lote
- Contagem em tempo real

### Importação Matrix Connect (PDF)
| Setor | Regra | Código |
|-------|-------|--------|
| Hematologia | Exato | `HMG,RET` |
| Urinálise | Contém | `CHEMSTRY` → todos os 7 reagentes |
| Imunobioquímica/Gasometria | Regra especial | BEB, HCO3, PCO2, PO2, etc. |

### Relatório PDF
Estrutura do relatório:
1. **Identificação do Lote** — Setor, Exame, Lote, Fabricante, Validade
2. **Dados da Validação** — Código, Responsável, Datas
3. **Rastreabilidade de Uso do Lote** — Tabela de amostras
4. **Resumo de Uso do Lote** — Total de amostras dosadas/processadas
5. **Observações**
- Rodapé com paginação e aviso LGPD

> Microbiologia usa "processadas" no lugar de "dosadas"

---

## 🎨 Identidade Visual

Paleta corporativa técnica:
- Azul petróleo `#0F3D3E` — cor principal
- Azul acinzentado `#1F4E5F` — secundário
- Grafite `#263238` — textos
- Fundo cinza claro `#F4F6F8`
- Verde `#2E7D32` — aprovado
- Vermelho `#C62828` — vencido/erro
- Âmbar `#F9A825` — alerta

---

## 🔒 Privacidade (LGPD)

- Apenas o número da Amostra/Etiqueta é salvo — nunca nome do paciente
- O PDF informa explicitamente que não há identificação direta de pacientes
