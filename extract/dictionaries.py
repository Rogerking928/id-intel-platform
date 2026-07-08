"""
Controlled vocabularies (gazetteers) for the rule-based extractor.

Each dictionary maps a CANONICAL term -> list of surface forms / synonyms that
may appear in text. The extractor matches synonyms but always stores the
canonical term, so "MRSA" and "methicillin-resistant Staphylococcus aureus"
collapse to one node in search and the knowledge graph.

Freeze this file (the codebook) BEFORE looking at model outputs so the Paper 1
benchmark has no leakage.
"""

# --- Pathogens: both phenotype labels (MRSA/CRE) and organisms ---------------
PATHOGENS = {
    "MRSA": ["mrsa", "methicillin-resistant staphylococcus aureus",
             "methicillin resistant staphylococcus aureus", "meticillin-resistant staphylococcus aureus"],
    "MSSA": ["mssa", "methicillin-susceptible staphylococcus aureus"],
    "VRE": ["vre", "vancomycin-resistant enterococc", "vancomycin resistant enterococc"],
    "VRSA": ["vrsa", "vancomycin-resistant staphylococcus aureus"],
    "CRE": ["cre", "carbapenem-resistant enterobacterales", "carbapenem resistant enterobacterales",
            "carbapenem-resistant enterobacteriaceae", "carbapenem resistant enterobacteriaceae"],
    "CRKP": ["crkp", "carbapenem-resistant klebsiella pneumoniae", "carbapenem resistant klebsiella"],
    "CRAB": ["crab", "carbapenem-resistant acinetobacter", "carbapenem resistant acinetobacter"],
    "CRPA": ["crpa", "carbapenem-resistant pseudomonas", "carbapenem resistant pseudomonas"],
    "ESBL": ["esbl", "extended-spectrum beta-lactamase", "extended spectrum beta-lactamase",
             "extended-spectrum β-lactamase"],
    "Candida auris": ["candida auris", "c. auris", "candidozyma auris"],
    "Clostridioides difficile": ["clostridioides difficile", "clostridium difficile", "c. difficile", "c difficile"],
    "Klebsiella pneumoniae": ["klebsiella pneumoniae", "k. pneumoniae"],
    "Escherichia coli": ["escherichia coli", "e. coli"],
    "Acinetobacter baumannii": ["acinetobacter baumannii", "a. baumannii"],
    "Pseudomonas aeruginosa": ["pseudomonas aeruginosa", "p. aeruginosa"],
    "Staphylococcus aureus": ["staphylococcus aureus", "s. aureus"],
    "Enterococcus faecium": ["enterococcus faecium", "e. faecium"],
    "Enterococcus faecalis": ["enterococcus faecalis", "e. faecalis"],
    "Neisseria gonorrhoeae": ["neisseria gonorrhoeae", "n. gonorrhoeae", "gonorrhoea", "gonorrhea"],
    "Mycobacterium tuberculosis": ["mycobacterium tuberculosis", "m. tuberculosis", "mdr-tb", "xdr-tb",
                                   "multidrug-resistant tuberculosis"],
    "Salmonella": ["salmonella", "typhoid", "salmonella typhi"],
    "Shigella": ["shigella", "shigellosis"],
    "Streptococcus pneumoniae": ["streptococcus pneumoniae", "s. pneumoniae", "pneumococc"],
    "Aspergillus": ["aspergillus", "aspergillosis"],
}

# --- Antibiotics / antifungals ----------------------------------------------
ANTIBIOTICS = {
    "cefiderocol": ["cefiderocol"],
    "ceftazidime-avibactam": ["ceftazidime-avibactam", "ceftazidime avibactam", "caz-avi"],
    "meropenem-vaborbactam": ["meropenem-vaborbactam", "meropenem vaborbactam"],
    "imipenem-relebactam": ["imipenem-relebactam", "imipenem relebactam"],
    "meropenem": ["meropenem"],
    "imipenem": ["imipenem"],
    "ertapenem": ["ertapenem"],
    "vancomycin": ["vancomycin"],
    "daptomycin": ["daptomycin"],
    "linezolid": ["linezolid"],
    "teicoplanin": ["teicoplanin"],
    "colistin": ["colistin", "polymyxin e"],
    "polymyxin B": ["polymyxin b"],
    "tigecycline": ["tigecycline"],
    "eravacycline": ["eravacycline"],
    "ceftaroline": ["ceftaroline"],
    "ceftolozane-tazobactam": ["ceftolozane-tazobactam", "ceftolozane tazobactam"],
    "aztreonam": ["aztreonam"],
    "fosfomycin": ["fosfomycin"],
    "amikacin": ["amikacin"],
    "gentamicin": ["gentamicin"],
    "ciprofloxacin": ["ciprofloxacin"],
    "levofloxacin": ["levofloxacin"],
    "piperacillin-tazobactam": ["piperacillin-tazobactam", "piperacillin tazobactam", "pip-tazo"],
    "fluconazole": ["fluconazole"],
    "echinocandin": ["echinocandin", "caspofungin", "micafungin", "anidulafungin"],
    "amphotericin B": ["amphotericin b"],
}

