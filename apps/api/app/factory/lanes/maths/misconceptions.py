# ruff: noqa: E501
"""Named wrong procedures (misconceptions) for the Class 10 maths lane. Original wording.

Each id is attached to the wrong options a family builds with that procedure, so a wrong answer
can be explained by what the student likely did, not only marked wrong. Status is draft: nobody
has reviewed these descriptions yet.
"""

from __future__ import annotations

# id -> (title, explanation of the wrong procedure)
TEXT: dict[str, tuple[str, str]] = {
    # ---------------- Quadratic equations
    "MC.QUAD.STD_RHS_IGNORED": (
        "Ignores the right-hand side when collecting",
        "The student reads the coefficient from the left side and never takes the right-hand terms away.",
    ),
    "MC.QUAD.STD_TERM_ADDED": (
        "Adds the right-hand term instead of removing it",
        "To clear the right side the student adds its term to the left side, so the coefficient moves the wrong way.",
    ),
    "MC.QUAD.STD_SIGN_NEGATED": (
        "Reverses the sign of the coefficient",
        "The student collects correctly but reports the opposite sign.",
    ),
    "MC.QUAD.STD_COEFF_POSITION_MIXED": (
        "Reads the wrong coefficient",
        "The student picks the coefficient that sits next to the one asked for.",
    ),
    "MC.QUAD.CHECK_SIGN_FLIPPED": (
        "Offers the opposite of a root",
        "The student takes the number inside a bracket as the root without changing its sign.",
    ),
    "MC.QUAD.CHECK_CONSTANT_TERM_USED": (
        "Offers the constant term as a root",
        "The student assumes the plain number in the equation must be a solution.",
    ),
    "MC.QUAD.CHECK_ONE_OFF": (
        "Offers a value next to a root",
        "The student is close to a root but off by one and does not test by substituting.",
    ),
    "MC.QUAD.CHECK_COEFFICIENT_USED": (
        "Offers a coefficient as a root",
        "The student treats a coefficient of the equation as if it were a solution.",
    ),
    "MC.QUAD.PURE_PLUS_ONLY": (
        "Takes only the positive square root",
        "After isolating the squared term the student gives only the positive root.",
    ),
    "MC.QUAD.PURE_FORGOT_SQRT": (
        "Forgets to take the square root",
        "The student stops at the value of x squared and reports it as x.",
    ),
    "MC.QUAD.PURE_MULTIPLIED_NOT_DIVIDED": (
        "Multiplies by the leading coefficient instead of dividing",
        "To isolate the squared term the student multiplies by its coefficient, which does not undo it.",
    ),
    "MC.QUAD.PURE_NO_REAL_ROOTS": (
        "Declares no solution by mistake",
        "A sign slip when moving the plain number makes the student think the square is negative.",
    ),
    "MC.QUAD.PURE_SIGN_IGNORED": (
        "Ignores that a square cannot be negative",
        "The student takes the square root of a negative number as if it were positive.",
    ),
    "MC.QUAD.PURE_ONE_NEGATIVE_ROOT": (
        "Gives a single negative root for a negative square",
        "The student believes the square root of a negative number is negative.",
    ),
    "MC.QUAD.PURE_ONE_POSITIVE_ROOT": (
        "Gives a single positive root for a negative square",
        "The student drops the minus sign and reports one positive root.",
    ),
    "MC.QUAD.PURE_ZERO_ROOT": (
        "Reports zero as the only solution",
        "The student guesses that the only way to satisfy the equation is x = 0.",
    ),
    "MC.QUAD.DIVIDED_BY_X_LOST_ROOT": (
        "Divides by x and loses a root",
        "Dividing both sides by x removes the solution x = 0.",
    ),
    "MC.QUAD.ONE_FACTOR_ONLY": (
        "Solves from one factor only",
        "The student sets only the x factor to zero and ignores the bracket.",
    ),
    "MC.QUAD.FACTOR_SIGN_SLIP": (
        "Wrong sign on the second root",
        "The student gets the factor right but writes the second root with the opposite sign.",
    ),
    "MC.QUAD.SECOND_ROOT_SIGN_ONLY": (
        "Reports only the second root with its sign changed",
        "The student loses the zero root and flips the sign of the other.",
    ),
    "MC.QUAD.FACTOR_SIGN_READ": (
        "Reads roots straight from the brackets",
        "The student takes the number inside each bracket as the root without undoing the addition or subtraction.",
    ),
    "MC.QUAD.FACTOR_ONE_SIGN": (
        "Changes the sign of only one root",
        "The student undoes one bracket correctly and reads the other one straight.",
    ),
    "MC.QUAD.FACTOR_ONE_ROOT_ONLY": (
        "Stops after one root",
        "The student solves one bracket and forgets the second root.",
    ),
    "MC.QUAD.FACTOR_SUM_PRODUCT_CONFUSED": (
        "Reports the sum and product as the roots",
        "The student mixes up what the sum and product of two numbers are used for.",
    ),
    "MC.QUAD.BRACKET_COEFF_IGNORED": (
        "Ignores the coefficient of x inside a bracket",
        "The student adds or subtracts but never divides by the number multiplying x in the bracket.",
    ),
    "MC.QUAD.BRACKET_COEFF_INVERTED": (
        "Divides the wrong way round",
        "To undo a bracket the student writes the coefficient over the number instead of the number over the coefficient.",
    ),
    "MC.QUAD.FORMULA_B_SIGN": (
        "Uses b instead of minus b",
        "The student forgets the leading minus sign in the formula.",
    ),
    "MC.QUAD.FORMULA_FORGOT_2A": (
        "Divides by a instead of twice a",
        "The denominator of the formula is written as the leading coefficient only.",
    ),
    "MC.QUAD.FORMULA_DIVIDE_ONE_TERM": (
        "Divides only the square-root part",
        "The student divides only the discriminant term by 2a and leaves the other term alone.",
    ),
    "MC.QUAD.FORMULA_FORGOT_A": (
        "Divides by 2 and ignores the leading coefficient",
        "The student treats the leading coefficient as 1 in the denominator.",
    ),
    "MC.QUAD.FORMULA_DISC_SIGN": (
        "Adds instead of subtracting in the discriminant",
        "The student evaluates b squared plus 4ac.",
    ),
    "MC.QUAD.DISC_SIGN_OF_4AC": (
        "Adds 4ac in the discriminant",
        "The student writes b squared plus 4ac instead of minus.",
    ),
    "MC.QUAD.DISC_FORGOT_FOUR": (
        "Forgets the factor 4",
        "The student subtracts ac instead of 4ac.",
    ),
    "MC.QUAD.DISC_DOUBLED_B": (
        "Doubles b instead of squaring it",
        "The student writes 2b in place of b squared.",
    ),
    "MC.QUAD.DISC_NEGATIVE_B_SQUARED": (
        "Carries the minus into the square",
        "With a negative b the student squares the minus sign away incorrectly and gets a negative square.",
    ),
    "MC.QUAD.NATURE_DISC_SIGN_REVERSED": (
        "Reads the sign of the discriminant backwards",
        "A positive discriminant is taken to mean no real roots, or a negative one to mean two roots.",
    ),
    "MC.QUAD.NATURE_ZERO_ONLY_TESTED": (
        "Only tests whether the discriminant is zero",
        "Any non-zero discriminant is wrongly treated as the same case.",
    ),
    "MC.QUAD.NATURE_EQUAL_ROOTS_MISSED": (
        "Misses the equal-roots case",
        "A zero discriminant is thought to give two different roots.",
    ),
    "MC.QUAD.NATURE_ZERO_DISC_NO_ROOTS": (
        "Thinks zero discriminant means no roots",
        "The student reads zero as nothing, so concludes there are no roots.",
    ),
    "MC.QUAD.NATURE_ONE_REAL_ONE_NOT": (
        "Mixed real and non-real roots",
        "The student believes a quadratic can have one real and one non-real root.",
    ),
    "MC.QUAD.K_POSITIVE_ONLY": (
        "Gives only the positive value of the parameter",
        "After taking a square root the student forgets the negative value.",
    ),
    "MC.QUAD.K_FORGOT_SQRT": (
        "Forgets the square root on the parameter",
        "The student stops at the value of k squared.",
    ),
    "MC.QUAD.K_FORGOT_FACTOR_FOUR": (
        "Forgets the 4 in the discriminant condition",
        "The student sets b squared equal to ac instead of 4ac.",
    ),
    "MC.QUAD.K_ONE_SIGN_PAIR": (
        "Mismatched pair for the parameter",
        "The student combines a correct negative value with an unrelated positive one.",
    ),
    "MC.QUAD.K_SIGN": (
        "Reverses the sign of the parameter",
        "The student finds the size of k correctly but gives it the opposite sign.",
    ),
    "MC.QUAD.K_HALF_FACTOR": (
        "Uses 2 where 4 is needed",
        "The student writes 2kc instead of 4kc in the discriminant.",
    ),
    "MC.QUAD.K_INVERTED": (
        "Inverts the parameter",
        "The student rearranges the condition upside down.",
    ),
    "MC.QUAD.FORM_SUM_SIGN": (
        "Wrong sign on the middle term",
        "The student writes plus the sum of the roots instead of minus.",
    ),
    "MC.QUAD.FORM_PRODUCT_SIGN": (
        "Wrong sign on the constant",
        "The student uses the opposite of the product and also flips the middle term.",
    ),
    "MC.QUAD.SUM_PRODUCT_CONFUSED": (
        "Swaps sum and product",
        "The coefficient of x and the constant term are filled in the wrong way round.",
    ),
    "MC.QUAD.FORM_BOTH_SIGNS_FLIPPED": (
        "Both coefficients take the wrong sign",
        "The student reverses the signs of the constant and the x coefficient.",
    ),
    "MC.QUAD.CS_SIGN_OF_HALF": (
        "Wrong sign inside the bracket",
        "The student halves the coefficient but writes it with the opposite sign.",
    ),
    "MC.QUAD.CS_NOT_HALVED": (
        "Does not halve the coefficient",
        "The whole x coefficient is placed in the bracket.",
    ),
    "MC.QUAD.CS_SQUARED_INSTEAD": (
        "Squares instead of halving",
        "The student squares the coefficient to find what goes inside the bracket.",
    ),
    "MC.QUAD.CS_ADDED_NOT_SUBTRACTED": (
        "Adds the constant instead of moving it",
        "The student adds the plain number to the square instead of taking it away.",
    ),
    "MC.QUAD.CS_NOT_SQUARED": (
        "Forgets to square the half",
        "The student adds half the coefficient rather than its square.",
    ),
    "MC.QUAD.CS_SIGN_SWAPPED": (
        "Subtracts in the wrong order",
        "The student finds the right pieces but subtracts them the wrong way round.",
    ),
    "MC.QUAD.WORD_LARGER_REPORTED": (
        "Reports the larger number",
        "The student solves correctly but answers with the other number.",
    ),
    "MC.QUAD.WORD_NEGATIVE_ROOT_KEPT": (
        "Keeps the root that does not fit",
        "A negative solution is accepted even though the quantity must be positive.",
    ),
    "MC.QUAD.WORD_SETUP_WRONG_DIFFERENCE": (
        "Sets the numbers up with the wrong gap",
        "The second number is written with the difference subtracted instead of added.",
    ),
    "MC.QUAD.WORD_SUM_USED_FOR_PRODUCT": (
        "Adds where the story multiplies",
        "The student writes a sum of the two numbers in place of their product.",
    ),
    "MC.QUAD.WORD_LENGTH_REPORTED": (
        "Reports the length instead of the breadth",
        "The student answers with the other side.",
    ),
    "MC.QUAD.WORD_SEMIPERIMETER_FOR_SIDE": (
        "Reports the semi-perimeter",
        "The student adds the two sides and reports that as a side.",
    ),
    "MC.QUAD.WORD_BREADTH_REPORTED": (
        "Reports the breadth instead of the length",
        "The student answers with the unknown they defined rather than the quantity asked.",
    ),
    "MC.QUAD.WORD_DIFFERENCE_ADDED_TWICE": (
        "Adds the difference twice",
        "The length is written as the breadth plus twice the stated difference.",
    ),
    "MC.QUAD.WORD_HALF_PERIMETER": (
        "Uses half the perimeter",
        "The student adds length and breadth once and forgets to double.",
    ),
    "MC.QUAD.WORD_AREA_NOT_PERIMETER": (
        "Uses the area where the perimeter is needed",
        "Cost per metre is multiplied by the area, not the distance round.",
    ),
    "MC.QUAD.WORD_LENGTH_AS_BREADTH": (
        "Swaps the length and the breadth",
        "The roles of the two sides are exchanged before the perimeter is found.",
    ),
    "MC.QUAD.WORD_FORGOT_FINAL_STEP": (
        "Stops before the final step",
        "The student finds the perimeter but does not multiply by the rate.",
    ),
    "MC.QUAD.WORD_OTHER_SIDE_REPORTED": (
        "Reports the other side",
        "The student answers with the side that was not asked about.",
    ),
    "MC.QUAD.WORD_HYPOTENUSE_MINUS_DIFFERENCE": (
        "Subtracts the difference from the longest side",
        "The student guesses a side by taking the difference from the hypotenuse.",
    ),
    "MC.QUAD.WORD_SIDES_SUMMED": (
        "Mixes the longest side and a leg",
        "The student subtracts a leg from the hypotenuse and reports it as the other leg.",
    ),
    "MC.QUAD.WORD_OTHER_SPEED_REPORTED": (
        "Reports the other speed",
        "The student answers with the faster or the usual speed, whichever was not asked.",
    ),
    "MC.QUAD.WORD_INCREASE_SUBTRACTED": (
        "Subtracts the speed increase",
        "The student takes the increase away from the usual speed.",
    ),
    "MC.QUAD.WORD_INCREASE_ONLY": (
        "Reports the speed increase itself",
        "The student answers with the given change in speed.",
    ),
    # ---------------- Arithmetic progressions
    "MC.AP.DIFF_SIGN_REVERSED": (
        "Wrong order when subtracting",
        "The student subtracts the later term from the earlier one, so the sign is reversed.",
    ),
    "MC.AP.DIFF_AS_RATIO": (
        "Divides instead of subtracting",
        "The student finds the ratio of two terms instead of their difference.",
    ),
    "MC.AP.DIFF_FIRST_TERM_GIVEN": (
        "Reports the first term",
        "The student gives the first term in place of the difference.",
    ),
    "MC.AP.DIFF_SKIPPED_TERM": (
        "Subtracts terms that are not neighbours",
        "The student takes the difference between terms two places apart.",
    ),
    "MC.AP.DIFF_LAST_TERM_GIVEN": (
        "Reports the last listed term",
        "The student gives the final term shown.",
    ),
    "MC.AP.RATIO_FOR_DIFFERENCE": (
        "Mistakes a constant ratio for a constant difference",
        "A list that multiplies by the same number each time is accepted as an AP.",
    ),
    "MC.AP.CHECKED_TWO_TERMS_ONLY": (
        "Checks only the first gap",
        "The student compares the first two terms and does not check the rest.",
    ),
    "MC.AP.DIFFERENCES_INCREASING_ACCEPTED": (
        "Accepts steadily growing steps",
        "A list whose gaps grow by a fixed amount is taken to be an AP.",
    ),
    "MC.AP.NTH_N_FOR_N_MINUS_1": (
        "Uses n instead of n minus 1",
        "The student multiplies the difference by the position instead of by one fewer.",
    ),
    "MC.AP.NTH_D_ADDED_NOT_MULTIPLIED": (
        "Adds the difference instead of multiplying",
        "The student adds d once rather than multiplying by the number of steps.",
    ),
    "MC.AP.NTH_SIGN_OF_D_FLIPPED": (
        "Subtracts the difference",
        "The student takes the steps in the wrong direction.",
    ),
    "MC.AP.NTH_FIRST_TERM_DROPPED": (
        "Forgets the first term",
        "The student reports only the total of the steps.",
    ),
    "MC.AP.NTH_OFF_BY_ONE_LOW": (
        "Counts two fewer steps than needed",
        "The student uses n minus 2 steps.",
    ),
    "MC.AP.FIND_N_FORGOT_PLUS_ONE": (
        "Forgets to add 1 to the step count",
        "The student finds the number of steps and reports it as the position.",
    ),
    "MC.AP.FIND_N_OVERCOUNT": (
        "Counts one position too many",
        "The student adds 1 twice when finding the position.",
    ),
    "MC.AP.FIND_N_DIFFERENCE_NOT_DIVIDED": (
        "Stops before dividing by the difference",
        "The student subtracts the first term and reports the result as the position.",
    ),
    "MC.AP.FIND_N_VALUE_OVER_DIFFERENCE": (
        "Divides the target by the difference",
        "The student ignores the first term and divides the target value directly.",
    ),
    "MC.AP.TWO_TERMS_DIFF_NOT_DIVIDED": (
        "Does not share the change over the steps",
        "The difference between two terms is used as the common difference even when they are several steps apart.",
    ),
    "MC.AP.TWO_TERMS_STARTED_FROM_GIVEN_TERM": (
        "Starts counting from a given term as if it were the first",
        "The student treats the first given term as the first term of the AP.",
    ),
    "MC.AP.SUM_FORGOT_HALF": (
        "Forgets to halve",
        "The student computes n times the bracket without dividing by 2.",
    ),
    "MC.AP.SUM_N_FOR_N_MINUS_1": (
        "Uses n instead of n minus 1 in the sum",
        "The step count inside the sum formula is one too large.",
    ),
    "MC.AP.SUM_NO_DOUBLE_A": (
        "Forgets to double the first term",
        "The student uses a instead of 2a inside the sum formula.",
    ),
    "MC.AP.SUM_AS_NTH_TERM": (
        "Gives the last term instead of the sum",
        "The student answers with a_n.",
    ),
    "MC.AP.SUM_COUNT_FORGOT_PLUS_ONE": (
        "Counts the terms one short",
        "The number of terms is taken as the number of gaps.",
    ),
    "MC.AP.SUM_LAST_TERM_AS_COUNT": (
        "Uses the last term as the number of terms",
        "The last term is placed where n belongs.",
    ),
    "MC.AP.SUM_FORGOT_COUNT_AND_HALF": (
        "Adds only the first and last terms",
        "The student reports first plus last as the sum.",
    ),
    "MC.AP.SUMN_OTHER_ROOT_KEPT": (
        "Keeps the root that is not a count",
        "A negative or fractional solution is accepted as the number of terms.",
    ),
    "MC.AP.SUMN_OFF_BY_ONE": (
        "Off by one in the number of terms",
        "The student solves correctly and then adds or removes one.",
    ),
    "MC.AP.SUMN_DIVIDED_BY_FIRST_TERM": (
        "Divides the sum by the first term",
        "The student treats the sum as n times the first term.",
    ),
    "MC.AP.TERM_IS_SUM": (
        "Reports the sum instead of the term",
        "The student answers with S_n at the stated position.",
    ),
    "MC.AP.TERM_FROM_SUM_AVERAGE": (
        "Divides the sum by n",
        "The student finds the average of the terms and calls it the term.",
    ),
    "MC.AP.TERM_FROM_SUM_WRONG_INDEX": (
        "Subtracts the wrong earlier sum",
        "The student subtracts S two places back, not one.",
    ),
    "MC.AP.TERM_FROM_SUM_NEXT_SUM": (
        "Takes the sums either side",
        "The student subtracts the sum before from the sum after, getting two terms.",
    ),
    "MC.AP.D_FROM_SUM_COEFF_NOT_DOUBLED": (
        "Forgets to double the coefficient",
        "The difference is read as the coefficient of n squared, not twice it.",
    ),
    "MC.AP.D_FROM_SUM_FIRST_TERM": (
        "Reports the first term",
        "The student gives the first term rather than the difference.",
    ),
    "MC.AP.D_FROM_SUM_SECOND_TERM": (
        "Reports the second term",
        "The student gives the second term rather than the difference.",
    ),
    "MC.AP.D_FROM_SUM_LINEAR_COEFF": (
        "Reads the difference from the linear term",
        "The student takes the coefficient of n as the difference.",
    ),
    "MC.AP.WORD_TOTAL_REPORTED": (
        "Reports the total for a single term",
        "The student answers with the sum of all rows.",
    ),
    "MC.AP.WORD_LAST_REPORTED": (
        "Reports the last value for the total",
        "The student answers with the final term rather than the total.",
    ),
    "MC.AP.COUNT_FORGOT_PLUS_ONE": (
        "Counts the multiples one short",
        "The student subtracts the positions without adding 1.",
    ),
    "MC.AP.ENDPOINTS_USED_NOT_MULTIPLES": (
        "Uses the range ends instead of the multiples",
        "The student averages the ends of the range even though they are not multiples.",
    ),
    "MC.AP.MULTIPLES_STARTED_FROM_FIRST": (
        "Starts adding multiples from the very first",
        "The student includes the multiples below the range.",
    ),
    # ---------------- Trigonometry
    "MC.TRIG.SIN_COS_MIXED": (
        "Mixes up sine and cosine",
        "The student uses the adjacent side where the opposite is needed, or the reverse.",
    ),
    "MC.TRIG.RATIO_INVERTED": (
        "Writes the ratio upside down",
        "The student inverts the fraction, giving the reciprocal ratio.",
    ),
    "MC.TRIG.SIN_AS_OPP_OVER_ADJ": (
        "Takes sine as opposite over adjacent",
        "The hypotenuse is replaced by the adjacent side.",
    ),
    "MC.TRIG.SIN_AS_ADJ_OVER_OPP": (
        "Takes sine as adjacent over opposite",
        "Both the numerator and the denominator are chosen wrongly.",
    ),
    "MC.TRIG.COS_AS_ADJ_OVER_OPP": (
        "Takes cosine as adjacent over opposite",
        "The hypotenuse is replaced by the opposite side.",
    ),
    "MC.TRIG.COS_AS_OPP_OVER_ADJ": (
        "Takes cosine as opposite over adjacent",
        "Both sides of the ratio are chosen wrongly.",
    ),
    "MC.TRIG.TAN_AS_OPP_OVER_HYP": (
        "Takes tangent as opposite over hypotenuse",
        "The student uses the longest side as the denominator.",
    ),
    "MC.TRIG.TAN_AS_ADJ_OVER_HYP": (
        "Takes tangent as adjacent over hypotenuse",
        "The student uses the sides of the cosine ratio.",
    ),
    "MC.TRIG.HYP_AS_SUM_OF_LEGS": (
        "Takes the hypotenuse as the sum of the legs",
        "The student adds the two legs instead of using the right-triangle relation.",
    ),
    "MC.TRIG.SWAPPED_SIN_COS_VALUES": (
        "Swaps the sine and cosine table values",
        "The student recalls the values of sine and cosine in the wrong order.",
    ),
    "MC.TRIG.SQUARE_DROPPED": (
        "Forgets to square the ratio",
        "The student evaluates each ratio but skips the power.",
    ),
    "MC.TRIG.ANGLES_ADDED_INSIDE": (
        "Adds the angles inside one ratio",
        "The student treats sin A plus sin B as sin of A plus B.",
    ),
    "MC.TRIG.TAN_VALUE_AS_SIN_VALUE": (
        "Uses the sine value for the tangent",
        "The student recalls the sine table and applies it to tangent.",
    ),
    "MC.TRIG.OPERATION_MIXED_UP": (
        "Uses the wrong operation between terms",
        "The two values are right but combined with the other operation.",
    ),
    "MC.TRIG.COMPLEMENT_GAVE_ZERO": (
        "Concludes that complementary terms cancel to zero",
        "The student sees matching ratios and assumes they cancel.",
    ),
    "MC.TRIG.COMPLEMENT_GAVE_ONE": (
        "Concludes the expression equals one",
        "The student applies a sum-of-squares or ratio result where it does not hold.",
    ),
    "MC.TRIG.COMPLEMENT_GAVE_TWO": (
        "Adds two equal values",
        "The student sees two terms each worth one and adds them.",
    ),
    "MC.TRIG.COMPLEMENT_GAVE_MINUS_ONE": (
        "Gets a stray minus sign",
        "A minus sign is carried from the subtraction into the result.",
    ),
    "MC.TRIG.PYTHAG_NOT_SQUARED": (
        "Forgets the squares in the identity",
        "The student writes cos A as 1 minus sin A.",
    ),
    "MC.TRIG.SQUARE_NOT_ROOTED": (
        "Stops at the square of the ratio",
        "The student finds the square of the ratio and does not take the root.",
    ),
    "MC.TRIG.GIVEN_REPEATED": (
        "Repeats the given ratio",
        "The student answers with the value they were given.",
    ),
    "MC.TRIG.WRONG_RATIO_REPORTED": (
        "Reports the third ratio",
        "The student finds a different ratio from the one asked.",
    ),
    "MC.TRIG.HD_TAN_INVERTED": (
        "Divides by the tangent instead of multiplying",
        "The student uses cotangent where tangent is needed.",
    ),
    "MC.TRIG.HD_SIN_FOR_TAN": (
        "Uses sine instead of tangent",
        "The student involves the sloping side without it being known.",
    ),
    "MC.TRIG.HD_COS_FOR_TAN": (
        "Uses cosine instead of tangent",
        "The student picks the ratio of adjacent to hypotenuse.",
    ),
    "MC.TRIG.HD_SLANT_REPORTED": (
        "Reports the sloping distance",
        "The student finds the hypotenuse rather than the height or distance.",
    ),
    "MC.TRIG.HD_MULTIPLIED_NOT_DIVIDED": (
        "Multiplies where division is needed",
        "The unknown sits under the ratio and the student multiplies instead of dividing.",
    ),
    "MC.TRIG.HD_SIN_COS_SWAPPED": (
        "Swaps sine and cosine in the figure",
        "The student attaches the ratio to the wrong side of the ladder triangle.",
    ),
    "MC.TRIG.HD_TAN_FOR_SIN_COS": (
        "Uses tangent where sine or cosine is needed",
        "The student chooses a ratio that does not include the ladder.",
    ),
    "MC.TRIG.HD_DIVIDED_NOT_MULTIPLIED": (
        "Divides where multiplication is needed",
        "The student divides the ladder length by the ratio.",
    ),
    "MC.TRIG.HD_HALF_LENGTH_ONLY": (
        "Halves the length without a ratio",
        "The student assumes the side is half the ladder.",
    ),
    "MC.TRIG.HD_SIDE_REPORTED": (
        "Reports the given side as the ladder",
        "The student answers with the number from the question.",
    ),
    "MC.TRIG.HD_DEPRESSION_FROM_VERTICAL": (
        "Measures the angle of depression from the vertical",
        "The student places the angle against the wall of the tower, so the ratio is inverted.",
    ),
    "MC.TRIG.HD_SEPARATION_AS_HEIGHT": (
        "Reports the distance walked as the height",
        "The student uses the separation between the two positions directly.",
    ),
    "MC.TRIG.HD_FIRST_ANGLE_ONLY": (
        "Uses only the first angle",
        "The student treats the distance walked as the whole ground distance.",
    ),
    "MC.TRIG.HD_SECOND_ANGLE_ONLY": (
        "Uses only the second angle",
        "The student treats the distance walked as the final ground distance.",
    ),
    "MC.TRIG.HD_DISTANCES_ADDED": (
        "Adds the two ground distances",
        "The student adds where the two distances should be subtracted.",
    ),
}
