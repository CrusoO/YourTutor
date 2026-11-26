# ruff: noqa: E501
"""Reviewed data tables for the chemistry lane. Closed lists only; nothing here is generated.

REVIEWED = False: a person must review every table before any item built from it is served. Each
reaction carries its balanced coefficients written BY HAND, so tests can compare them with the
coefficients the two methods compute (a golden vector from a different author than the code).
Atomic masses and constants come only from the kernel's one constants table, never from here.
The reactivity series is the school series; the standard electrode potentials are a cited
cross-check (standard tables, rounded) used only to refuse pairs on which the two disagree.
"""

from __future__ import annotations

REVIEWED = False
TABLE_VERSION = "1"

# ---------------------------------------------------------------- reactions
# id, type, reactants, products, hand-balanced coefficients (reactants then products)
Reaction = tuple[str, str, tuple[str, ...], tuple[str, ...], tuple[int, ...]]

COMBINATION = "combination"
DECOMPOSITION = "decomposition"
DISPLACEMENT = "displacement"
DOUBLE = "double displacement"
TYPES = (COMBINATION, DECOMPOSITION, DISPLACEMENT, DOUBLE)

REACTIONS: tuple[Reaction, ...] = (
    ("C01", COMBINATION, ("Mg", "O2"), ("MgO",), (2, 1, 2)),
    ("C02", COMBINATION, ("H2", "O2"), ("H2O",), (2, 1, 2)),
    ("C03", COMBINATION, ("N2", "H2"), ("NH3",), (1, 3, 2)),
    ("C04", COMBINATION, ("CaO", "H2O"), ("Ca(OH)2",), (1, 1, 1)),
    ("C05", COMBINATION, ("Na", "Cl2"), ("NaCl",), (2, 1, 2)),
    ("C06", COMBINATION, ("Al", "O2"), ("Al2O3",), (4, 3, 2)),
    ("C07", COMBINATION, ("C", "O2"), ("CO2",), (1, 1, 1)),
    ("C08", COMBINATION, ("CO", "O2"), ("CO2",), (2, 1, 2)),
    ("C09", COMBINATION, ("S", "O2"), ("SO2",), (1, 1, 1)),
    ("C10", COMBINATION, ("SO2", "O2"), ("SO3",), (2, 1, 2)),
    ("C11", COMBINATION, ("Mg", "N2"), ("Mg3N2",), (3, 1, 1)),
    ("C12", COMBINATION, ("Cu", "O2"), ("CuO",), (2, 1, 2)),
    ("C13", COMBINATION, ("Na", "O2"), ("Na2O",), (4, 1, 2)),
    ("C14", COMBINATION, ("H2", "Cl2"), ("HCl",), (1, 1, 2)),
    ("C15", COMBINATION, ("NH3", "HCl"), ("NH4Cl",), (1, 1, 1)),
    ("C16", COMBINATION, ("Fe", "Cl2"), ("FeCl3",), (2, 3, 2)),
    ("C17", COMBINATION, ("Ca", "O2"), ("CaO",), (2, 1, 2)),
    ("C18", COMBINATION, ("Zn", "O2"), ("ZnO",), (2, 1, 2)),
    ("C19", COMBINATION, ("P", "O2"), ("P2O5",), (4, 5, 2)),
    ("C20", COMBINATION, ("Al", "Cl2"), ("AlCl3",), (2, 3, 2)),
    ("C21", COMBINATION, ("Fe", "O2"), ("Fe2O3",), (4, 3, 2)),
    ("C22", COMBINATION, ("Li", "N2"), ("Li3N",), (6, 1, 2)),
    ("D01", DECOMPOSITION, ("H2O",), ("H2", "O2"), (2, 2, 1)),
    ("D02", DECOMPOSITION, ("CaCO3",), ("CaO", "CO2"), (1, 1, 1)),
    ("D03", DECOMPOSITION, ("KClO3",), ("KCl", "O2"), (2, 2, 3)),
    ("D04", DECOMPOSITION, ("HgO",), ("Hg", "O2"), (2, 2, 1)),
    ("D05", DECOMPOSITION, ("H2O2",), ("H2O", "O2"), (2, 2, 1)),
    ("D06", DECOMPOSITION, ("NaHCO3",), ("Na2CO3", "H2O", "CO2"), (2, 1, 1, 1)),
    ("D07", DECOMPOSITION, ("FeSO4",), ("Fe2O3", "SO2", "SO3"), (2, 1, 1, 1)),
    ("D08", DECOMPOSITION, ("Pb(NO3)2",), ("PbO", "NO2", "O2"), (2, 2, 4, 1)),
    ("D09", DECOMPOSITION, ("Cu(OH)2",), ("CuO", "H2O"), (1, 1, 1)),
    ("D10", DECOMPOSITION, ("AgCl",), ("Ag", "Cl2"), (2, 2, 1)),
    ("D11", DECOMPOSITION, ("AgBr",), ("Ag", "Br2"), (2, 2, 1)),
    ("D12", DECOMPOSITION, ("ZnCO3",), ("ZnO", "CO2"), (1, 1, 1)),
    ("D13", DECOMPOSITION, ("NaCl",), ("Na", "Cl2"), (2, 2, 1)),
    ("D14", DECOMPOSITION, ("Al2O3",), ("Al", "O2"), (2, 4, 3)),
    ("D15", DECOMPOSITION, ("NH4Cl",), ("NH3", "HCl"), (1, 1, 1)),
    ("D16", DECOMPOSITION, ("KNO3",), ("KNO2", "O2"), (2, 2, 1)),
    ("D17", DECOMPOSITION, ("MgCO3",), ("MgO", "CO2"), (1, 1, 1)),
    ("D18", DECOMPOSITION, ("Ca(OH)2",), ("CaO", "H2O"), (1, 1, 1)),
    ("D19", DECOMPOSITION, ("Fe(OH)3",), ("Fe2O3", "H2O"), (2, 1, 3)),
    ("S01", DISPLACEMENT, ("Zn", "CuSO4"), ("ZnSO4", "Cu"), (1, 1, 1, 1)),
    ("S02", DISPLACEMENT, ("Fe", "CuSO4"), ("FeSO4", "Cu"), (1, 1, 1, 1)),
    ("S03", DISPLACEMENT, ("Zn", "HCl"), ("ZnCl2", "H2"), (1, 2, 1, 1)),
    ("S04", DISPLACEMENT, ("Mg", "HCl"), ("MgCl2", "H2"), (1, 2, 1, 1)),
    ("S05", DISPLACEMENT, ("Pb", "Cu(NO3)2"), ("Pb(NO3)2", "Cu"), (1, 1, 1, 1)),
    ("S06", DISPLACEMENT, ("Cu", "AgNO3"), ("Cu(NO3)2", "Ag"), (1, 2, 1, 2)),
    ("S07", DISPLACEMENT, ("Zn", "H2SO4"), ("ZnSO4", "H2"), (1, 1, 1, 1)),
    ("S08", DISPLACEMENT, ("Fe", "HCl"), ("FeCl2", "H2"), (1, 2, 1, 1)),
    ("S09", DISPLACEMENT, ("Mg", "CuSO4"), ("MgSO4", "Cu"), (1, 1, 1, 1)),
    ("S10", DISPLACEMENT, ("Al", "CuSO4"), ("Al2(SO4)3", "Cu"), (2, 3, 1, 3)),
    ("S11", DISPLACEMENT, ("Cl2", "KBr"), ("KCl", "Br2"), (1, 2, 2, 1)),
    ("S12", DISPLACEMENT, ("Cl2", "KI"), ("KCl", "I2"), (1, 2, 2, 1)),
    ("S13", DISPLACEMENT, ("Br2", "KI"), ("KBr", "I2"), (1, 2, 2, 1)),
    ("S14", DISPLACEMENT, ("Zn", "Pb(NO3)2"), ("Zn(NO3)2", "Pb"), (1, 1, 1, 1)),
    ("S15", DISPLACEMENT, ("Al", "HCl"), ("AlCl3", "H2"), (2, 6, 2, 3)),
    ("S16", DISPLACEMENT, ("Al", "Fe2O3"), ("Al2O3", "Fe"), (2, 1, 1, 2)),
    ("S17", DISPLACEMENT, ("Mg", "FeSO4"), ("MgSO4", "Fe"), (1, 1, 1, 1)),
    ("S18", DISPLACEMENT, ("Fe", "AgNO3"), ("Fe(NO3)2", "Ag"), (1, 2, 1, 2)),
    ("S19", DISPLACEMENT, ("Zn", "AgNO3"), ("Zn(NO3)2", "Ag"), (1, 2, 1, 2)),
    ("S20", DISPLACEMENT, ("Mg", "H2SO4"), ("MgSO4", "H2"), (1, 1, 1, 1)),
    ("S21", DISPLACEMENT, ("Al", "H2SO4"), ("Al2(SO4)3", "H2"), (2, 3, 1, 3)),
    ("X01", DOUBLE, ("Na2SO4", "BaCl2"), ("BaSO4", "NaCl"), (1, 1, 1, 2)),
    ("X02", DOUBLE, ("NaOH", "HCl"), ("NaCl", "H2O"), (1, 1, 1, 1)),
    ("X03", DOUBLE, ("AgNO3", "NaCl"), ("AgCl", "NaNO3"), (1, 1, 1, 1)),
    ("X04", DOUBLE, ("CuSO4", "NaOH"), ("Cu(OH)2", "Na2SO4"), (1, 2, 1, 1)),
    ("X05", DOUBLE, ("Pb(NO3)2", "KI"), ("PbI2", "KNO3"), (1, 2, 1, 2)),
    ("X06", DOUBLE, ("CaCl2", "Na2CO3"), ("CaCO3", "NaCl"), (1, 1, 1, 2)),
    ("X07", DOUBLE, ("NaOH", "H2SO4"), ("Na2SO4", "H2O"), (2, 1, 1, 2)),
    ("X08", DOUBLE, ("KOH", "HNO3"), ("KNO3", "H2O"), (1, 1, 1, 1)),
    ("X09", DOUBLE, ("FeCl3", "NaOH"), ("Fe(OH)3", "NaCl"), (1, 3, 1, 3)),
    ("X10", DOUBLE, ("BaCl2", "H2SO4"), ("BaSO4", "HCl"), (1, 1, 1, 2)),
    ("X11", DOUBLE, ("Ca(OH)2", "HCl"), ("CaCl2", "H2O"), (1, 2, 1, 2)),
    ("X12", DOUBLE, ("MgCl2", "NaOH"), ("Mg(OH)2", "NaCl"), (1, 2, 1, 2)),
    ("X13", DOUBLE, ("ZnSO4", "Na2CO3"), ("ZnCO3", "Na2SO4"), (1, 1, 1, 1)),
    ("X14", DOUBLE, ("AgNO3", "KBr"), ("AgBr", "KNO3"), (1, 1, 1, 1)),
    ("X15", DOUBLE, ("KOH", "H2SO4"), ("K2SO4", "H2O"), (2, 1, 1, 2)),
    ("X16", DOUBLE, ("Al(OH)3", "HCl"), ("AlCl3", "H2O"), (1, 3, 1, 3)),
    ("X17", DOUBLE, ("Mg(OH)2", "H2SO4"), ("MgSO4", "H2O"), (1, 1, 1, 2)),
)
REACTION_BY_ID = {r[0]: r for r in REACTIONS}

