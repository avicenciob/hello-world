"""
EU Critical Raw Materials list (2023 update) with metadata for patent search.

Source: European Commission - Study on the Critical Raw Materials for the EU (2023)
https://single-market-economy.ec.europa.eu/sectors/raw-materials/areas-specific-interest/critical-raw-materials_en

Each material entry includes:
- name: Official name from the EU CRM list
- symbol: Chemical symbol(s) where applicable
- aliases: Alternative names, chemical formulas, and common industry terms
- cpc_codes: Relevant Cooperative Patent Classification codes
- applications: Key industrial applications (for context in patent classification)
- category: Material category (e.g., metal, mineral, element)
"""

from dataclasses import dataclass, field


@dataclass
class CriticalRawMaterial:
    name: str
    symbol: str
    aliases: list[str] = field(default_factory=list)
    cpc_codes: list[str] = field(default_factory=list)
    applications: list[str] = field(default_factory=list)
    category: str = ""

    def search_terms(self) -> list[str]:
        """Return all terms that should be used when searching patents."""
        terms = [self.name]
        if self.symbol:
            terms.append(self.symbol)
        terms.extend(self.aliases)
        return list(set(terms))


# EU Critical Raw Materials List (2023) - 34 materials
# Reference: COM(2023) 160 final - European Critical Raw Materials Act
EU_CRITICAL_RAW_MATERIALS: list[CriticalRawMaterial] = [
    CriticalRawMaterial(
        name="Antimony",
        symbol="Sb",
        aliases=["stibium", "antimony trioxide", "Sb2O3", "antimony trisulfide"],
        cpc_codes=["C22B30/02", "C01G30/00"],
        applications=["flame retardants", "lead-acid batteries", "semiconductors"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Arsenic",
        symbol="As",
        aliases=["arsenicum", "arsenic trioxide", "As2O3", "gallium arsenide", "GaAs"],
        cpc_codes=["C22B30/04", "C01G28/00"],
        applications=["semiconductors", "wood preservatives", "alloys"],
        category="metalloid",
    ),
    CriticalRawMaterial(
        name="Baryte",
        symbol="BaSO4",
        aliases=["barite", "barium sulfate", "barium sulphate", "heavy spar"],
        cpc_codes=["C01F11/46", "C09K8/02"],
        applications=["drilling fluids", "filler", "radiation shielding"],
        category="mineral",
    ),
    CriticalRawMaterial(
        name="Bauxite",
        symbol="",
        aliases=["aluminium ore", "aluminum ore", "gibbsite", "boehmite", "diaspore"],
        cpc_codes=["C22B21/00", "C01F7/00"],
        applications=["aluminium production", "refractories", "abrasives"],
        category="mineral",
    ),
    CriticalRawMaterial(
        name="Beryllium",
        symbol="Be",
        aliases=["glucinium", "beryllium copper", "BeCu", "beryllium oxide", "BeO"],
        cpc_codes=["C22B59/00", "C22C1/04"],
        applications=["aerospace", "electronics", "nuclear", "X-ray windows"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Bismuth",
        symbol="Bi",
        aliases=["bismuth oxide", "Bi2O3", "bismuth subsalicylate", "bismuth telluride"],
        cpc_codes=["C22B30/06", "C01G29/00"],
        applications=["pharmaceuticals", "cosmetics", "low-melting alloys", "thermoelectrics"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Boron",
        symbol="B",
        aliases=["borate", "boron carbide", "B4C", "boron nitride", "BN", "borax", "boric acid"],
        cpc_codes=["C01B35/00", "C04B35/583"],
        applications=["glass", "ceramics", "detergents", "agriculture", "nuclear shielding"],
        category="metalloid",
    ),
    CriticalRawMaterial(
        name="Cobalt",
        symbol="Co",
        aliases=["cobalt oxide", "CoO", "cobalt sulfate", "lithium cobalt oxide", "LiCoO2"],
        cpc_codes=["C22B23/00", "H01M4/525"],
        applications=["batteries", "superalloys", "catalysts", "magnets"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Coking coal",
        symbol="",
        aliases=["metallurgical coal", "coking coal", "met coal", "bituminous coal"],
        cpc_codes=["C10B57/00", "C21B5/00"],
        applications=["steelmaking", "coke production"],
        category="mineral",
    ),
    CriticalRawMaterial(
        name="Copper",
        symbol="Cu",
        aliases=["cuprum", "copper oxide", "CuO", "copper sulfate", "CuSO4"],
        cpc_codes=["C22B15/00", "H01B1/02"],
        applications=["electrical wiring", "electronics", "plumbing", "renewable energy"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Feldspar",
        symbol="",
        aliases=["orthoclase", "plagioclase", "microcline", "albite", "anorthite", "K-feldspar"],
        cpc_codes=["C04B33/00", "C03C1/02"],
        applications=["ceramics", "glassmaking", "fillers"],
        category="mineral",
    ),
    CriticalRawMaterial(
        name="Fluorspar",
        symbol="CaF2",
        aliases=["fluorite", "calcium fluoride", "fluorospar", "acid grade fluorspar"],
        cpc_codes=["C01F11/22", "C22B1/02"],
        applications=["steelmaking flux", "hydrofluoric acid", "aluminium smelting"],
        category="mineral",
    ),
    CriticalRawMaterial(
        name="Gallium",
        symbol="Ga",
        aliases=["gallium arsenide", "GaAs", "gallium nitride", "GaN", "gallium oxide"],
        cpc_codes=["C22B58/00", "H01L29/20"],
        applications=["semiconductors", "LEDs", "solar cells", "5G technology"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Germanium",
        symbol="Ge",
        aliases=["germanium dioxide", "GeO2", "germanium tetrachloride", "GeCl4"],
        cpc_codes=["C22B41/00", "C01G17/00"],
        applications=["fiber optics", "infrared optics", "solar cells", "semiconductors"],
        category="metalloid",
    ),
    CriticalRawMaterial(
        name="Hafnium",
        symbol="Hf",
        aliases=["hafnium oxide", "HfO2", "hafnium carbide", "hafnium diboride"],
        cpc_codes=["C22B34/14", "C01G27/00"],
        applications=["nuclear reactors", "superalloys", "semiconductors"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Helium",
        symbol="He",
        aliases=["liquid helium", "helium-3", "He-3", "helium-4"],
        cpc_codes=["C01B23/00", "F25J1/00"],
        applications=["cryogenics", "MRI", "welding", "leak detection"],
        category="element",
    ),
    CriticalRawMaterial(
        name="Lithium",
        symbol="Li",
        aliases=[
            "lithium carbonate", "Li2CO3", "lithium hydroxide", "LiOH",
            "lithium iron phosphate", "LiFePO4", "spodumene",
        ],
        cpc_codes=["C22B26/12", "H01M10/052"],
        applications=["batteries", "ceramics", "glass", "lubricants", "pharmaceuticals"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Magnesium",
        symbol="Mg",
        aliases=["magnesium alloy", "magnesium oxide", "MgO", "magnesia", "magnesium hydroxide"],
        cpc_codes=["C22B26/20", "C22C23/00"],
        applications=["lightweight alloys", "refractories", "desulfurization"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Manganese",
        symbol="Mn",
        aliases=["manganese dioxide", "MnO2", "ferromanganese", "manganese sulfate"],
        cpc_codes=["C22B47/00", "H01M4/50"],
        applications=["steelmaking", "batteries", "chemicals"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Natural graphite",
        symbol="C",
        aliases=["graphite", "flake graphite", "vein graphite", "amorphous graphite", "crystalline graphite"],
        cpc_codes=["C01B32/20", "H01M4/587"],
        applications=["batteries", "refractories", "lubricants", "fuel cells"],
        category="mineral",
    ),
    CriticalRawMaterial(
        name="Nickel",
        symbol="Ni",
        aliases=["nickel sulfate", "NiSO4", "nickel oxide", "NiO", "nickel hydroxide"],
        cpc_codes=["C22B23/00", "H01M4/525"],
        applications=["stainless steel", "batteries", "superalloys", "plating"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Niobium",
        symbol="Nb",
        aliases=["columbium", "ferroniobium", "niobium oxide", "Nb2O5", "niobium carbide"],
        cpc_codes=["C22B34/24", "C01G33/00"],
        applications=["steel alloys", "superconductors", "capacitors"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Phosphate rock",
        symbol="",
        aliases=["phosphorite", "apatite", "phosphorus", "rock phosphate", "fluorapatite"],
        cpc_codes=["C05B1/00", "C01B25/00"],
        applications=["fertilizers", "phosphoric acid", "animal feed"],
        category="mineral",
    ),
    CriticalRawMaterial(
        name="Platinum Group Metals",
        symbol="PGM",
        aliases=[
            "platinum", "Pt", "palladium", "Pd", "rhodium", "Rh",
            "ruthenium", "Ru", "iridium", "Ir", "osmium", "Os",
        ],
        cpc_codes=["C22B11/00", "B01J23/40"],
        applications=["catalytic converters", "fuel cells", "electronics", "jewelry"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Rare Earth Elements",
        symbol="REE",
        aliases=[
            "rare earth", "lanthanum", "La", "cerium", "Ce", "praseodymium", "Pr",
            "neodymium", "Nd", "samarium", "Sm", "europium", "Eu", "gadolinium", "Gd",
            "terbium", "Tb", "dysprosium", "Dy", "holmium", "Ho", "erbium", "Er",
            "thulium", "Tm", "ytterbium", "Yb", "lutetium", "Lu",
            "yttrium", "Y", "scandium", "Sc",
            "NdFeB", "neodymium magnet",
        ],
        cpc_codes=["C22B59/00", "H01F1/057"],
        applications=["magnets", "catalysts", "glass polishing", "phosphors", "wind turbines"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Silicon metal",
        symbol="Si",
        aliases=[
            "metallurgical grade silicon", "polysilicon", "silicon wafer",
            "ferrosilicon", "silicon carbide", "SiC",
        ],
        cpc_codes=["C01B33/00", "C30B29/06"],
        applications=["semiconductors", "solar cells", "aluminium alloys", "silicones"],
        category="metalloid",
    ),
    CriticalRawMaterial(
        name="Strontium",
        symbol="Sr",
        aliases=["strontium carbonate", "SrCO3", "strontium oxide", "celestite", "strontianite"],
        cpc_codes=["C01F11/00", "C22B26/20"],
        applications=["pyrotechnics", "ferrite magnets", "zinc refining"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Tantalum",
        symbol="Ta",
        aliases=["tantalum pentoxide", "Ta2O5", "tantalum capacitor", "coltan", "tantalite"],
        cpc_codes=["C22B34/24", "H01G9/042"],
        applications=["capacitors", "surgical instruments", "jet engines"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Titanium",
        symbol="Ti",
        aliases=[
            "titanium dioxide", "TiO2", "titanium alloy", "Ti-6Al-4V",
            "rutile", "ilmenite", "titanium sponge",
        ],
        cpc_codes=["C22B34/12", "C01G23/00"],
        applications=["aerospace", "pigments", "medical implants", "3D printing"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Tungsten",
        symbol="W",
        aliases=[
            "wolfram", "tungsten carbide", "WC", "scheelite",
            "wolframite", "ammonium paratungstate", "APT",
        ],
        cpc_codes=["C22B34/36", "B23B27/14"],
        applications=["cutting tools", "mining", "lighting", "military"],
        category="metal",
    ),
    CriticalRawMaterial(
        name="Vanadium",
        symbol="V",
        aliases=[
            "vanadium pentoxide", "V2O5", "ferrovanadium",
            "vanadium redox battery", "vanadium oxide",
        ],
        cpc_codes=["C22B34/22", "H01M8/18"],
        applications=["steel alloys", "flow batteries", "catalysts", "aerospace"],
        category="metal",
    ),
]

# Build lookup dictionaries for fast access
CRM_BY_NAME: dict[str, CriticalRawMaterial] = {m.name: m for m in EU_CRITICAL_RAW_MATERIALS}

ALL_CRM_SEARCH_TERMS: dict[str, str] = {}
for material in EU_CRITICAL_RAW_MATERIALS:
    for term in material.search_terms():
        ALL_CRM_SEARCH_TERMS[term.lower()] = material.name


def get_all_materials() -> list[CriticalRawMaterial]:
    """Return the complete list of EU Critical Raw Materials."""
    return EU_CRITICAL_RAW_MATERIALS


def find_material(name: str) -> CriticalRawMaterial | None:
    """Find a CRM by name or alias."""
    name_lower = name.lower()
    if name_lower in ALL_CRM_SEARCH_TERMS:
        return CRM_BY_NAME[ALL_CRM_SEARCH_TERMS[name_lower]]
    return None


def detect_materials_in_text(text: str) -> list[tuple[CriticalRawMaterial, str]]:
    """Detect which CRMs are mentioned in a text. Returns list of (material, matched_term)."""
    text_lower = text.lower()
    found = []
    seen_materials = set()
    # Sort by length descending to match longer terms first
    sorted_terms = sorted(ALL_CRM_SEARCH_TERMS.keys(), key=len, reverse=True)
    for term in sorted_terms:
        material_name = ALL_CRM_SEARCH_TERMS[term]
        if material_name not in seen_materials and term in text_lower:
            # Only match terms of 3+ chars to avoid false positives with symbols
            if len(term) >= 3:
                material = CRM_BY_NAME[material_name]
                found.append((material, term))
                seen_materials.add(material_name)
    return found
