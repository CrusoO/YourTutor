# ruff: noqa: E501
"""Named wrong procedures (misconceptions) of the chemistry lane: id -> (title, explanation).

All wording is original. Explanations speak to the learner in the second person and never give the
answer of any item. Every id used by a family must have an entry here (a test enforces it).
"""

from __future__ import annotations

from app.factory.lanes.chemistry.balance import TYPE_RULE, type_mc
from app.factory.lanes.chemistry.tables import TYPES

TEXT: dict[str, tuple[str, str]] = {
    # atoms and equations
    "CHEM.MC.ATOM.BRACKET_AND_COEFFICIENT_IGNORED": (
        "Counts only the atoms written inside the bracket",
        "You may have ignored both the number after the bracket and the number in front. Both multiply the atoms.",
    ),
    "CHEM.MC.ATOM.BRACKET_IGNORED": (
        "Ignores the number after a bracket",
        "You may have forgotten that the small number after a bracket multiplies every atom inside it.",
    ),
    "CHEM.MC.ATOM.COEFFICIENT_ADDED": (
        "Adds the number in front instead of multiplying",
        "You may have added the big number in front. It tells you how many units there are, so it multiplies.",
    ),
    "CHEM.MC.ATOM.COEFFICIENT_IGNORED": (
        "Leaves out the number in front of the formula",
        "You may have counted one unit only. The number in front says how many units there are.",
    ),
    "CHEM.MC.BAL.COEFFICIENTS_NOT_ADDED": (
        "Counts the formulas instead of adding the coefficients",
        "You may have counted how many substances appear. Add the numbers written in front of them instead.",
    ),
    "CHEM.MC.BAL.COEFFICIENTS_SWAPPED": (
        "Puts the coefficients in the wrong order",
        "You may have used the right numbers but put them in front of the wrong formulas. Recount the atoms.",
    ),
    "CHEM.MC.BAL.NOTHING_CHANGED": (
        "Leaves the equation unbalanced",
        "You may have copied the skeleton equation. Count the atoms of each element on both sides first.",
    ),
    "CHEM.MC.BAL.NOT_SMALLEST": (
        "Uses numbers that are not the smallest whole numbers",
        "You may have a balanced equation that can be divided by a common factor. Use the smallest whole numbers.",
    ),
    "CHEM.MC.BAL.ONE_COEFFICIENT_OFF": (
        "Balances almost, with one number wrong",
        "You may have one coefficient too big or too small. Recount every element after you choose the numbers.",
    ),
    "CHEM.MC.BAL.ONE_SIDE_ONLY": (
        "Adds the coefficients of one side only",
        "You may have added only the left or only the right side. The question asks for all of them.",
    ),
    "CHEM.MC.BAL.OXYGEN_ATOMS_ONLY_ON_ONE_SIDE": (
        "Counts oxygen from one product only",
        "You may have counted oxygen from one product only. Both products contain oxygen.",
    ),
    "CHEM.MC.BAL.SUBSCRIPT_AS_COEFFICIENT": (
        "Uses a subscript as the coefficient",
        "You may have used a small number inside the formula. The coefficient is the number in front of the formula.",
    ),
    "CHEM.MC.BAL.SUBSCRIPT_CHANGED": (
        "Changes a formula to balance an equation",
        "You may have changed a small number inside a formula. That makes a different substance. Change the numbers in front instead.",
    ),
    "CHEM.MC.BAL.WRONG_SPECIES_READ": (
        "Reads the coefficient of a different substance",
        "You may have read the number for the neighbouring formula. Check which formula the question names.",
    ),
    # reaction types
    # pH
    "CHEM.MC.PH.CONCENTRATION_READ_AS_PH": (
        "Uses the concentration number as the pH",
        "You may have turned the power of ten into an ordinary number. The pH is the power with its sign changed.",
    ),
    "CHEM.MC.PH.DIFFERENCE_NOT_POWER": (
        "Gives the pH difference instead of the factor",
        "You may have stopped at the difference of the two pH values. Each unit is a factor of ten, so use powers of ten.",
    ),
    "CHEM.MC.PH.DILUTION_DIRECTION_REVERSED": (
        "Moves the pH the wrong way on dilution",
        "You may have moved the pH away from 7. Adding water moves the pH towards 7.",
    ),
    "CHEM.MC.PH.FACTOR_ADDED_TO_PH": (
        "Adds the dilution factor to the pH",
        "You may have added the number of times the volume grew. Each ten times is only one pH unit.",
    ),
    "CHEM.MC.PH.IONS_PER_FORMULA_IGNORED": (
        "Ignores how many ions one unit gives",
        "You may have used the stated concentration directly. A unit that gives two ions doubles the ion concentration.",
    ),
    "CHEM.MC.PH.NEEDS_NAME_OF_SUBSTANCE": (
        "Thinks the character of a solution depends on the substance name",
        "You may have looked for the substance. The pH number alone tells you whether a solution is acidic, neutral or basic.",
    ),
    "CHEM.MC.PH.NEUTRAL_POINT_MISPLACED": (
        "Puts the neutral point in the wrong place",
        "You may have used a different number as the neutral point. At room temperature the neutral pH is 7.",
    ),
    "CHEM.MC.PH.NO_CHANGE_ON_DILUTION": (
        "Thinks dilution leaves the pH unchanged",
        "You may have forgotten that adding water lowers the ion concentration, which changes the pH.",
    ),
    "CHEM.MC.PH.OH_FOR_H": (
        "Mixes up hydrogen and hydroxide ions",
        "You may have used the wrong ion. pH belongs to hydrogen ions and pOH to hydroxide ions.",
    ),
    "CHEM.MC.PH.PH_PLUS_POH_NOT_14": (
        "Does not use the total of pH and pOH correctly",
        "You may have added instead of subtracting from the fixed total of pH and pOH.",
    ),
    "CHEM.MC.PH.PH_READ_AS_CONCENTRATION": (
        "Writes the pH as a concentration",
        "You may have written the pH number with a concentration unit. The concentration is a power of ten.",
    ),
    "CHEM.MC.PH.PH_SCALED_BY_FACTOR": (
        "Multiplies the pH by the dilution factor",
        "You may have multiplied the pH. The pH is a logarithm, so a factor moves it by a fixed step.",
    ),
    "CHEM.MC.PH.POH_REPORTED_AS_PH": (
        "Reports the pOH as the pH",
        "You may have stopped at the pOH. Turn it into a pH using the fixed total of pH and pOH.",
    ),
    "CHEM.MC.PH.POH_SAME_AS_PH": (
        "Thinks pOH equals pH",
        "You may have copied the pH. The pOH is a different number that together with the pH makes a fixed total.",
    ),
    "CHEM.MC.PH.POWER_MISCOUNT": (
        "Miscounts the power of ten by one",
        "You may have counted one place too many or too few. Check the power carefully.",
    ),
    "CHEM.MC.PH.RATIO_INVERTED": (
        "Turns the ratio upside down",
        "You may have written the smaller concentration over the larger. Check which solution has more hydrogen ions.",
    ),
    "CHEM.MC.PH.RATIO_OF_PH_VALUES": (
        "Divides the pH values",
        "You may have divided one pH by the other. The pH scale is a logarithm scale, so look at the difference.",
    ),
    "CHEM.MC.PH.SCALE_READ_BACKWARDS": (
        "Reads the pH scale backwards",
        "You may have reversed the scale. Low pH values are acidic and high pH values are basic.",
    ),
    "CHEM.MC.PH.SEVEN_USED": (
        "Uses 7 where the fixed total of 14 belongs",
        "You may have used the neutral point 7 in a calculation that needs the fixed total of pH and pOH.",
    ),
    "CHEM.MC.PH.SIGN_OF_EXPONENT_DROPPED": (
        "Drops the minus sign of the power",
        "You may have written a positive power. These solutions are dilute, so the power is negative.",
    ),
    "CHEM.MC.PH.SIGN_OF_EXPONENT_KEPT": (
        "Keeps the minus sign in the pH",
        "You may have copied the power with its sign. The pH is the power with its sign changed.",
    ),
    "CHEM.MC.PH.TIMES_TEN_PER_UNIT": (
        "Multiplies the pH difference by 10",
        "You may have multiplied by ten once. A change of one pH unit is a factor of ten, and each extra unit multiplies by ten again.",
    ),
    # neutralisation
    "CHEM.MC.NEUT.ACID_BASICITY_IGNORED": (
        "Ignores how many hydrogen ions an acid unit gives",
        "You may have treated every acid as giving one hydrogen ion. Check the formula of the acid.",
    ),
    "CHEM.MC.NEUT.BASE_ACIDITY_IGNORED": (
        "Ignores how many hydroxide ions a base unit gives",
        "You may have treated every base as giving one hydroxide ion. Check the formula of the base.",
    ),
    "CHEM.MC.NEUT.BASICITY_RATIO_INVERTED": (
        "Swaps the ion counts of acid and base",
        "You may have put the acid's ion count where the base's belongs, and the other way round.",
    ),
    "CHEM.MC.NEUT.CONCENTRATION_RATIO_INVERTED": (
        "Turns the concentration ratio upside down",
        "You may have divided by the acid's concentration instead of the base's.",
    ),
    "CHEM.MC.NEUT.ACID_MILLIMOLES_GIVEN": (
        "Stops before dividing by the base concentration",
        "You may have found the amount of acid and stopped. The volume of base still has to be found from its concentration.",
    ),
    "CHEM.MC.NEUT.TOTAL_VOLUME_GIVEN": (
        "Gives the total volume of the mixture",
        "You may have added the two volumes. The question asks only for the volume of the base solution.",
    ),
    "CHEM.MC.NEUT.EQUAL_VOLUMES_ASSUMED": (
        "Assumes equal volumes neutralise",
        "You may have assumed the same volume of base is needed. That is true only when everything else is equal.",
    ),
    # salts
    "CHEM.MC.SALT.ACID_FORMULA_GIVEN": (
        "Gives the acid instead of the salt",
        "You may have named a reactant. The salt is a product made from ions of the acid and the base.",
    ),
    "CHEM.MC.SALT.BASE_FORMULA_GIVEN": (
        "Gives the base instead of the salt",
        "You may have named a reactant. The salt is a product made from ions of the acid and the base.",
    ),
    "CHEM.MC.SALT.BRACKET_MISSING": (
        "Leaves out the bracket round a group",
        "You may have written a subscript that belongs to a whole group of atoms without a bracket.",
    ),
    "CHEM.MC.SALT.CHARGES_IGNORED": (
        "Ignores the charges of the ions",
        "You may have written one of each ion. The charges must cancel, so check them.",
    ),
    "CHEM.MC.SALT.CHARGE_AS_OWN_SUBSCRIPT": (
        "Writes each charge as a subscript on its own ion",
        "You may have put each ion's charge number on the same ion. The charge numbers are swapped.",
    ),
    "CHEM.MC.SALT.NOT_REDUCED": (
        "Does not reduce the ion counts",
        "You may have a correct ratio that can be divided by a common factor. Use the smallest whole numbers.",
    ),
    "CHEM.MC.SALT.SUBSCRIPTS_SWAPPED": (
        "Puts the swapped numbers on the wrong ions",
        "You may have put the numbers on the wrong ions. Each ion's charge number goes to the other ion.",
    ),
    # stoichiometry
    "CHEM.MC.STOICH.BRACKET_IN_MOLAR_MASS": (
        "Forgets the bracket multiplier in a molar mass",
        "You may have counted the atoms inside a bracket once. The number after the bracket multiplies them.",
    ),
    "CHEM.MC.STOICH.MASS_NOT_CONVERTED": (
        "Uses mass where moles are needed",
        "You may have used the given mass as if it were an amount in moles. Divide by the molar mass first.",
    ),
    "CHEM.MC.STOICH.MOLE_RATIO_IGNORED": (
        "Ignores the ratio of the coefficients",
        "You may have assumed the substances react one to one. Use the coefficients of the balanced equation.",
    ),
    "CHEM.MC.STOICH.ONE_MOLE_ASSUMED": (
        "Gives the result for one mole",
        "You may have found the amount for one mole of the given substance. Use the quantity stated in the question.",
    ),
    "CHEM.MC.STOICH.RATIO_INVERTED": (
        "Inverts the ratio of the coefficients",
        "You may have divided by the wanted substance's coefficient. Wanted goes on the top, given on the bottom.",
    ),
    "CHEM.MC.STOICH.WRONG_MOLAR_MASS": (
        "Uses the molar mass of the wrong substance",
        "You may have used the molar mass of the given substance for the answer. Use the substance you are asked about.",
    ),
    # metals
    "CHEM.MC.METAL.ABOVE_HYDROGEN_INERT": (
        "Thinks metals above hydrogen do not react with acid",
        "You may have mixed up the order. Metals above hydrogen in the series do release hydrogen from a dilute acid.",
    ),
    "CHEM.MC.METAL.BELOW_HYDROGEN_REACTS": (
        "Thinks every metal gives hydrogen with acid",
        "You may have assumed all metals react. Metals below hydrogen in the series do not.",
    ),
    "CHEM.MC.METAL.LESS_REACTIVE_DISPLACES": (
        "Lets a less reactive metal displace a more reactive one",
        "You may have turned the order round. Only the more reactive metal can displace the other.",
    ),
    "CHEM.MC.METAL.MIDDLE_OF_SERIES_PICKED": (
        "Picks a metal from the middle of the series",
        "You may not have compared all four metals. Find the highest or lowest position in the series.",
    ),
    "CHEM.MC.METAL.MORE_REACTIVE_DOES_NOT_DISPLACE": (
        "Thinks a more reactive metal cannot displace another",
        "You may have turned the order round. A metal higher in the series does displace one lower down.",
    ),
    "CHEM.MC.METAL.ROLES_REVERSED": (
        "Swaps which metal is added and which is in the solution",
        "You may have turned the two metals round. The metal that is added is the one that has to be more reactive.",
    ),
    "CHEM.MC.METAL.HYDROGEN_ALWAYS_RELEASED": (
        "Thinks hydrogen is released whenever a metal reacts",
        "You may have remembered metals with acids. Here the metal replaces another metal, not hydrogen.",
    ),
    "CHEM.MC.METAL.WRONG_GAS_NAMED": (
        "Names the wrong gas",
        "You may have named oxygen. The gas given off when a metal reacts with a dilute acid is hydrogen.",
    ),
    "CHEM.MC.METAL.METAL_TREATED_AS_BASE": (
        "Treats the metal as a base",
        "You may have thought a metal neutralises an acid. A metal reacts differently from a base.",
    ),
    "CHEM.MC.METAL.ORDER_REVERSED": (
        "Reads the reactivity series upside down",
        "You may have read the series from the wrong end. The most reactive metal is at the top.",
    ),
    # ionic
    "CHEM.MC.IONIC.ANION_WRITTEN_FIRST": (
        "Writes the negative ion first",
        "You may have followed the order of the ions in the wrong way. The positive ion is written first.",
    ),
    "CHEM.MC.IONIC.BRACKET_MISSING": (
        "Leaves out the bracket round a group",
        "You may have written a subscript that belongs to a whole group of atoms without a bracket.",
    ),
    "CHEM.MC.IONIC.CHARGES_IGNORED": (
        "Ignores the charges of the ions",
        "You may have written one of each ion. The charges must cancel, so check them.",
    ),
    "CHEM.MC.IONIC.CHARGES_WRITTEN_IN_FORMULA": (
        "Writes the charges inside the formula",
        "You may have written the charge signs in the formula. A formula shows the number of atoms, not the charges.",
    ),
    "CHEM.MC.IONIC.CHARGE_AS_OWN_SUBSCRIPT": (
        "Writes each charge as a subscript on its own ion",
        "You may have put each ion's charge number on the same ion. The charge numbers are swapped.",
    ),
    "CHEM.MC.IONIC.NOT_REDUCED": (
        "Does not reduce the ion counts",
        "You may have a correct ratio that can be divided by a common factor. Use the smallest whole numbers.",
    ),
    "CHEM.MC.IONIC.SUBSCRIPTS_SWAPPED": (
        "Puts the swapped numbers on the wrong ions",
        "You may have put the numbers on the wrong ions. Each ion's charge number goes to the other ion.",
    ),
    # carbon
    "CHEM.MC.ISO.NEIGHBOUR_FORMULA_COUNT": (
        "Gives the isomer count of a neighbouring compound",
        "You may have remembered the number for a different number of carbon atoms. Count for this formula.",
    ),
    "CHEM.MC.ISO.ONE_ISOMER_MISSED": (
        "Misses or invents one isomer",
        "You may have counted one skeleton twice or missed one. Check each shorter-chain arrangement once.",
    ),
    "CHEM.MC.ISO.ONLY_STRAIGHT_CHAIN_COUNTED": (
        "Counts only the straight chain",
        "You may have forgotten that a chain can have branches. Shorter main chains with branches are different isomers.",
    ),
    "CHEM.MC.ISO.POSITIONS_COUNTED_AS_ISOMERS": (
        "Counts positions instead of different structures",
        "You may have counted the places to attach a branch. Different places can give the same structure.",
    ),
    "CHEM.MC.NAME.BRANCH_COUNTED_IN_CHAIN": (
        "Names the compound as the straight chain",
        "You may have counted all the carbon atoms as one chain. Look for the longest unbroken chain.",
    ),
    "CHEM.MC.NAME.CARBON_MISCOUNT": (
        "Counts the carbon atoms wrongly",
        "You may have counted one carbon too many or too few. Count again along the chain.",
    ),
    "CHEM.MC.NAME.GROUP_CARBON_NOT_COUNTED": (
        "Leaves out the carbon of the end group",
        "You may have not counted the carbon inside a group such as CHO or COOH. It belongs to the chain.",
    ),
    "CHEM.MC.NAME.GROUP_SUFFIX_MIXED": (
        "Uses the ending of a different group",
        "You may have used the ending of another group. Check which group is at the end of the chain.",
    ),
    "CHEM.MC.NAME.MULTIPLIER_DROPPED": (
        "Leaves out di or tri",
        "You may have forgotten the word that says how many identical groups there are.",
    ),
    "CHEM.MC.NAME.NUMBERED_FROM_WRONG_END": (
        "Numbers the chain from the wrong end",
        "You may have started numbering at the end that gives the larger numbers. Choose the end that gives lower numbers.",
    ),
    "CHEM.MC.NAME.POSITION_OF_BOND_NOT_GIVEN": (
        "Leaves out the position of the multiple bond",
        "You may have written the parent name and ending only. Longer chains need the position of the bond.",
    ),
    "CHEM.MC.NAME.SUFFIX_MIXED": (
        "Uses the wrong ending for the bond type",
        "You may have used the ending for single, double or triple bonds the wrong way round.",
    ),
    "CHEM.MC.NAME.WRONG_ISOMER": (
        "Names a different isomer",
        "You may have given the name of another compound with the same number of carbon atoms. Check the branches.",
    ),
    "CHEM.MC.SERIES.ATOMS_COUNTED_AS_BONDS": (
        "Counts atoms instead of bonds",
        "You may have added up the atoms. Count the bonds between the atoms instead.",
    ),
    "CHEM.MC.SERIES.ATOMS_COUNTED_AS_MASS": (
        "Counts atoms instead of adding masses",
        "You may have counted the atoms. Multiply each count by the atomic mass first.",
    ),
    "CHEM.MC.SERIES.CARBON_COUNT_COPIED": (
        "Copies the number of carbon atoms",
        "You may have repeated the number given. Use the general formula to find the other count.",
    ),
    "CHEM.MC.SERIES.CARBON_MASS_ONLY": (
        "Counts the mass of carbon only",
        "You may have left out the hydrogen atoms. They add mass too.",
    ),
    "CHEM.MC.SERIES.HALF_ONLY": (
        "Halves the hydrogen count only",
        "You may have divided by two without first removing the constant term of the general formula.",
    ),
    "CHEM.MC.SERIES.HYDROGEN_COUNT_COPIED": (
        "Copies the hydrogen count",
        "You may have repeated the number given. The question asks for the carbon atoms.",
    ),
    "CHEM.MC.SERIES.HYDROGEN_MASS_FORGOTTEN_FACTOR": (
        "Counts one carbon only",
        "You may have used one carbon atom instead of all of them.",
    ),
    "CHEM.MC.SERIES.MULTIPLE_BOND_COUNTED_ONCE": (
        "Counts a double or triple bond as one bond",
        "You may have counted every line between two atoms once. A double bond counts as two and a triple bond as three.",
    ),
    "CHEM.MC.SERIES.N_PLUS_TWO": (
        "Adds two to the carbon count",
        "You may have used n + 2. The general formula has 2n, not n.",
    ),
    "CHEM.MC.SERIES.ONE_BOND_OFF": (
        "Is out by one",
        "You may have counted one too many or too few. Recount using the general formula.",
    ),
    "CHEM.MC.SERIES.ONLY_C_C_BONDS_COUNTED": (
        "Counts only the carbon-carbon bonds",
        "You may have left out the bonds to hydrogen. Every hydrogen atom forms a bond.",
    ),
    "CHEM.MC.SERIES.ONLY_C_H_BONDS_COUNTED": (
        "Counts only the carbon-hydrogen bonds",
        "You may have left out the bonds between carbon atoms in the chain.",
    ),
    "CHEM.MC.SERIES.RADICAL_FORMULA_USED": (
        "Uses a formula that is not for a whole molecule",
        "You may have used a formula with an odd number of hydrogen atoms. A whole hydrocarbon molecule follows one of the three formulas.",
    ),
    "CHEM.MC.SERIES.TWICE_N_ONLY": (
        "Uses twice the carbon count only",
        "You may have used 2n for every series. Each series has its own constant.",
    ),
    "CHEM.MC.SERIES.WRONG_SERIES_FORMULA": (
        "Uses the formula of a different series",
        "You may have used the general formula of another series. Check which one fits.",
    ),
}