# ---------------------------------------------------------------- ions (school charges)
# symbol-or-group, charge, name, polyatomic
CATIONS: tuple[tuple[str, int, str], ...] = (
    ("Na", 1, "sodium"),
    ("K", 1, "potassium"),
    ("Mg", 2, "magnesium"),
    ("Ca", 2, "calcium"),
    ("Ba", 2, "barium"),
    ("Al", 3, "aluminium"),
    ("Zn", 2, "zinc"),
    ("Cu", 2, "copper(2+)"),
    ("Fe", 2, "iron(2+)"),
    ("Ag", 1, "silver"),
    ("Pb", 2, "lead(2+)"),
    ("NH4", 1, "ammonium"),
)
FE3 = ("Fe", 3, "iron(3+)")
ANIONS: tuple[tuple[str, int, str], ...] = (
    ("Cl", 1, "chloride"),
    ("Br", 1, "bromide"),
    ("O", 2, "oxide"),
    ("S", 2, "sulphide"),
    ("N", 3, "nitride"),
    ("OH", 1, "hydroxide"),
    ("NO3", 1, "nitrate"),
    ("SO4", 2, "sulphate"),
    ("CO3", 2, "carbonate"),
    ("PO4", 3, "phosphate"),
)
POLYATOMIC = {"NH4", "OH", "NO3", "SO4", "CO3", "PO4"}
CATION_BY_NAME = {n: (s, q) for s, q, n in (*CATIONS, FE3)}
ANION_BY_NAME = {n: (s, q) for s, q, n in ANIONS}

