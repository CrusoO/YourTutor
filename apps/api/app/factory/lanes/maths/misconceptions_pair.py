# ruff: noqa: E501
"""Named wrong procedures for Pair of Linear Equations in Two Variables. Original wording.

Each id is attached to the wrong options a family builds with that procedure, so the hint and the
review can name the idea. Status is draft: nobody has reviewed these descriptions yet.
"""

from __future__ import annotations

# id -> (title, explanation of the wrong procedure)
PAIR_TEXT: dict[str, tuple[str, str]] = {
    # ---------------- shared slips
    "MC.PAIR.XY_SWAPPED": (
        "Mixes up which value belongs to x and which to y",
        "You may have found both numbers but written them against the wrong letters.",
    ),
    "MC.PAIR.ONE_VARIABLE_ONLY": (
        "Stops after finding one variable",
        "You may have found one unknown and then used the same number for the other one.",
    ),
    # ---------------- reading the graph from computed data
    "MC.PAIR.GRAPH_INTERCEPT_FOR_MEET": (
        "Reads where a line meets the y-axis as the meeting point",
        "You may have taken the point where one line cuts the y-axis. The two lines meet where both of them give the same point.",
    ),
    "MC.PAIR.GRAPH_ONE_LINE_POINT": (
        "Gives a point that lies on only one of the lines",
        "You may have picked a listed point of one line. The meeting point has to lie on both lines.",
    ),
    "MC.PAIR.GRAPH_OTHER_LINE_POINT": (
        "Gives a listed point of the second line",
        "You may have picked a listed point of the other line. A meeting point lies on both lines, not just one.",
    ),
    # ---------------- deciding the kind of solution
    "MC.PAIR.TYPE_CONSTANT_RATIO_IGNORED": (
        "Compares only the coefficients and skips the constants",
        "You may have seen that the x and y coefficients are in the same ratio and stopped. The constants decide between parallel and identical lines.",
    ),
    "MC.PAIR.TYPE_COINCIDENT_AS_PARALLEL": (
        "Calls identical lines parallel",
        "You may have seen equal ratios and said the lines never meet. When the constants match too, every point is shared.",
    ),
    "MC.PAIR.TYPE_ONE_AS_NONE": (
        "Thinks different-looking lines can never meet",
        "You may have expected two lines with different numbers never to meet. Lines meet once unless their directions are the same.",
    ),
    "MC.PAIR.TYPE_ONE_AS_INFINITE": (
        "Calls lines that cut each other the same line",
        "You may have taken a shared look or a shared factor for the same line. Compare the ratios of the coefficients.",
    ),
    "MC.PAIR.TYPE_RATIOS_NOT_COMPARED": (
        "Says the lines meet without comparing the ratios",
        "You may have assumed two lines always cross. They cross once only when the ratios of the x and y coefficients differ.",
    ),
    "MC.PAIR.TYPE_TWO_MEETING_POINTS": (
        "Thinks two straight lines can meet at two points",
        "Two different straight lines meet at one point, or never, or they are the same line.",
    ),
    # ---------------- finding k
    "MC.PAIR.K_RATIO_UPSIDE_DOWN": (
        "Turns one of the ratios upside down",
        "You may have written one ratio the wrong way up before cross-multiplying.",
    ),
    "MC.PAIR.K_WRONG_RATIO_USED": (
        "Uses the ratio of the constants to find k",
        "You may have equated the wrong pair of ratios. Use the ratio that holds k's own line.",
    ),
    "MC.PAIR.K_ADDITIVE_INSTEAD_OF_RATIO": (
        "Compares differences instead of ratios",
        "You may have kept the gap between the coefficients the same. The condition is about equal ratios, not equal gaps.",
    ),
    "MC.PAIR.K_SIGN_SLIP": (
        "Loses a minus sign while solving for k",
        "You may have the right size for k but the wrong sign.",
    ),
    "MC.PAIR.K_EQUAL_TO_OTHER_CONSTANT": (
        "Copies the other constant into k",
        "You may have assumed the missing number equals the matching number in the first line.",
    ),
    # ---------------- substitution
    "MC.PAIR.SUBST_NOT_DISTRIBUTED": (
        "Does not multiply the whole expression when substituting",
        "You may have put the expression in but multiplied only its first term by the coefficient.",
    ),
    "MC.PAIR.SUBST_SIGN_SLIP": (
        "Loses a sign when working the second unknown back out",
        "You may have found the first unknown correctly and then reversed one sign when substituting back.",
    ),
    "MC.PAIR.SUBST_ISOLATE_SIGN": (
        "Gets the sign wrong when writing one variable alone",
        "You may have moved a term to the other side without reversing its sign.",
    ),
    # ---------------- elimination
    "MC.PAIR.ELIM_SIGN_SLIP": (
        "Subtracts equations but not the whole of the second one",
        "You may have changed the sign of the first term of the second equation and forgotten the other terms.",
    ),
    "MC.PAIR.ELIM_ADD_NOT_SUBTRACT": (
        "Adds when the terms need subtracting",
        "You may have added two equations whose coefficients have the same sign, so nothing cancelled.",
    ),
    "MC.PAIR.ELIM_SUBTRACT_NOT_ADD": (
        "Subtracts when the terms need adding",
        "You may have subtracted two equations whose coefficients have opposite signs, so nothing cancelled.",
    ),
    "MC.PAIR.ELIM_SCALE_PARTIAL": (
        "Multiplies only some terms of an equation",
        "You may have multiplied the left side by a number and left the right side, or one term, as it was.",
    ),
    "MC.PAIR.ELIM_DIVIDED_ONE_TERM": (
        "Divides only one term",
        "You may have divided one term by the coefficient and left the other terms of that line unchanged.",
    ),
    # ---------------- cross-multiplication
    "MC.PAIR.CROSS_CONSTANT_SIGN": (
        "Uses the constants with the wrong sign",
        "You may have put the constant terms into the formula as they stand on the right of the equals sign instead of on the left.",
    ),
    "MC.PAIR.CROSS_NUMERATOR_ORDER": (
        "Subtracts the products in the wrong order",
        "You may have taken the two products of one numerator the wrong way round.",
    ),
    "MC.PAIR.CROSS_PAIRING_SLIP": (
        "Pairs the wrong numbers in the products",
        "You may have multiplied numbers from the same equation instead of numbers from different equations.",
    ),
    "MC.PAIR.CROSS_DENOM_ADDED": (
        "Adds the two products in the denominator",
        "You may have added the products that the formula subtracts.",
    ),
    # ---------------- word problems
    "MC.PAIR.WORD_ASKED_OTHER_UNKNOWN": (
        "Answers for the other unknown",
        "You may have solved the pair well and then reported the quantity that was not asked for.",
    ),
    "MC.PAIR.WORD_AGES_FUTURE_REPORTED": (
        "Reports an age at the later time",
        "You may have given the age after the stated years instead of the present age.",
    ),
    "MC.PAIR.WORD_AGES_SIGN_OF_TIME": (
        "Adds the years when they should be taken away, or the other way round",
        "You may have used later ages for a statement about the past, or earlier ages for the future.",
    ),
    "MC.PAIR.WORD_FRACTION_ROLES_SWAPPED": (
        "Swaps the numerator and the denominator",
        "You may have found both numbers and written the fraction upside down.",
    ),
    "MC.PAIR.WORD_FRACTION_REPORTED_NEW": (
        "Gives the new fraction instead of the original",
        "You may have stopped at the fraction the question says it becomes.",
    ),
    "MC.PAIR.WORD_FRACTION_CHANGE_MISPLACED": (
        "Applies the change to the wrong part of the fraction",
        "You may have added to the denominator what should be added to the numerator, or the other way round.",
    ),
    "MC.PAIR.WORD_STREAM_REVERSED": (
        "Swaps upstream and downstream",
        "You may have taken the stream as helping on the way up and slowing the trip down.",
    ),
    "MC.PAIR.WORD_STREAM_AVERAGE": (
        "Uses total distance over total time as the boat speed",
        "You may have averaged the two trips, but the stream helps one trip and hurts the other.",
    ),
    "MC.PAIR.WORD_COST_COUNTS_SWAPPED": (
        "Attaches the counts to the wrong items",
        "You may have multiplied the number of pens by the price of a notebook and the other way round.",
    ),
    "MC.PAIR.WORD_COST_AVERAGE": (
        "Divides the total bill by the number of things bought",
        "You may have found an average price. The two items have different prices.",
    ),
    "MC.PAIR.WORD_RECT_PERIMETER_AS_SUM": (
        "Uses the perimeter as length plus width",
        "You may have forgotten that the perimeter counts each side, so length plus width is half of it.",
    ),
    "MC.PAIR.WORD_RECT_AREA_AS_SUM": (
        "Adds length and width when asked for the area",
        "You may have found both sides and then added them instead of multiplying.",
    ),
    "MC.PAIR.WORD_AGES_RATIO_FLIPPED": (
        "Puts the multiplier on the wrong person",
        "You may have written the younger person's age as the multiple of the older person's age.",
    ),
    "MC.PAIR.WORD_STREAM_NOT_HALVED": (
        "Forgets to halve when combining the two speeds",
        "You may have added or subtracted the two trip speeds and not divided by two.",
    ),
    "MC.PAIR.WORD_RECT_STOPPED_AT_SEMIPERIMETER": (
        "Stops at half the perimeter",
        "You may have found length plus width and reported it as one of the sides.",
    ),
    "MC.PAIR.WORD_RECT_MORE_THAN_AS_LESS": (
        "Reads more than as less than",
        "You may have taken the extra length as being taken away from a multiple of the width.",
    ),
    # ---------------- equations that reduce to a pair of linear equations
    "MC.PAIR.RECIP_ANSWER_IS_RECIPROCAL": (
        "Stops at the reciprocals",
        "You may have solved for 1/x and 1/y and written those as x and y.",
    ),
    "MC.PAIR.RECIP_ONE_NOT_INVERTED": (
        "Turns only one reciprocal back",
        "You may have inverted one of the two values and left the other as it was.",
    ),
    "MC.PAIR.RECIP_TREATED_AS_LINEAR": (
        "Treats a number over x as a number times x",
        "You may have read each term as if x and y were not in the denominator.",
    ),
    "MC.PAIR.RECIP_SUMDIFF_STOPPED_EARLY": (
        "Stops at x + y and x - y",
        "You may have found the values of x + y and x - y and reported them as x and y.",
    ),
    "MC.PAIR.RECIP_SUMDIFF_NOT_HALVED": (
        "Forgets to halve",
        "You may have added x + y and x - y and not divided by two.",
    ),
    "MC.PAIR.RECIP_SUMDIFF_SIGN_OF_Y": (
        "Takes the difference the wrong way round for y",
        "You may have taken x - y minus x + y when finding y.",
    ),
}
