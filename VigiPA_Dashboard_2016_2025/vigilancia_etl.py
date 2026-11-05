"""ETL streaming para notificações de violência SINAN (2016–2025).

Entrada: cinco CSVs brutos disponíveis na pasta upload, sendo dois dentro de csv.zip.
Saída: dados agregados sem registros individuais, em vigilancia_dashboard/data.json.
Não imputa campos epidemiológicos ignorados/ausentes nem calcula taxas sem população.
"""
from collections import Counter, defaultdict
from datetime import datetime
import csv
import json
from pathlib import Path
import unicodedata
import zipfile

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'vigilancia_dashboard' / 'data.json'

# Códigos de seis dígitos do SINAN; aceitam-se também os sete dígitos IBGE.
MUNICIPIOS = {
    '150040': 'Alenquer', '150050': 'Almeirim', '150145': 'Belterra',
    '150285': 'Curuá', '150300': 'Faro', '150390': 'Juruti',
    '150475': 'Mojuí dos Campos', '150480': 'Monte Alegre',
    '150510': 'Óbidos', '150530': 'Oriximiná', '150600': 'Prainha',
    '150680': 'Santarém', '150797': 'Terra Santa',
}
MUNICIPIOS_7 = {
    '1500404','1500503','1501451','1502855','1503002','1503903',
    '1504752','1504802','1505106','1505304','1506005','1506807','1507979'
}
COLS = ['NU_ANO','DT_NOTIFIC','DT_OCOR','ID_MN_OCOR','ID_MN_RESI','CS_SEXO','CS_RACA','NU_IDADE_N','LES_AUTOP','OUT_VEZES','EVOLUCAO','LOCAL_OCOR']
VIOLENCE = {
    'VIOL_FISIC':'Física','VIOL_PSICO':'Psicológica/moral','VIOL_TORT':'Tortura',
    'VIOL_SEXU':'Sexual','VIOL_TRAF':'Tráfico de pessoas','VIOL_FINAN':'Financeira/econômica',
    'VIOL_NEGLI':'Negligência/abandono','VIOL_INFAN':'Trabalho infantil',
    'VIOL_LEGAL':'Intervenção legal','VIOL_OUTR':'Outros',
}
MEANS = {
    'AG_FORCA':'Força corporal','AG_ENFOR':'Enforcamento','AG_OBJETO':'Objeto contundente',
    'AG_CORTE':'Objeto perfurocortante','AG_QUENTE':'Objeto quente',
    'AG_ENVEN':'Envenenamento','AG_FOGO':'Arma de fogo',
    'AG_AMEACA':'Ameaça','AG_OUTROS':'Outros meios',
}
RELATIONS = {
    'REL_PAI':'Pai','REL_MAE':'Mãe','REL_PAD':'Padrasto',
    'REL_CONJ':'Cônjuge','REL_EXCON':'Ex-cônjuge','REL_NAMO':'Namorado(a)',
    'REL_EXNAM':'Ex-namorado(a)','REL_FILHO':'Filho(a)',
    'REL_DESCO':'Desconhecido(a)','REL_IRMAO':'Irmão(ã)',
    'REL_CONHEC':'Conhecido(a)','REL_CUIDA':'Cuidador(a)',
    'REL_PATRAO':'Patrão','REL_INST':'Institucional',
    'REL_POL':'Policial','REL_PROPRI':'Própria pessoa','REL_OUTROS':'Outros vínculos',
}
PLACE = {'01':'Residência','02':'Habitação coletiva','03':'Escola','04':'Esporte',
         '05':'Bar ou similar','06':'Via pública','07':'Comércio/serviços',
         '08':'Indústria/construção','09':'Outros'}
SEX = {'F':'Feminino','M':'Masculino'}
RACE = {'1':'Branca','2':'Preta','3':'Amarela','4':'Parda','5':'Indígena'}


def new_agg():
    return {'n':0,'repeat_yes':0,'repeat_known':0,'outcome_known':0,'deaths':0,
            'sex':Counter(),'race':Counter(),'age':Counter(),'place':Counter(),
            'violence':Counter(),'means':Counter(),'relations':Counter(),
            'month':Counter()}


def age_group(raw):
    s=(raw or '').strip()
    if len(s)!=4 or not s.isdigit():return 'Ignorada'
    unit=int(s[0]);value=int(s[1:])
    if unit in (1,2,3):return 'Criança (0–11)'
    if unit!=4 or value>120:return 'Ignorada'
    if value<12:return 'Criança (0–11)'
    if value<18:return 'Adolescente (12–17)'
    if value<60:return 'Adulto (18–59)'
    return 'Idoso (60+)'