# acids: (formula, name, anion group, basicity)
ACIDS: tuple[tuple[str, str, str, int], ...] = (
    ("HCl", "hydrochloric acid", "Cl", 1),
    ("HNO3", "nitric acid", "NO3", 1),
    ("H2SO4", "sulphuric acid", "SO4", 2),
)
# bases: (formula, name, cation, acidity)
BASES: tuple[tuple[str, str, str, int], ...] = (
    ("NaOH", "sodium hydroxide", "Na", 1),
    ("KOH", "potassium hydroxide", "K", 1),
    ("Ca(OH)2", "calcium hydroxide", "Ca", 2),
    ("Mg(OH)2", "magnesium hydroxide", "Mg", 2),
    ("Ba(OH)2", "barium hydroxide", "Ba", 2),
    ("Al(OH)3", "aluminium hydroxide", "Al", 3),
)

# ---------------------------------------------------------------- metals
SCHOOL_SERIES = ("K", "Na", "Ca", "Mg", "Al", "Zn", "Fe", "Pb", "H", "Cu", "Hg", "Ag", "Au")
# standard electrode potentials in volts (rounded standard-table values): cross-check only
E0 = {
    "K": -2.93, "Na": -2.71, "Ca": -2.87, "Mg": -2.37, "Al": -1.66, "Zn": -0.76, "Fe": -0.44,
    "Pb": -0.13, "H": 0.0, "Cu": 0.34, "Hg": 0.85, "Ag": 0.80, "Au": 1.50,
}  # fmt: skip
METAL_NAME = {
    "K": "potassium", "Na": "sodium", "Ca": "calcium", "Mg": "magnesium", "Al": "aluminium",
    "Zn": "zinc", "Fe": "iron", "Pb": "lead", "Cu": "copper", "Ag": "silver", "Au": "gold",
}  # fmt: skip
# metals used in solution displacement items: symbol -> ion charge in the salt used
SOLUTION_METALS = {"Mg": 2, "Al": 3, "Zn": 2, "Fe": 2, "Pb": 2, "Cu": 2, "Ag": 1}
# metals that react with a dilute acid in the lane (above hydrogen, not violent) or do not (below)
ACID_ACTIVE = ("Mg", "Al", "Zn", "Fe")
ACID_INERT = ("Cu", "Ag", "Au")