# --- Resistance genes / mechanisms ------------------------------------------
RESISTANCE_GENES = {
    "NDM": ["ndm", "new delhi metallo"],
    "KPC": ["kpc", "klebsiella pneumoniae carbapenemase"],
    "OXA-48": ["oxa-48", "oxa 48"],
    "OXA-23": ["oxa-23", "oxa 23"],
    "VIM": ["vim-", "verona integron"],
    "IMP": ["imp-", "imipenemase"],
    "CTX-M": ["ctx-m", "ctx m"],
    "mcr-1": ["mcr-1", "mcr1", "mobile colistin resistance"],
    "vanA": ["vana", "van a"],
    "vanB": ["vanb", "van b"],
    "mecA": ["meca"],
    "mecC": ["mecc"],
    "SME": ["sme carbapenemase"],
    "GES": ["ges carbapenemase", "ges-"],
    "carbapenemase": ["carbapenemase"],
    "metallo-beta-lactamase": ["metallo-beta-lactamase", "metallo-β-lactamase", "mbl"],
}

# --- Diseases / syndromes ----------------------------------------------------
DISEASES = {
    "bloodstream infection": ["bloodstream infection", "bacteraemia", "bacteremia", "sepsis", "septic shock"],
    "pneumonia": ["pneumonia", "ventilator-associated pneumonia", "vap", "hap"],
    "urinary tract infection": ["urinary tract infection", "uti", "pyelonephritis"],
    "intra-abdominal infection": ["intra-abdominal infection", "peritonitis", "liver abscess"],
    "meningitis": ["meningitis"],
    "endocarditis": ["endocarditis"],
    "wound infection": ["wound infection", "surgical site infection", "ssi"],
    "outbreak": ["outbreak", "cluster of cases", "nosocomial transmission"],
    "colonisation": ["colonisation", "colonization", "carriage"],
    "candidemia": ["candidemia", "candidaemia", "invasive candidiasis"],
    "tuberculosis": ["tuberculosis"],
}

# --- Countries (subset; APAC emphasised). Maps country -> region ------------
COUNTRY_REGION = {
    # APAC
    "Taiwan": "APAC", "China": "APAC", "Japan": "APAC", "South Korea": "APAC",
    "Korea": "APAC", "Hong Kong": "APAC", "Singapore": "APAC", "Malaysia": "APAC",
    "Thailand": "APAC", "Vietnam": "APAC", "Viet Nam": "APAC", "Philippines": "APAC",
    "Indonesia": "APAC", "India": "APAC", "Pakistan": "APAC", "Bangladesh": "APAC",
    "Australia": "APAC", "New Zealand": "APAC", "Nepal": "APAC", "Sri Lanka": "APAC",
    "Myanmar": "APAC", "Cambodia": "APAC", "Laos": "APAC", "Mongolia": "APAC",
    # Americas
    "United States": "Americas", "USA": "Americas", "United States of America": "Americas",
    "Canada": "Americas", "Brazil": "Americas", "Mexico": "Americas", "Argentina": "Americas",
    "Chile": "Americas", "Colombia": "Americas", "Peru": "Americas",
    # Europe
    "United Kingdom": "Europe", "England": "Europe", "France": "Europe", "Germany": "Europe",
    "Italy": "Europe", "Spain": "Europe", "Greece": "Europe", "Netherlands": "Europe",
    "Portugal": "Europe", "Poland": "Europe", "Sweden": "Europe", "Switzerland": "Europe",
    "Ireland": "Europe", "Belgium": "Europe", "Turkey": "Europe", "Russia": "Europe",
    # MENA / Africa
    "Saudi Arabia": "MENA", "Iran": "MENA", "Iraq": "MENA", "Egypt": "MENA",
    "Israel": "MENA", "United Arab Emirates": "MENA", "Qatar": "MENA", "Kuwait": "MENA",
    "South Africa": "Africa", "Nigeria": "Africa", "Kenya": "Africa", "Ethiopia": "Africa",
    "Ghana": "Africa", "Tanzania": "Africa", "Uganda": "Africa",
    "Democratic Republic of the Congo": "Africa",
}

# Study-type keyword hints (used by the classifier)
STUDY_TYPE_HINTS = {
    "Clinical Trial": ["randomi", "clinical trial", "phase i", "phase ii", "phase iii",
                       "double-blind", "placebo", "nct0", "nct1", "nct2"],
    "Guideline": ["guideline", "recommendation", "consensus", "guidance", "position statement"],
    "Outbreak": ["outbreak", "disease outbreak news", "cluster of cases", "epidemic"],
}

# Event-type classification keywords. The 8 categories the user asked for.
# "Research Article" is the fallback when nothing more specific matches a paper.
EVENT_TYPE_ORDER = [
    "Outbreak", "Clinical Trial", "Guideline", "Vaccine", "New Drug",
    "Emerging Pathogen", "Antimicrobial Resistance", "Research Article",
]
EVENT_TYPE_HINTS = {
    "Outbreak": ["outbreak", "epidemic", "cluster of cases", "disease outbreak news", "nosocomial transmission"],
    "Clinical Trial": ["randomi", "clinical trial", "phase iii", "phase ii", "placebo", "nct0", "nct1", "nct2"],
    "Guideline": ["guideline", "recommendation", "consensus", "guidance", "position statement"],
    "Vaccine": ["vaccine", "vaccination", "immuni", "immunogenicity"],
    "New Drug": ["novel antibiotic", "new antibiotic", "drug candidate", "in vitro activity",
                 "pharmacokinetic", "spectrum of activity"],
    "Emerging Pathogen": ["emerging", "novel pathogen", "first report", "first detection", "newly identified"],
    "Antimicrobial Resistance": ["resistance", "resistant", "carbapenemase", "mdr", "xdr", "susceptibility",
                                 "antimicrobial resistance", "amr", "esbl"],
}