def date_month(raw):
    s=(raw or '').strip()
    for fmt in ('%Y%m%d','%d/%m/%Y','%Y-%m-%d'):
        try:return datetime.strptime(s,fmt).month
        except ValueError:pass
    return None


def normalized_mun(raw):
    s=''.join(c for c in str(raw).strip() if c.isdigit())
    if len(s) not in (6,7):return None
    if len(s)==7 and s not in MUNICIPIOS_7:return None
    return MUNICIPIOS.get(s[:6])


def aggregate_one(row,agg):
    agg['n']+=1
    repeat=row['OUT_VEZES'].strip()
    if repeat in ('1','2'):
        agg['repeat_known']+=1
        if repeat=='1':agg['repeat_yes']+=1
    outcome=row['EVOLUCAO'].strip()
    # Dicionário SINAN: 1=alta, 2=evasão/fuga, 3=óbito por violência,
    # 4=óbito por outras causas; ignorado/nulo não entra no denominador.
    if outcome in ('1','2','3','4'):
        agg['outcome_known']+=1
        if outcome=='3':agg['deaths']+=1
    agg['sex'][SEX.get(row['CS_SEXO'].strip().upper(),'Ignorado')]+=1
    agg['race'][RACE.get(row['CS_RACA'].strip(),'Ignorada')]+=1
    agg['age'][age_group(row['NU_IDADE_N'])]+=1
    agg['place'][PLACE.get(row['LOCAL_OCOR'].strip().zfill(2),'Ignorado')]+=1
    for field,name in VIOLENCE.items():
        if row[field].strip()=='1':agg['violence'][name]+=1
    for field,name in MEANS.items():
        if row[field].strip()=='1':agg['means'][name]+=1
    for field,name in RELATIONS.items():
        if row[field].strip()=='1':agg['relations'][name]+=1
    month=date_month(row['DT_NOTIFIC'])
    if month is not None:agg['month'][str(month).zfill(2)]+=1


def main():
    aggregate=defaultdict(new_agg)
    profile=Counter()
    source_names=[]
    sources=[ROOT/'upload'/'Violencia16_17(1).csv',ROOT/'upload'/'Violencia18_19(1).csv',ROOT/'upload'/'Violencia20_21(1).csv']
    z=zipfile.ZipFile(ROOT/'upload'/'csv.zip')
    source_iter=[(p.name,p.open('r',encoding='utf-8-sig',newline='')) for p in sources]
    source_iter += [(name,__import__('io').TextIOWrapper(z.open(name),encoding='utf-8-sig',newline='')) for name in ('csv/Violencia22_23.csv','csv/Violencia24_25.csv')]
    for label,handle in source_iter:
        source_names.append(label)
        with handle:
            reader=csv.DictReader(handle)
            needed=set(COLS)|set(VIOLENCE)|set(MEANS)|set(RELATIONS)
            missing=needed-set(reader.fieldnames or [])
            if missing:raise ValueError(f'{label}: campos ausentes: {sorted(missing)}')
            for row in reader:
                profile['raw_rows']+=1
                year_s=(row['NU_ANO'] or '').strip()
                if not(year_s.isdigit() and 2016<=int(year_s)<=2025):
                    profile['outside_year_or_invalid']+=1;continue
                mun=normalized_mun(row['ID_MN_OCOR'])
                if mun is None:
                    profile['outside_municipalities_or_invalid']+=1;continue
                kind={'1':'Autoprovocada','2':'Não autoprovocada'}.get((row['LES_AUTOP'] or '').strip(),'Não classificada')
                profile['selected_rows']+=1
                if kind=='Não classificada':profile['unclassified_kind']+=1
                aggregate_one(row,aggregate[(int(year_s),mun,kind)])
        print(f'Processado {label}: {profile["raw_rows"]:,} linhas acumuladas',flush=True)
    z.close()
    records=[]
    for (year,mun,kind),value in sorted(aggregate.items()):
        record={'year':year,'municipio':mun,'agravo':kind}
        for key,val in value.items():record[key]=dict(val) if isinstance(val,Counter) else val
        records.append(record)
    payload={'metadata':{'title':'Vigilância de violência interpessoal e autoprovocada',
                         'source_files':source_names,'date_basis':'NU_ANO (ano da notificação)',
                         'municipality_basis':'ID_MN_OCOR (município de ocorrência)',
                         'population_available':False,'individual_records_included':False,
                         'source_dictionary':'VIOLEN_DIC_DADOS.pdf (revisão junho/2015)',
                         'quality':dict(profile)},
             'municipios':list(MUNICIPIOS.values()),'years':list(range(2016,2026)),
             'records':records}
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f'Salvo {OUTPUT}: {len(records)} grupos, {OUTPUT.stat().st_size:,} bytes',flush=True)
    print('Qualidade:',dict(profile),flush=True)


if __name__=='__main__':main()