# ---------------------------------------------------------------- carbon
ROOTS = {
    1: "meth",
    2: "eth",
    3: "prop",
    4: "but",
    5: "pent",
    6: "hex",
    7: "hept",
    8: "oct",
    9: "non",
    10: "dec",
}
# number of structural isomers of the alkane with n carbons: A000602 (cross-check only)
ALKANE_ISOMERS_OEIS = {1: 1, 2: 1, 3: 1, 4: 2, 5: 3, 6: 5, 7: 9, 8: 18, 9: 35, 10: 75}

# Condensed formula -> IUPAC name, written by hand (the lookup method). Each isomer may be written
# in several equivalent ways; the namer must give the same name to all of them.
ALKANE_NAMES: dict[str, str] = {
    "CH4": "methane",
    "CH3-CH3": "ethane",
    "CH3-CH2-CH3": "propane",
    "CH3-CH2-CH2-CH3": "butane",
    "CH3-CH(CH3)-CH3": "2-methylpropane",
    "CH3-CH2-CH2-CH2-CH3": "pentane",
    "CH3-CH(CH3)-CH2-CH3": "2-methylbutane",
    "CH3-CH2-CH(CH3)-CH3": "2-methylbutane",
    "CH3-C(CH3)2-CH3": "2,2-dimethylpropane",
    "CH3-CH2-CH2-CH2-CH2-CH3": "hexane",
    "CH3-CH(CH3)-CH2-CH2-CH3": "2-methylpentane",
    "CH3-CH2-CH(CH3)-CH2-CH3": "3-methylpentane",
    "CH3-CH2-CH2-CH(CH3)-CH3": "2-methylpentane",
    "CH3-C(CH3)2-CH2-CH3": "2,2-dimethylbutane",
    "CH3-CH2-C(CH3)2-CH3": "2,2-dimethylbutane",
    "CH3-CH(CH3)-CH(CH3)-CH3": "2,3-dimethylbutane",
    "CH3-CH2-CH2-CH2-CH2-CH2-CH3": "heptane",
    "CH3-CH(CH3)-CH2-CH2-CH2-CH3": "2-methylhexane",
    "CH3-CH2-CH(CH3)-CH2-CH2-CH3": "3-methylhexane",
    "CH3-CH(CH3)-CH(CH3)-CH2-CH3": "2,3-dimethylpentane",
    "CH3-C(CH3)2-CH2-CH2-CH3": "2,2-dimethylpentane",
    "CH3-CH(CH3)-CH2-CH(CH3)-CH3": "2,4-dimethylpentane",
    "CH3-CH2-C(CH3)2-CH2-CH3": "3,3-dimethylpentane",
    "CH3-CH2-CH(CH2-CH3)-CH2-CH3": "3-ethylpentane",
    "CH3-C(CH3)2-CH(CH3)-CH3": "2,2,3-trimethylbutane",
}
# unsaturated straight chains (no branches): condensed formula -> name
ALKENE_NAMES: dict[str, str] = {
    "CH2=CH2": "ethene",
    "CH2=CH-CH3": "propene",
    "CH2=CH-CH2-CH3": "but-1-ene",
    "CH3-CH=CH-CH3": "but-2-ene",
    "CH2=CH-CH2-CH2-CH3": "pent-1-ene",
    "CH3-CH=CH-CH2-CH3": "pent-2-ene",
    "CH3-CH2-CH=CH-CH3": "pent-2-ene",
    "CH2=CH-CH2-CH2-CH2-CH3": "hex-1-ene",
    "CH3-CH=CH-CH2-CH2-CH3": "hex-2-ene",
    "CH3-CH2-CH=CH-CH2-CH3": "hex-3-ene",
    "CH3-CH2-CH2-CH=CH-CH3": "hex-2-ene",
    "CH3-CH2-CH2-CH2-CH=CH2": "hex-1-ene",
}
ALKYNE_NAMES: dict[str, str] = {
    "CH≡CH": "ethyne",
    "CH≡C-CH3": "propyne",
    "CH≡C-CH2-CH3": "but-1-yne",
    "CH3-C≡C-CH3": "but-2-yne",
    "CH≡C-CH2-CH2-CH3": "pent-1-yne",
    "CH3-C≡C-CH2-CH3": "pent-2-yne",
    "CH3-CH2-C≡CH": "but-1-yne",
    "CH≡C-CH2-CH2-CH2-CH3": "hex-1-yne",
    "CH3-C≡C-CH2-CH2-CH3": "hex-2-yne",
    "CH3-CH2-C≡C-CH2-CH3": "hex-3-yne",
}
# straight-chain compounds with one functional group at the end of the chain:
# group -> {carbons: name}; the condensed formula is built from group and carbons
FUNCTIONAL: dict[str, dict[int, str]] = {
    "alcohol": {1: "methanol", 2: "ethanol", 3: "propan-1-ol", 4: "butan-1-ol", 5: "pentan-1-ol"},
    "aldehyde": {1: "methanal", 2: "ethanal", 3: "propanal", 4: "butanal", 5: "pentanal"},
    "carboxylic acid": {
        1: "methanoic acid", 2: "ethanoic acid", 3: "propanoic acid", 4: "butanoic acid",
        5: "pentanoic acid",
    },
    "haloalkane": {
        1: "chloromethane", 2: "chloroethane", 3: "1-chloropropane", 4: "1-chlorobutane",
        5: "1-chloropentane",
    },
}  # fmt: skip