_LABEL = {
    "combination": "combination",
    "decomposition": "decomposition",
    "displacement": "displacement",
    "double displacement": "double displacement",
}
for _key in TYPES:
    for _other in TYPES:
        if _key != _other:
            TEXT[type_mc(_key, _other)] = (
                f"Calls a {_LABEL[_key]} reaction a {_LABEL[_other]} reaction",
                f"You may have chosen {_LABEL[_other]}. In a {_LABEL[_key]} reaction, {TYPE_RULE[_key]}.",
            )

REMEDIAL_PREFIX = (
    ("CHEM.MC.ATOM.", "CHEM.RXN.ATOM_COUNT"),
    ("CHEM.MC.BAL.", "CHEM.RXN.BALANCE"),
    ("CHEM.MC.TYPE.", "CHEM.RXN.TYPE"),
    ("CHEM.MC.PH.", "CHEM.ACID.PH_CONVERSION"),
    ("CHEM.MC.NEUT.", "CHEM.ACID.NEUTRAL_VOLUME"),
    ("CHEM.MC.SALT.", "CHEM.ACID.SALT_FORMULA"),
    ("CHEM.MC.STOICH.", "CHEM.ACID.NEUTRAL_MASS"),
    ("CHEM.MC.METAL.", "CHEM.METAL.DISPLACEMENT"),
    ("CHEM.MC.IONIC.", "CHEM.METAL.IONIC_FORMULA"),
    ("CHEM.MC.ISO.", "CHEM.CARBON.ISOMER_COUNT"),
    ("CHEM.MC.NAME.", "CHEM.CARBON.NAME_ALKANE"),
    ("CHEM.MC.SERIES.", "CHEM.CARBON.SERIES_FORMULA"),
)


def remedial_skill(mc_id: str) -> str:
    for prefix, skill in REMEDIAL_PREFIX:
        if mc_id.startswith(prefix):
            return skill
    raise KeyError(mc_id)
